function showToast(message, type) {
  const colors = {
    success: "bg-green-600",
    error: "bg-red-600",
    info: "bg-slate-700",
  };
  const toast = document.createElement("div");
  toast.className = `pointer-events-auto px-4 py-2.5 rounded-lg text-white text-sm shadow-lg transition-opacity duration-300 ${colors[type] || colors.info}`;
  toast.textContent = message;
  const container = document.getElementById("toast-container");
  if (!container) {
    return;
  }
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
  }, 2700);
  setTimeout(() => {
    toast.remove();
  }, 3000);
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

document.addEventListener("DOMContentLoaded", () => {
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
      badge.classList.remove("hidden");
    })
    .catch(() => {});
});
