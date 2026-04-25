"""Tests for Gmail LinkedIn alert ingestion helpers."""

from __future__ import annotations

from email.message import EmailMessage
from unittest.mock import Mock

from job_agent.services.gmail import GmailService, _extract_job_cards, _get_html_body


def test_get_html_body_extracts_html_part():
    msg = EmailMessage()
    msg.set_content("Plain text")
    msg.add_alternative("<html><body><p>Hello</p></body></html>", subtype="html")

    assert _get_html_body(msg) == "<html><body><p>Hello</p></body></html>\n"


def test_extract_job_cards_returns_unique_clean_urls():
    html = """
    <html><body>
      <table>
        <tr><td>
          <a href="https://www.linkedin.com/jobs/view/12345?tracking=abc">Data Engineer</a>
          <div>Acme</div>
          <div>Milan, Italy</div>
        </td></tr>
        <tr><td>
          <a href="https://www.linkedin.com/jobs/view/12345?tracking=xyz">Data Engineer</a>
          <div>Acme</div>
          <div>Milan, Italy</div>
        </td></tr>
      </table>
    </body></html>
    """

    cards = _extract_job_cards(html)

    assert cards == [
        {
            "title": "Data Engineer",
            "company": "Acme",
            "location": "Milan, Italy",
            "url": "https://www.linkedin.com/jobs/view/12345",
        }
    ]


def test_sync_jobs_skips_when_not_configured(monkeypatch):
    service = GmailService()
    monkeypatch.setattr(service.settings, "gmail_email", "")
    monkeypatch.setattr(service.settings, "gmail_app_password", "")
    monkeypatch.setattr(service.oauth, "is_connected", lambda: False)

    session = Mock()

    assert service.sync_jobs(session) == []
    session.query.assert_not_called()
