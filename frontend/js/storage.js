/**
 * storage.js
 * ──────────
 * IndexedDB helper for caching audio blobs locally in the browser.
 *
 * Why IndexedDB?
 *   Browsers don't let web pages write to the real filesystem.
 *   IndexedDB is the standard browser API for storing binary data
 *   (like audio files) persistently across page reloads.
 *
 * The "virtual" file key format mirrors the backend naming convention:
 *   User audio:  "user_{username}_{messageId}.wav"
 *   Agent audio: "agent_{username}_{messageId}.mp3"
 *
 * Usage:
 *   const url = await AudioStorage.get(key);      // → blob URL or null
 *   await AudioStorage.set(key, blob);             // store a Blob
 */

const AudioStorage = (() => {

  const DB_NAME    = "multiagent_audio";
  const STORE_NAME = "audio_files";
  const DB_VERSION = 1;

  // We open the DB once and reuse the connection
  let _db = null;

  /** Open (or create) the IndexedDB database. Returns a Promise<IDBDatabase>. */
  function openDB() {
    if (_db) return Promise.resolve(_db);

    return new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);

      // Called once when the DB is created or upgraded
      request.onupgradeneeded = (event) => {
        const db = event.target.result;
        if (!db.objectStoreNames.contains(STORE_NAME)) {
          db.createObjectStore(STORE_NAME); // keyed by our filename string
        }
      };

      request.onsuccess = (event) => {
        _db = event.target.result;
        resolve(_db);
      };

      request.onerror = () => reject(request.error);
    });
  }

  /**
   * Retrieve a cached audio Blob URL by its virtual filename key.
   * Returns a blob: URL string if found, or null if not cached yet.
   */
  async function get(key) {
    const db = await openDB();
    return new Promise((resolve) => {
      const tx    = db.transaction(STORE_NAME, "readonly");
      const store = tx.objectStore(STORE_NAME);
      const req   = store.get(key);

      req.onsuccess = () => {
        if (req.result) {
          // Convert stored Blob back into a usable object URL
          resolve(URL.createObjectURL(req.result));
        } else {
          resolve(null); // not cached
        }
      };
      req.onerror = () => resolve(null);
    });
  }

  /**
   * Store an audio Blob under the given virtual filename key.
   * @param {string} key   - e.g. "agent_alice_42.mp3"
   * @param {Blob}   blob  - the raw audio blob from fetch
   */
  async function set(key, blob) {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const tx    = db.transaction(STORE_NAME, "readwrite");
      const store = tx.objectStore(STORE_NAME);
      const req   = store.put(blob, key);
      req.onsuccess = () => resolve();
      req.onerror   = () => reject(req.error);
    });
  }

  // ─── Public helpers for constructing keys ────────────────────

  function userKey(username, messageId)  { return `user_${username}_${messageId}.wav`; }
  function agentKey(username, messageId) { return `agent_${username}_${messageId}.mp3`; }

  return { get, set, userKey, agentKey };

})();
