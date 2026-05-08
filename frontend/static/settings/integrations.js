/*
 * Integration settings controller.
 */

(() => {
  const app = window.SettingsApp;

  app.connectGmailOAuth = async function connectGmailOAuth() {
    const form = document.getElementById("gmail-form");
    const status = document.getElementById("gmail-status");
    if (!form || !status) {
      return;
    }

    status.textContent = "Saving OAuth settings…";
    const gmailEntries = app.readGmailEntries(form);
    const savePayload = {
      gmail_label_filter: (form.elements.gmail_label_filter?.value || "").trim(),
      gmail_auto_sync: !!form.elements.gmail_auto_sync?.checked,
    };
    if (gmailEntries.clientId) {
      savePayload.gmail_oauth_client_id = gmailEntries.clientId;
    }
    if (gmailEntries.clientEntry) {
      savePayload.gmail_oauth_client_secret = gmailEntries.clientEntry;
    }
    if (!gmailEntries.clientId && form.dataset.gmailOauthConfigured !== "true") {
      status.textContent = "Paste OAuth Client ID first.";
      return;
    }

    const saveResp = await fetch("/settings/save", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(savePayload),
    });
    if (!saveResp.ok) {
      status.textContent = "✗ Could not save OAuth settings";
      return;
    }

    status.textContent = "Opening Google consent…";
    const response = await fetch("/gmail/oauth/start", {method: "POST"});
    const payload = await response.json();
    if (!response.ok || !payload.auth_url) {
      status.textContent = "✗ " + (payload.detail || "Could not start OAuth flow");
      return;
    }
    window.location.href = payload.auth_url;
  };

  app.disconnectGmailOAuth = async function disconnectGmailOAuth() {
    const status = document.getElementById("gmail-status");
    if (status) {
      status.textContent = "Disconnecting…";
    }
    const response = await fetch("/gmail/oauth/disconnect", {method: "POST"});
    if (response.ok) {
      if (status) {
        status.textContent = "✓ Gmail disconnected";
      }
      window.location.reload();
      return;
    }
    if (status) {
      status.textContent = "✗ Disconnect failed";
    }
  };

  app.reloadSettings = async function reloadSettings() {
    const response = await fetch("/settings/reload", {method: "POST"});
    const status = document.getElementById("system-status");
    if (!status) {
      return;
    }
    status.textContent = response.ok ? "✓ Reloaded" : "✗ Failed";
  };

  window.connectGmailOAuth = app.connectGmailOAuth;
  window.disconnectGmailOAuth = app.disconnectGmailOAuth;
  window.reloadSettings = app.reloadSettings;
})();
