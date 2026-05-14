import { apiFetch, vueApiFetch } from "../api/client";

async function responseDetail(response, fallback) {
  const contentType = response.headers.get("content-type") || "";
  const text = await response.text();

  if (contentType.includes("application/json") && text) {
    try {
      const payload = JSON.parse(text);
      return payload.detail || payload.message || fallback;
    } catch {
      return fallback;
    }
  }

  return text || fallback;
}

export async function legacyFetchJson(path, options = {}, fallback = "Request failed.") {
  const response = await fetch(path, {
    credentials: "same-origin",
    ...options,
  });

  if (!response.ok) {
    throw new Error(await responseDetail(response, fallback));
  }

  const contentType = response.headers.get("content-type") || "";

  if (response.status === 204) return null;
  if (contentType.includes("application/json")) return response.json();

  return response.text();
}

export function loadOnboardingStateBundle() {
  return Promise.all([
    vueApiFetch("/onboarding/state"),
    vueApiFetch("/onboarding/steps"),
    vueApiFetch("/setup/state"),
  ]);
}

export function validateProvider(payload) {
  return apiFetch("/providers/validate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function saveSettings(payload) {
  return apiFetch("/settings/save", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function ensureCandidateShellApi() {
  return apiFetch("/candidates/ensure-owner", { method: "POST" });
}

export function uploadCandidateSources(candidateId, formData) {
  return legacyFetchJson(
    `/candidates/${candidateId}/sources/upload`,
    { method: "POST", body: formData },
    "Uploading source files failed.",
  );
}

export function startCandidateIntake(candidateId, notes) {
  return legacyFetchJson(
    `/candidates/${candidateId}/intake/start`,
    {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ profile_notes: notes }),
    },
    "The AI provider could not complete intake. Check your provider key in Settings.",
  );
}

export function answerCandidateIntake(candidateId, answers) {
  return apiFetch(`/candidates/${candidateId}/intake/answer`, {
    method: "POST",
    body: JSON.stringify({ answers }),
  });
}

export function loadCandidateReview(candidateId) {
  return apiFetch(`/candidates/${candidateId}/onboarding-review`);
}

export function saveCandidateFactSheet(candidateId, payload) {
  return apiFetch(`/candidates/${candidateId}/fact-sheet-json`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function loadSearchRecommendations(candidateId) {
  return apiFetch(
    `/search/preferences/recommendations?candidate_id=${encodeURIComponent(candidateId)}`,
  );
}

export function suggestCandidateTracks(candidateId) {
  return apiFetch(`/candidates/${encodeURIComponent(candidateId)}/suggest-tracks`, {
    method: "POST",
  });
}

export function generateCandidateTracks(candidateId, roles) {
  return apiFetch(`/candidates/${encodeURIComponent(candidateId)}/generate-tracks`, {
    method: "POST",
    body: JSON.stringify({ roles }),
  });
}
