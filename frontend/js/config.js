/**
 * config.js
 * ─────────
 * Central place for all configuration constants.
 * Change API_BASE to point to your backend server.
 */

const CONFIG = {
  /**
   * Base URL for the FastAPI backend.
   * Trailing slash intentionally omitted.
   * Example: "https://myserver.com" or "http://localhost:8000"
   */
  API_BASE: "http://localhost:8000",

  /**
   * How many messages to load per page when paginating chat history.
   */
  MESSAGES_PER_PAGE: 10,

  /**
   * localStorage key used to persist the JWT token between page reloads.
   */
  TOKEN_KEY: "multiagent_token",

  /**
   * localStorage key used to persist the logged-in username.
   * Needed to reconstruct audio file paths (media/user_{username}_{id}.wav).
   */
  USERNAME_KEY: "multiagent_username",
};
