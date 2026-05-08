export async function apiFetch(path, options = {}) {
  const response = await fetch(path, {
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    },
    ...options
  });

  const contentType = response.headers.get("content-type") || "";

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;

    if (contentType.includes("application/json")) {
      const payload = await response.json();
      message = payload.detail || payload.message || payload.error?.message || message;
    } else {
      const text = await response.text();
      message = text || message;
    }

    throw new Error(message);
  }

  if (response.status === 204) {
    return null;
  }

  if (contentType.includes("application/json")) {
    return response.json();
  }

  return response.text();
}

export async function vueApiFetch(path, options = {}) {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return apiFetch(`/api/vue${normalizedPath}`, options);
}
