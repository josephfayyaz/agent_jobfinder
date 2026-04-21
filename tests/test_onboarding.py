from __future__ import annotations

from click.testing import CliRunner
import yaml

from job_agent.onboard import main


def test_onboarding_status_endpoint_unconfigured(client, tmp_path, monkeypatch):
    import job_agent.main as main_module

    monkeypatch.setattr(
        main_module,
        "_USER_SETTINGS_FILE",
        tmp_path / "config" / "user_settings.yml",
    )
    response = client.get("/onboarding/status")
    assert response.status_code == 200
    data = response.json()
    assert "configured" in data
    assert data["configured"] is False


def test_prerequisites_check_fails_gracefully(monkeypatch):
    """Docker not running should exit with a clear error."""

    class Result:
        returncode = 1

    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: Result())
    runner = CliRunner()
    result = runner.invoke(main, ["--non-interactive"])
    assert result.exit_code != 0
    assert "Docker" in result.output or "docker" in result.output


def test_write_default_candidate_id_replaces_existing_value(tmp_path):
    from job_agent.onboard import _write_default_candidate_id

    env_path = tmp_path / ".env"
    env_path.write_text("APP_ENV=development\nDEFAULT_CANDIDATE_ID=old-id\n", encoding="utf-8")

    _write_default_candidate_id("new-id", env_path=env_path)

    content = env_path.read_text(encoding="utf-8")
    assert "DEFAULT_CANDIDATE_ID=new-id" in content
    assert "DEFAULT_CANDIDATE_ID=old-id" not in content


def test_run_onboarding_overwrites_provider_settings(tmp_path, monkeypatch):
    import job_agent.onboard as onboard
    import job_agent.user_config as user_config

    settings_path = tmp_path / "config" / "user_settings.yml"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(
        "anthropic_api_key: sk-ant-old\n"
        "use_claude_final_review: true\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(user_config, "USER_SETTINGS_PATH", settings_path)
    monkeypatch.setattr(onboard, "USER_SETTINGS_PATH", settings_path)
    monkeypatch.setattr(onboard, "load_user_settings_overlay", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(onboard, "_run_prerequisites_check", lambda _url: (True, ["small-model", "writer-model"]))
    monkeypatch.setattr(onboard, "_fetch_lm_studio_models", lambda _url: (True, ["small-model", "writer-model"]))
    monkeypatch.setattr(onboard, "_server_is_running", lambda: False)

    def prompt_select(message, choices, *, default, non_interactive=False):
        if "Which AI provider" in message:
            return "Local LLM (LM Studio)"
        if "Small/review model" in message:
            return "small-model"
        if "Writer model" in message:
            return "writer-model"
        if "Mid/extraction model" in message:
            return "small-model"
        if "Target job seniority" in message:
            return "junior"
        return default

    def prompt_text(message, *, default="", non_interactive=False):
        if "Primary location" in message:
            return "Italy"
        if "Job titles to search" in message:
            return "AI Engineer, Data Engineer"
        if "Path to your fact sheet" in message:
            return ""
        return default

    def prompt_confirm(message, *, default=True, non_interactive=False):
        if "Re-run setup?" in message:
            return True
        if "Enable automatic JobSpy discovery?" in message:
            return False
        if "Save these settings?" in message:
            return True
        return default

    monkeypatch.setattr(onboard, "_prompt_select", prompt_select)
    monkeypatch.setattr(onboard, "_prompt_text", prompt_text)
    monkeypatch.setattr(onboard, "_prompt_confirm", prompt_confirm)
    monkeypatch.setattr(onboard, "_prompt_int_range", lambda *args, **kwargs: 75)

    onboard.run_onboarding(non_interactive=False)

    data = yaml.safe_load(settings_path.read_text(encoding="utf-8"))
    assert data["anthropic_api_key"] == ""
    assert data["use_claude_final_review"] is False
    assert data["lm_studio_small_model"] == "small-model"
    assert data["lm_studio_writer_model"] == "writer-model"
