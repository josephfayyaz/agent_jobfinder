function showToast(message, type = "info", duration = 3000) {
  const typeClass = {
    success: "toast--success",
    error: "toast--error",
    warning: "toast--info",
    info: "toast--info",
  };
  const toast = document.createElement("div");
  toast.dataset.toast = "1";
  toast.className = `toast ${typeClass[type] || "toast--info"}`;
  toast.textContent = message;
  const container = document.getElementById("toast-container");
  if (!container) {
    return;
  }
  container.appendChild(toast);
  if (duration > 0) {
    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateY(8px)";
      toast.style.transition = "opacity 0.28s ease, transform 0.28s ease";
    }, Math.max(duration - 300, 300));
    setTimeout(() => {
      toast.remove();
    }, duration);
  }
}

async function refreshAiBanner() {
  const banner = document.getElementById("ai-missing-banner");
  if (!banner) {
    return;
  }
  try {
    const response = await fetch("/health/ai-status", {cache: "no-store"});
    if (!response.ok) {
      return;
    }
    const data = await response.json();
    banner.classList.toggle("hidden", !!data.configured);
  } catch (_error) {
    // Ignore banner failures; page remains usable.
  }
}

function initNetworkMonitor() {
  const banner = document.getElementById("network-banner");
  if (!banner) {
    return;
  }

  let wasOffline = false;

  async function checkConnectivity() {
    if (navigator.onLine === false) {
      banner.classList.remove("hidden");
      wasOffline = true;
      return;
    }

    try {
      const response = await fetch("/health/connectivity", {cache: "no-store"});
      const data = response.ok ? await response.json() : {online: false};
      if (!data.online) {
        banner.classList.remove("hidden");
        wasOffline = true;
        return;
      }
    } catch (_error) {
      banner.classList.remove("hidden");
      wasOffline = true;
      return;
    }

    banner.classList.add("hidden");
    if (wasOffline) {
      showToast("Back online — cloud features resumed.", "success");
    }
    wasOffline = false;
  }

  window.addEventListener("online", checkConnectivity);
  window.addEventListener("offline", checkConnectivity);
  checkConnectivity();
  setInterval(checkConnectivity, 30_000);
}

document.addEventListener("htmx:afterRequest", (event) => {
  const xhr = event.detail.xhr;
  if (!xhr || !xhr.getResponseHeader) {
    return;
  }
  const success = xhr.getResponseHeader("X-Toast-Success");
  const error = xhr.getResponseHeader("X-Toast-Error");
  if (success) {
    showToast(success, "success");
  }
  if (error) {
    showToast(error, "error");
  }
});

document.addEventListener("htmx:responseError", (event) => {
  const xhr = event.detail.xhr;
  if (!xhr) {
    return;
  }
  const headerMessage = xhr.getResponseHeader ? xhr.getResponseHeader("X-Toast-Error") : "";
  if (headerMessage) {
    showToast(headerMessage, "error");
    return;
  }
  showToast(`Request failed (${xhr.status || "network error"}).`, "error");
});

document.addEventListener("DOMContentLoaded", () => {
  refreshAiBanner();
  initNetworkMonitor();
  fetch("/verified-facts/count")
    .then((response) => (response.ok ? response.json() : null))
    .then((data) => {
      if (!data || data.count <= 0) {
        return;
      }
      const badge = document.getElementById("vf-badge");
      if (!badge) {
        return;
      }
      badge.textContent = data.count;
    })
    .catch(() => {});
});
