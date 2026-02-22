/**
 * app.js
 * ──────
 * Application entry point and top-level orchestrator.
 *
 * Responsibilities:
 *  - On page load: check if a token exists → resume session or show auth
 *  - Expose App.onLoginSuccess() so auth.js can call it after login
 *  - Wire up the logout button
 *
 * All other logic is delegated to the relevant modules:
 *   Auth, Agents, Chat, AudioManager
 */

const App = (() => {

  // ─── DOM references ──────────────────────────────────────────
  const authPage  = document.getElementById("auth-page");
  const appPage   = document.getElementById("app-page");
  const logoutBtn = document.getElementById("logout-btn");

  // ─── Logout ───────────────────────────────────────────────────

  logoutBtn.addEventListener("click", () => {
    // Clear agents list and chat state
    Agents.clear();

    // Delegate credential clearing + UI switch to Auth
    Auth.logout();
  });

  // ─── Login success hook ───────────────────────────────────────

  /**
   * Called by auth.js after a successful login or auto-login after register.
   * @param {string} username - the logged-in username (stored for audio paths)
   */
  async function onLoginSuccess(username) {
    // Hide auth page, show main app
    authPage.classList.add("hidden");
    appPage.classList.remove("hidden");

    // Load the user's agents into the sidebar
    await Agents.loadAll();
  }

  // ─── On page load: check for existing session ─────────────────

  function init() {
    const token    = localStorage.getItem(CONFIG.TOKEN_KEY);
    const username = localStorage.getItem(CONFIG.USERNAME_KEY);

    if (token && username) {
      // We have a stored token — try to resume the session
      // Verify the token is still valid by calling /users/me/
      API.get("/users/me/")
        .then(() => {
          // Token is valid — go straight to the app
          onLoginSuccess(username);
        })
        .catch(() => {
          // Token expired or invalid — show login
          localStorage.removeItem(CONFIG.TOKEN_KEY);
          localStorage.removeItem(CONFIG.USERNAME_KEY);
          Auth.show();
        });
    } else {
      // No token — show the auth page
      Auth.show();
    }
  }

  // Start the app
  init();

  return { onLoginSuccess };

})();
