from __future__ import annotations

from pathlib import Path

from job_agent.services.exporters import CsvExportService


def test_export_creates_csv_file(db_session, db_job, monkeypatch, tmp_path):
    del db_job
    monkeypatch.setattr("job_agent.services.exporters.settings.artifacts_dir", tmp_path)

    export = CsvExportService(db_session).export_jobs_snapshot()
    file_path = Path(export.file_path)

    assert file_path.exists()
    assert file_path.suffix == ".csv"


def test_export_csv_has_header_row(db_session, db_job, monkeypatch, tmp_path):
    del db_job
    monkeypatch.setattr("job_agent.services.exporters.settings.artifacts_dir", tmp_path)

    export = CsvExportService(db_session).export_jobs_snapshot()
    first_line = Path(export.file_path).read_text(encoding="utf-8").splitlines()[0].lower()

    assert "job_title" in first_line
    assert "company_name" in first_line


def test_export_csv_contains_job_data(db_session, db_job, monkeypatch, tmp_path):
    monkeypatch.setattr("job_agent.services.exporters.settings.artifacts_dir", tmp_path)

    export = CsvExportService(db_session).export_jobs_snapshot()
    content = Path(export.file_path).read_text(encoding="utf-8")

    assert db_job.company in content or db_job.title in content


def test_export_empty_db_produces_header_only(db_session, monkeypatch, tmp_path):
    monkeypatch.setattr("job_agent.services.exporters.settings.artifacts_dir", tmp_path)

    export = CsvExportService(db_session).export_jobs_snapshot()
    lines = Path(export.file_path).read_text(encoding="utf-8").splitlines()

    assert len(lines) == 1
