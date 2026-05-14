import { apiFetch } from "./client";

function modelQuery(baseUrl) {
  const trimmed = String(baseUrl || "").trim();
  return trimmed ? `?base_url=${encodeURIComponent(trimmed)}` : "";
}

export function validateProvider(payload) {
  return apiFetch("/providers/validate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function fetchLmStudioModels(baseUrl) {
  return apiFetch(`/lm-studio/models${modelQuery(baseUrl)}`);
}

export function fetchOllamaModels(baseUrl) {
  return apiFetch(`/ollama/models${modelQuery(baseUrl)}`);
}

export function saveSettings(payload) {
  return apiFetch("/settings/save", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
