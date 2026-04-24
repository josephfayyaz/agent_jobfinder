document.addEventListener("DOMContentLoaded", async () => {
  try {
    const response = await fetch("/career-pages/velocity/bulk");
    if (!response.ok) {
      return;
    }
    const payload = await response.json();
    const surgingSet = new Set((payload.surging || []).map((id) => Number(id)));
    document.querySelectorAll("[data-source-id]").forEach((row) => {
      const sourceId = Number(row.dataset.sourceId);
      if (!surgingSet.has(sourceId)) {
        return;
      }
      const nameEl = row.querySelector(".company-name");
      if (!nameEl || nameEl.querySelector("[data-velocity-badge]")) {
        return;
      }

      const badge = document.createElement("span");
      badge.dataset.velocityBadge = "true";
      badge.title = "Hiring surge — new roles posted in 2+ recent scans";
      badge.className = "ml-2 text-sm text-yellow-500";
      badge.textContent = "⚡";
      nameEl.appendChild(badge);
    });
  } catch (_error) {
    // Velocity badges are a non-blocking enhancement.
  }
});

function submitAddCompany(event) {
  event.preventDefault();
  const form = event.target;
  const error = document.getElementById("add-company-error");
  const params = new URLSearchParams({
    company: form.company.value,
    career_url: form.career_url.value,
    country: form.country.value || "Italy",
  });
  if (form.ats_type.value) {
    params.set("ats_type", form.ats_type.value);
  }
  if (form.ats_slug.value) {
    params.set("ats_slug", form.ats_slug.value);
  }

  fetch("/career-pages?" + params.toString(), {method: "POST"})
    .then(async (response) => {
      if (response.ok || response.status === 201) {
        window.location.reload();
        return;
      }
      const payload = await response.json().catch(() => ({detail: "Failed to add company."}));
      const detail = typeof payload.detail === "string" ? payload.detail : "Failed to add company.";
      error.textContent = detail;
      error.classList.remove("hidden");
    })
    .catch(() => {
      error.textContent = "Failed to add company.";
      error.classList.remove("hidden");
    });
}
