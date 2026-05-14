const NUMERIC_FIELDS = [
  "match_min_score",
  "discovery_min_fit_score",
  "discovery_max_visible_jobs",
  "cv_pass_score",
  "cv_revise_score",
  "bullet_clarify_word_limit",
];

export function splitLines(value) {
  return String(value || "")
    .split(/\n+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

export function roleLines(value) {
  return splitLines(value);
}

export function primaryCountry(value) {
  const countries = splitLines(value);
  return countries[0] || "Italy";
}

export function normalizeLanguageRows(rows) {
  const normalized = [];
  for (const row of Array.isArray(rows) ? rows : []) {
    const name = String(row?.name || "").trim();
    const level = String(row?.level || "professional").trim() || "professional";
    if (!name) continue;
    if (normalized.some((item) => item.name.toLowerCase() === name.toLowerCase())) continue;
    normalized.push({ name, level });
  }
  return normalized.length ? normalized : [{ name: "English", level: "professional" }];
}

export function parseInteger(value) {
  const parsed = parseInt(value, 10);
  return Number.isNaN(parsed) ? null : parsed;
}

function assignInteger(payload, key, value) {
  const parsed = parseInteger(value);
  if (parsed !== null) {
    payload[key] = parsed;
  }
}

export function buildSearchPayload(search) {
  const country = primaryCountry(search.countriesText);
  const payload = {
    target_job_seniority: search.targetSeniority,
    use_jobspy: Boolean(search.useJobspy),
    jobspy_discover_location: String(search.jobspyDiscoverLocation || country).trim() || country,
    job_search_countries: [country],
    jobspy_discover_queries: roleLines(search.rolesText),
    job_search_languages: normalizeLanguageRows(search.languages),
  };

  assignInteger(payload, "match_min_score", search.matchMinScore);
  assignInteger(payload, "discovery_min_fit_score", search.discoveryMinFitScore);
  assignInteger(payload, "discovery_max_visible_jobs", search.discoveryMaxVisibleJobs);
  return payload;
}

export function buildGmailPayload(gmail) {
  const payload = {
    gmail_label_filter: String(gmail.labelFilter || "").trim() || "LinkedIn Jobs",
    gmail_auto_sync: Boolean(gmail.autoSync),
  };
  const clientId = String(gmail.clientId || "").trim();
  const clientSecret = String(gmail.clientSecret || "").trim();
  if (clientId) {
    payload.gmail_oauth_client_id = clientId;
  }
  if (clientSecret) {
    payload.gmail_oauth_client_secret = clientSecret;
  }
  return payload;
}

export function buildCvPayload(cv) {
  const payload = {};
  assignInteger(payload, "cv_pass_score", cv.cvPassScore);
  assignInteger(payload, "cv_revise_score", cv.cvReviseScore);
  assignInteger(payload, "bullet_clarify_word_limit", cv.bulletClarifyWordLimit);
  return payload;
}

export function validateMaintenancePhrase(phrase, expectedPhrase) {
  const trimmed = String(phrase || "").trim();
  if (!trimmed) {
    return "Enter the confirmation phrase first.";
  }
  if (trimmed !== expectedPhrase) {
    return `Type exactly: ${expectedPhrase}`;
  }
  return "";
}

export { NUMERIC_FIELDS };
