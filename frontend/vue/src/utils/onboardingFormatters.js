export function formatFileSize(size) {
  const bytes = Number(size) || 0;

  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;

  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export function splitLines(value) {
  return String(value || "")
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}

export function clonePlainObject(value) {
  return JSON.parse(JSON.stringify(value || {}));
}
