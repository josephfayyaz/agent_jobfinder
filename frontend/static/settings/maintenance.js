/*
 * Maintenance and destructive workspace actions.
 */

(() => {
  const app = window.SettingsApp;

  app.runWorkspaceDanger = async function runWorkspaceDanger(action, inputId, expectedPhrase, statusId) {
    const input = document.getElementById(inputId);
    const status = document.getElementById(statusId);
    const phrase = input ? input.value.trim() : "";

    if (!phrase) {
      if (status) {
        status.textContent = "Enter the confirmation phrase first.";
      }
      return;
    }
    if (phrase !== expectedPhrase) {
      if (status) {
        status.textContent = `Type exactly: ${expectedPhrase}`;
      }
      return;
    }

    if (status) {
      status.textContent = "Working…";
    }
    const openBackups = action === "reset" && !!document.getElementById("reset-open-backups")?.checked;
    const response = await fetch(`/workspace/${action}`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({phrase}),
    });

    if (response.ok) {
      const target = action === "reset"
        ? `/ui/workspace-reset?mode=reset${openBackups ? "&open=1" : ""}`
        : "/ui/workspace-reset?mode=delete";
      window.location.href = target;
      return;
    }

    let detail = "Action failed";
    try {
      const payload = await response.json();
      detail = typeof payload.detail === "string" ? payload.detail : detail;
    } catch (_error) {
      // Keep default detail.
    }
    if (status) {
      status.textContent = "✗ " + detail;
    }
  };

  window.runWorkspaceDanger = app.runWorkspaceDanger;
})();
