import { apiFetch, vueApiFetch } from "./client";

export function fetchSettings() {
  return vueApiFetch("/settings");
}

export function saveSettings(payload) {
  return apiFetch("/settings/save", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function fetchSearchRecommendations({ candidateId, countries } = {}) {
  const params = new URLSearchParams();
  if (candidateId) params.set("candidate_id", candidateId);
  if (countries) params.set("countries", countries);
  const suffix = params.toString();
  return apiFetch(`/search/preferences/recommendations${suffix ? `?${suffix}` : ""}`);
}

export function connectGmailOAuth() {
  return apiFetch("/gmail/oauth/start", { method: "POST" });
}

export function disconnectGmailOAuth() {
  return apiFetch("/gmail/oauth/disconnect", { method: "POST" });
}

export function reloadSettings() {
  return apiFetch("/settings/reload", { method: "POST" });
}

export function runWorkspaceAction(action, phrase) {
  return apiFetch(`/workspace/${action}`, {
    method: "POST",
    body: JSON.stringify({ phrase }),
  });
}
