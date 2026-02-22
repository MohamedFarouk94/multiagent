/**
 * audio.js
 * ────────
 * Handles:
 *  1. Microphone recording via the MediaRecorder API
 *  2. Uploading recorded audio to the server
 *  3. Resolving audio messages — checking cache first,
 *     downloading from server if not cached, then returning a blob URL
 *
 * Depends on: api.js, storage.js, config.js
 */

const AudioManager = (() => {

  // ─── DOM references ──────────────────────────────────────────
  const micBtn         = document.getElementById("mic-btn");
  const audioPreview   = document.getElementById("audio-preview");
  const audioPreviewLbl= document.getElementById("audio-preview-label");
  const discardBtn     = document.getElementById("audio-discard-btn");

  // ─── Internal state ──────────────────────────────────────────
  let _mediaRecorder  = null;   // MediaRecorder instance
  let _audioChunks    = [];     // Collected audio chunks during recording
  let _recordedBlob   = null;   // Final recorded Blob (after stop)
  let _isRecording    = false;

  /**
   * Pick the best audio MIME type the current browser supports.
   * MediaRecorder does NOT record real WAV — it uses WebM/Opus or MP4/AAC.
   * OpenAI Whisper accepts: mp3, mp4, webm, wav, m4a, etc.
   * We pick webm first (Chrome/Firefox), then mp4 (Safari), then default.
   */
  function getSupportedMimeType() {
    const candidates = [
      "audio/webm;codecs=opus",
      "audio/webm",
      "audio/mp4",
      "audio/ogg;codecs=opus",
    ];
    for (const type of candidates) {
      if (MediaRecorder.isTypeSupported(type)) return type;
    }
    return ""; // Let the browser pick (still better than lying)
  }

  /** Given a MIME type string, return the matching file extension. */
  function mimeToExtension(mimeType) {
    if (mimeType.includes("webm")) return "webm";
    if (mimeType.includes("mp4"))  return "mp4";
    if (mimeType.includes("ogg"))  return "ogg";
    return "webm"; // safe default OpenAI accepts
  }

  // ─── Recording controls ──────────────────────────────────────

  micBtn.addEventListener("click", () => {
    if (_isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  });

  discardBtn.addEventListener("click", discardRecording);

  async function startRecording() {
    // Request microphone access
    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (err) {
      alert("Microphone access denied. Please allow microphone access and try again.");
      return;
    }

    _audioChunks = [];
    const mimeType = getSupportedMimeType();
    _mediaRecorder = new MediaRecorder(stream, mimeType ? { mimeType } : {});

    // Collect audio data chunks as they arrive
    _mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) _audioChunks.push(event.data);
    };

    // When recording finishes, assemble the Blob using the REAL mime type
    _mediaRecorder.onstop = () => {
      const actualMime = _mediaRecorder.mimeType || mimeType || "audio/webm";
      _recordedBlob = new Blob(_audioChunks, { type: actualMime });

      // Show preview bar
      audioPreviewLbl.textContent = "🎙 Recording ready — press Send or discard";
      audioPreview.classList.remove("hidden");

      // Stop all microphone tracks to release the device
      stream.getTracks().forEach(t => t.stop());
    };

    _mediaRecorder.start();
    _isRecording = true;

    // Visual feedback: mic button turns red and pulses
    micBtn.classList.add("recording");
    micBtn.textContent = "⏹";
    micBtn.title = "Stop recording";
  }

  function stopRecording() {
    if (_mediaRecorder && _isRecording) {
      _mediaRecorder.stop();
      _isRecording = false;
      micBtn.classList.remove("recording");
      micBtn.textContent = "🎤";
      micBtn.title = "Record audio";
    }
  }

  function discardRecording() {
    _recordedBlob = null;
    _audioChunks  = [];
    audioPreview.classList.add("hidden");
  }

  // ─── Upload & Send ────────────────────────────────────────────

  /**
   * Convert any audio Blob (WebM, MP4, etc.) into a true WAV Blob.
   *
   * How it works:
   *  1. Decode the compressed audio using the Web Audio API (AudioContext)
   *  2. Extract raw PCM float samples from the decoded AudioBuffer
   *  3. Write a proper WAV file header + the PCM samples as 16-bit integers
   *
   * This means the backend always receives a genuine .wav file,
   * no matter what format the browser recorded in (WebM, MP4, etc.)
   */
  async function convertToWav(blob) {
    // Step 1: Decode the compressed audio into raw PCM samples
    const arrayBuffer  = await blob.arrayBuffer();
    const audioContext = new AudioContext();
    const audioBuffer  = await audioContext.decodeAudioData(arrayBuffer);
    await audioContext.close();

    // Step 2: Mix down to mono (average all channels) for simplicity.
    // Whisper works fine with mono audio.
    const numChannels  = audioBuffer.numberOfChannels;
    const numSamples   = audioBuffer.length;
    const sampleRate   = audioBuffer.sampleRate;
    const monoSamples  = new Float32Array(numSamples);

    for (let ch = 0; ch < numChannels; ch++) {
      const channelData = audioBuffer.getChannelData(ch);
      for (let i = 0; i < numSamples; i++) {
        monoSamples[i] += channelData[i] / numChannels;
      }
    }

    // Step 3: Write WAV file
    // WAV format: RIFF header (44 bytes) + 16-bit PCM samples
    const byteCount  = numSamples * 2; // 2 bytes per 16-bit sample
    const buffer     = new ArrayBuffer(44 + byteCount);
    const view       = new DataView(buffer);

    // Helper to write ASCII strings into the DataView
    const writeStr = (offset, str) => {
      for (let i = 0; i < str.length; i++) {
        view.setUint8(offset + i, str.charCodeAt(i));
      }
    };

    // RIFF chunk descriptor
    writeStr(0,  "RIFF");
    view.setUint32(4,  36 + byteCount, true);  // file size - 8
    writeStr(8,  "WAVE");

    // fmt sub-chunk
    writeStr(12, "fmt ");
    view.setUint32(16, 16,         true);  // sub-chunk size (16 for PCM)
    view.setUint16(20, 1,          true);  // audio format: PCM = 1
    view.setUint16(22, 1,          true);  // num channels: mono
    view.setUint32(24, sampleRate, true);  // sample rate
    view.setUint32(28, sampleRate * 2, true); // byte rate = sampleRate * channels * bitsPerSample/8
    view.setUint16(32, 2,          true);  // block align = channels * bitsPerSample/8
    view.setUint16(34, 16,         true);  // bits per sample

    // data sub-chunk
    writeStr(36, "data");
    view.setUint32(40, byteCount, true);

    // Write PCM samples as 16-bit signed integers
    let offset = 44;
    for (let i = 0; i < numSamples; i++) {
      // Clamp to [-1, 1] then scale to 16-bit range [-32768, 32767]
      const clamped = Math.max(-1, Math.min(1, monoSamples[i]));
      view.setInt16(offset, clamped < 0 ? clamped * 32768 : clamped * 32767, true);
      offset += 2;
    }

    return new Blob([buffer], { type: "audio/wav" });
  }

  /**
   * Upload the recorded audio blob to /chats/{chatId}/upload-audio/
   * Converts to real WAV first so the backend always receives a .wav file.
   * Returns the message_id from the server response.
   */
  async function uploadRecording(chatId) {
    if (!_recordedBlob) throw new Error("No recording to upload.");

    // Convert whatever format the browser recorded (WebM, MP4…) to genuine WAV
    const wavBlob = await convertToWav(_recordedBlob);

    const formData = new FormData();
    formData.append("file", wavBlob, "recording.wav");

    const data = await API.upload(`/chats/${chatId}/upload-audio/`, formData);
    return data.message_id;
  }

  /**
   * Clear the recording state after it has been sent.
   */
  function clearAfterSend() {
    _recordedBlob = null;
    _audioChunks  = [];
    audioPreview.classList.add("hidden");
  }

  /**
   * Returns true if the user has a pending recorded blob ready to send.
   */
  function hasRecording() {
    return !!_recordedBlob;
  }

  // ─── Audio Resolution (cache → download) ─────────────────────

  /**
   * Given a message object, resolve its audio to a playable blob URL.
   *
   * Strategy:
   *  1. Build the cache key (same format as backend filename)
   *  2. Check IndexedDB — if cached, return blob URL immediately
   *  3. Otherwise, download from /messages/{id}/download/,
   *     store in IndexedDB, and return the new blob URL
   *
   * @param {object} message  - { id, sender, is_audio, ... }
   * @returns {Promise<string>} - a blob: URL safe to use in <audio src>
   */
  async function resolveAudioUrl(message) {
    const username = localStorage.getItem(CONFIG.USERNAME_KEY);
    const isAgent  = message.sender === "agent";

    // Build the cache key mirroring the backend filename convention
    const cacheKey = isAgent
      ? AudioStorage.agentKey(username, message.id)
      : AudioStorage.userKey(username, message.id);

    // Check cache first
    const cached = await AudioStorage.get(cacheKey);
    if (cached) return cached;

    // Not cached — download from API
    const response = await API.downloadAudio(message.id);
    // response here is a blob: URL string from api.downloadAudio
    // But we also need the raw blob to store in IndexedDB.
    // Re-fetch to get the blob for storage.
    const rawResponse = await fetch(CONFIG.API_BASE + `/messages/${message.id}/download/`, {
      headers: { Authorization: `Bearer ${localStorage.getItem(CONFIG.TOKEN_KEY)}` }
    });
    const blob = await rawResponse.blob();

    // Store for next time
    await AudioStorage.set(cacheKey, blob);

    // Return a fresh blob URL from the just-downloaded blob
    return URL.createObjectURL(blob);
  }

  return {
    hasRecording,
    uploadRecording,
    clearAfterSend,
    resolveAudioUrl,
  };

})();