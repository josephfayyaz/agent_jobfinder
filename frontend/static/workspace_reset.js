async function openBackupFolder() {
  const status = document.getElementById("backup-open-status");
  if (status) {
    status.textContent = "Opening backup folder…";
  }
  const response = await fetch("/workspace/backups/open", {method: "POST"});
  if (response.ok) {
    if (status) {
      status.textContent = "✓ Backup folder opened";
    }
    return;
  }
  let detail = "Could not open the backup folder automatically.";
  try {
    const payload = await response.json();
    if (typeof payload.detail === "string" && payload.detail.trim()) {
      detail = payload.detail;
    }
  } catch (_error) {
    // Keep fallback detail.
  }
  if (status) {
    status.textContent = "✗ " + detail;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const page = document.getElementById("workspace-reset-page");
  if (!page) {
    return;
  }
  if (page.dataset.autoOpenBackups === "1") {
    openBackupFolder();
  }
});
