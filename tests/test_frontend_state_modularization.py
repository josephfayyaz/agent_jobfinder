from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_core_state_uses_nested_buckets():
    text = _read("frontend/static/onboarding/core.js")
    assert "provider:" in text
    assert "intake:" in text
    assert "review:" in text
    assert "search:" in text
    assert "ui:" in text


def test_step_files_reference_nested_state_buckets():
    intake = _read("frontend/static/onboarding/intake.js")
    hydrate = _read("frontend/static/onboarding/hydrate.js")
    review = _read("frontend/static/onboarding/review.js")
    search = _read("frontend/static/onboarding/search.js")
    assert "app.state.intake" in intake
    assert "app.state.intake" in hydrate
    assert "app.state.review" in review
    assert "app.state.search" in search
    assert "app.state.ui" in _read("frontend/static/onboarding/core.js")


def test_flat_legacy_state_fields_are_removed_from_step_files():
    for relative_path in (
        "frontend/static/onboarding/intake.js",
        "frontend/static/onboarding/hydrate.js",
        "frontend/static/onboarding/review.js",
        "frontend/static/onboarding/search.js",
    ):
        text = _read(relative_path)
        assert "app.state.candidateId" not in text
        assert "app.state.reviewFactSheet" not in text
        assert "app.state.searchRecommendationsLoaded" not in text
