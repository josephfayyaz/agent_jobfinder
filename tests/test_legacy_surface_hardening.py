from __future__ import annotations

from collections.abc import Iterator

_VUE_HTML_MARKER = '<div id="app">'
_UNSAFE_KEY_PARTS = (
    "api_key",
    "token",
    "secret",
    "password",
    "credential",
    "private_key",
    "access_key",
    "refresh_token",
    "keyring",
    "absolute_path",
    "file_path",
    "pdflatex_path",
)
_UNSAFE_VALUE_PREFIXES = (
    "/Users/",
    "/home/",
    "/var/",
    "/tmp/",
    "/Library/",
    "~/",
    "file:",
)


def _walk_json(node: object, path: str = "$") -> Iterator[tuple[str, object]]:
    yield path, node
    if isinstance(node, dict):
        for key, value in node.items():
            yield from _walk_json(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _walk_json(value, f"{path}[{index}]")


def _unsafe_entries(payload: object) -> list[str]:
    hits: list[str] = []
    for path, node in _walk_json(payload):
        key_name = path.rsplit(".", 1)[-1].lower()
        if any(part in key_name for part in _UNSAFE_KEY_PARTS):
            hits.append(f"unsafe key at {path}")
        if isinstance(node, str):
            lowered = node.lower()
            if any(lowered.startswith(prefix.lower()) for prefix in _UNSAFE_VALUE_PREFIXES):
                hits.append(f"unsafe value at {path}: {node}")
    return hits


def test_dashboard_stays_json_and_hides_pdflatex_path(client) -> None:
    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "application/json" in response.headers.get("content-type", "")
    assert _VUE_HTML_MARKER not in response.text

    payload = response.json()
    assert "pdflatex_path" not in response.text
    assert payload["system"]["pdflatex_available"] in (True, False)
    assert _unsafe_entries(payload) == []


def test_health_stays_json_and_hides_pdflatex_path(client) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert "application/json" in response.headers.get("content-type", "")
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["pdflatex"]["available"] in (True, False)
    assert _unsafe_entries(payload) == []


def test_vue_dashboard_summary_still_hides_pdflatex_path(client) -> None:
    response = client.get("/api/vue/dashboard/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert "pdflatex_path" not in response.text
    assert _unsafe_entries(payload["data"]["sections"]["system"]) == []


def test_vue_health_contract_still_returns_json(client) -> None:
    response = client.get("/api/vue/health")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["ok"] is True


def test_app_dashboard_still_serves_vue_html_or_safe_503(client) -> None:
    response = client.get("/app/dashboard")

    assert response.status_code in (200, 503)
    if response.status_code == 200:
        assert "text/html" in response.headers.get("content-type", "")
        assert _VUE_HTML_MARKER in response.text
    else:
        assert response.headers["content-type"].startswith("application/json")


def test_ui_about_stays_legacy_html(client) -> None:
    response = client.get("/ui/about")

    assert response.status_code != 404
    assert _VUE_HTML_MARKER not in response.text


def test_dashboard_system_only_exposes_safe_status_fields(client) -> None:
    payload = client.get("/dashboard").json()
    assert set(payload["system"].keys()) == {
        "pdflatex_available",
        "lm_studio_online",
        "last_job_ingested",
    }
