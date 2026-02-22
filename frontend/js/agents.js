/**
 * agents.js
 * ─────────
 * Manages the left sidebar panel:
 *  - Fetching and rendering the list of agents
 *  - Selecting an agent (loads its chats via Chat module)
 *  - Creating a new agent
 *  - Opening the Edit Agent modal
 *
 * Depends on: api.js, config.js, chat.js (called via Chat.loadAgent)
 */

const Agents = (() => {

  // ─── DOM references ──────────────────────────────────────────
  const agentsList     = document.getElementById("agents-list");
  const newNameInput   = document.getElementById("new-agent-name");
  const newPromptInput = document.getElementById("new-agent-prompt");
  const createBtn      = document.getElementById("create-agent-btn");

  // Edit modal elements
  const editModal      = document.getElementById("edit-agent-modal");
  const editNameInput  = document.getElementById("edit-agent-name");
  const editPromptInput= document.getElementById("edit-agent-prompt");
  const editError      = document.getElementById("edit-agent-error");
  const editSaveBtn    = document.getElementById("edit-agent-save");
  const editCancelBtn  = document.getElementById("edit-agent-cancel");
  const editAgentBtn   = document.getElementById("edit-agent-btn"); // in header

  // Track which agent is currently being edited
  let _editingAgentId = null;
  // Track which agent is selected (highlighted in the list)
  let _activeAgentId  = null;

  // ─── Create Agent ─────────────────────────────────────────────

  createBtn.addEventListener("click", async () => {
    const name          = newNameInput.value.trim();
    const system_prompt = newPromptInput.value.trim();

    if (!name || !system_prompt) {
      alert("Please fill in both agent name and prompt.");
      return;
    }

    try {
      createBtn.disabled = true;
      const agent = await API.post("/agents/", { name, system_prompt });

      // Clear inputs
      newNameInput.value   = "";
      newPromptInput.value = "";

      // Add to list and activate
      addAgentToList(agent);
      selectAgent(agent.id);

    } catch (err) {
      alert("Error: " + err.message);
    } finally {
      createBtn.disabled = false;
    }
  });

  // ─── Edit Agent Modal ─────────────────────────────────────────

  // "Edit Agent" button in the chat header opens modal with current agent data
  editAgentBtn.addEventListener("click", () => {
    if (!_activeAgentId) return;
    openEditModal(_activeAgentId);
  });

  editCancelBtn.addEventListener("click", closeEditModal);

  editSaveBtn.addEventListener("click", async () => {
    const name          = editNameInput.value.trim();
    const system_prompt = editPromptInput.value.trim();
    editError.classList.add("hidden");

    if (!name || !system_prompt) {
      showEditError("Both fields are required.");
      return;
    }

    try {
      editSaveBtn.disabled = true;
      const updated = await API.put(`/agents/${_editingAgentId}/`, { name, system_prompt });

      // Refresh the agent's name in the sidebar list
      const listItem = agentsList.querySelector(`[data-agent-id="${_editingAgentId}"]`);
      if (listItem) {
        listItem.querySelector(".agent-name").textContent = updated.name;
      }

      // If this is the active agent, update the header too
      if (_editingAgentId === _activeAgentId) {
        document.getElementById("active-agent-name").textContent = updated.name;
      }

      closeEditModal();
    } catch (err) {
      showEditError(err.message);
    } finally {
      editSaveBtn.disabled = false;
    }
  });

  // Close modal when clicking the backdrop
  editModal.addEventListener("click", (e) => {
    if (e.target === editModal) closeEditModal();
  });

  function openEditModal(agentId) {
    _editingAgentId = agentId;

    // Find the agent's current data from the list item's stored attributes
    const item = agentsList.querySelector(`[data-agent-id="${agentId}"]`);
    editNameInput.value   = item?.dataset.agentName   || "";
    editPromptInput.value = item?.dataset.agentPrompt || "";
    editError.classList.add("hidden");

    editModal.classList.remove("hidden");
  }

  function closeEditModal() {
    editModal.classList.add("hidden");
    _editingAgentId = null;
  }

  function showEditError(msg) {
    editError.textContent = msg;
    editError.classList.remove("hidden");
  }

  // ─── Rendering helpers ────────────────────────────────────────

  /**
   * Create a single <li> element for an agent and append it to the list.
   * We store name/prompt as data-* attributes for the edit modal to read.
   */
  function addAgentToList(agent) {
    // Avoid duplicate entries
    if (agentsList.querySelector(`[data-agent-id="${agent.id}"]`)) return;

    const li = document.createElement("li");
    li.className = "agent-item";
    li.dataset.agentId = agent.id;

    // We store these for the edit modal; they're updated after a successful edit
    li.dataset.agentName   = agent.name          || "";
    li.dataset.agentPrompt = agent.system_prompt  || "";

    li.innerHTML = `
      <span class="agent-name">${escapeHtml(agent.name)}</span>
      <button class="btn-edit">Edit</button>
    `;

    // Click on the item (but not the Edit button) → select agent
    li.addEventListener("click", (e) => {
      if (e.target.classList.contains("btn-edit")) return;
      selectAgent(agent.id);
    });

    // Click the Edit button → open modal
    li.querySelector(".btn-edit").addEventListener("click", () => {
      openEditModal(agent.id);
    });

    agentsList.appendChild(li);
  }

  /**
   * Highlight the selected agent and load its details (chats).
   */
  async function selectAgent(agentId) {
    _activeAgentId = agentId;

    // Update active styling
    agentsList.querySelectorAll(".agent-item").forEach(el => {
      el.classList.toggle("active", Number(el.dataset.agentId) === agentId);
    });

    // Fetch full agent detail (includes chats array)
    try {
      const agentDetail = await API.get(`/agents/${agentId}/`);

      // Store prompt for edit modal (now we have it from the detail endpoint)
      const listItem = agentsList.querySelector(`[data-agent-id="${agentId}"]`);
      if (listItem) listItem.dataset.agentPrompt = agentDetail.system_prompt;

      // Update header
      document.getElementById("active-agent-name").textContent = agentDetail.name;
      document.getElementById("edit-agent-btn").classList.remove("hidden");

      // Hand chats to the Chat module
      Chat.loadAgent(agentDetail);

    } catch (err) {
      console.error("Failed to load agent:", err);
    }
  }

  // ─── Public API ───────────────────────────────────────────────

  /**
   * Fetch all agents for the current user and render them.
   * Called once after login.
   */
  async function loadAll() {
    agentsList.innerHTML = "";
    try {
      const agents = await API.get("/agents/");
      agents.forEach(addAgentToList);
    } catch (err) {
      console.error("Failed to load agents:", err);
    }
  }

  /** Clear the sidebar (called on logout). */
  function clear() {
    agentsList.innerHTML = "";
    _activeAgentId = null;
  }

  return { loadAll, clear };

})();

// ─── Utility: escape HTML to prevent XSS ────────────────────────────────────
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
