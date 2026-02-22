/**
 * api.js
 * ──────
 * Thin wrapper around fetch() that:
 *  - Prepends CONFIG.API_BASE to every URL
 *  - Injects the JWT Authorization header automatically
 *  - Parses JSON responses
 *  - Throws a readable Error on non-2xx responses
 *
 * Usage:
 *   const user = await API.get("/users/me/");
 *   const agent = await API.post("/agents/", { name: "Bot", system_prompt: "..." });
 */

const API = (() => {

  /** Return the stored JWT token (or null if not logged in). */
  function getToken() {
    return localStorage.getItem(CONFIG.TOKEN_KEY);
  }

  /**
   * Core fetch wrapper.
   * @param {string} path      - e.g. "/agents/"
   * @param {string} method    - "GET" | "POST" | "PUT" | "DELETE"
   * @param {object|null} body - JSON body (for POST/PUT); null for GET
   * @param {boolean} isForm   - pass true when body is FormData (file upload)
   */
  async function request(path, method = "GET", body = null, isForm = false) {
    const headers = {};

    // Attach token if we have one
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;

    // For JSON bodies, set content-type
    if (body && !isForm) headers["Content-Type"] = "application/json";

    const options = { method, headers };
    if (body) options.body = isForm ? body : JSON.stringify(body);

    const response = await fetch(CONFIG.API_BASE + path, options);

    // For file downloads we return the raw Response so the caller can .blob() it
    if (response.headers.get("Content-Type")?.startsWith("audio/")) {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response; // caller handles .blob()
    }

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      // FastAPI returns { detail: "..." } on errors
      throw new Error(data.detail || `HTTP ${response.status}`);
    }

    return data;
  }

  // ─── Public helpers ───────────────────────────────────────────

  return {
    get:    (path)         => request(path, "GET"),
    post:   (path, body)   => request(path, "POST", body),
    put:    (path, body)   => request(path, "PUT", body),
    upload: (path, formData) => request(path, "POST", formData, true),

    /**
     * Download an audio file and return it as a Blob URL.
     * Used for audio message playback.
     */
    async downloadAudio(messageId) {
      const response = await request(`/messages/${messageId}/download/`);
      const blob = await response.blob();
      return URL.createObjectURL(blob);
    },
  };

})();
