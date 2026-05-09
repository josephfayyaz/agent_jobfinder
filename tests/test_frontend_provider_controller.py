from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_provider_controller_file_exists_and_exports_global():
    text = _read("frontend/static/provider_controller.js")
    assert "window.ProviderController" in text
    assert "buildProviderFlags" in text
    assert "buildValidationPayload" in text
    assert "buildBaseSavePayload" in text
    assert "applyLocalProviderModels" in text


def test_onboarding_and_settings_load_shared_provider_controller():
    onboarding = _read("frontend/templates/onboarding.html")
    settings = _read("frontend/templates/settings.html")
    assert "/static/provider_controller.js" in onboarding
    assert "/static/provider_controller.js" in settings


def test_onboarding_and_settings_use_shared_provider_controller():
    onboarding_intake = _read("frontend/static/onboarding/intake.js")
    settings_provider = _read("frontend/static/settings/provider.js")
    assert "providerController.buildValidationPayload" in onboarding_intake
    assert "providerController.buildBaseSavePayload" in onboarding_intake
    assert "providerController.validateProvider" in onboarding_intake
    assert "providerController.buildValidationPayload" in settings_provider
    assert "providerController.buildBaseSavePayload" in settings_provider
    assert "providerController.validateProvider" in settings_provider
