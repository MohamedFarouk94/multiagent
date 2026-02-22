/**
 * auth.js
 * ───────
 * Handles everything related to authentication:
 *  - Showing the login / register page
 *  - Submitting forms and calling the API
 *  - Storing / clearing the JWT token in localStorage
 *  - Auto-login after successful registration
 */

const Auth = (() => {

  // ─── DOM references ──────────────────────────────────────────
  const authPage     = document.getElementById("auth-page");
  const tabs         = document.querySelectorAll(".auth-tab");
  const loginForm    = document.getElementById("login-form");
  const registerForm = document.getElementById("register-form");
  const loginError   = document.getElementById("login-error");
  const registerError= document.getElementById("register-error");

  // ─── Tab switching ───────────────────────────────────────────

  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      // Update active tab
      tabs.forEach(t => t.classList.remove("active"));
      tab.classList.add("active");

      // Show matching form
      const which = tab.dataset.tab; // "login" or "register"
      loginForm.classList.toggle("active",    which === "login");
      registerForm.classList.toggle("active", which === "register");

      // Clear errors
      loginError.classList.add("hidden");
      registerError.classList.add("hidden");
    });
  });

  // ─── Login form ──────────────────────────────────────────────

  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    loginError.classList.add("hidden");

    const username = document.getElementById("login-username").value.trim();
    const password = document.getElementById("login-password").value;

    try {
      await doLogin(username, password);
    } catch (err) {
      showError(loginError, err.message);
    }
  });

  // ─── Register form ───────────────────────────────────────────

  registerForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    registerError.classList.add("hidden");

    const username  = document.getElementById("reg-username").value.trim();
    const email     = document.getElementById("reg-email").value.trim();
    const password  = document.getElementById("reg-password").value;
    const password2 = document.getElementById("reg-password2").value;

    // Client-side password match check
    if (password !== password2) {
      showError(registerError, "Passwords do not match.");
      return;
    }

    try {
      // 1. Register
      await API.post("/register/", { username, email, password });

      // 2. Auto-login right after registration
      await doLogin(username, password);
    } catch (err) {
      showError(registerError, err.message);
    }
  });

  // ─── Core login logic ─────────────────────────────────────────

  /**
   * Call the /login/ endpoint, save the token, then bootstrap the app.
   */
  async function doLogin(username, password) {
    const data = await API.post("/login/", { username, password });

    // Persist token and username for later API calls
    localStorage.setItem(CONFIG.TOKEN_KEY,   data.access_token);
    localStorage.setItem(CONFIG.USERNAME_KEY, username);

    // Hand off to the main app
    App.onLoginSuccess(username);
  }

  // ─── Public API ───────────────────────────────────────────────

  /** Show the auth page (called on logout or on initial load without token). */
  function show() {
    document.getElementById("app-page").classList.add("hidden");
    authPage.classList.remove("hidden");
  }

  /** Remove stored credentials and return to login screen. */
  function logout() {
    localStorage.removeItem(CONFIG.TOKEN_KEY);
    localStorage.removeItem(CONFIG.USERNAME_KEY);
    show();
  }

  // ─── Helpers ─────────────────────────────────────────────────

  function showError(el, message) {
    el.textContent = message;
    el.classList.remove("hidden");
  }

  return { show, logout };

})();
