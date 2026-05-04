"""Tests that lifespan handles startup failures gracefully."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


def test_lifespan_raises_when_prepare_database_fails():
    """If prepare_database() raises, lifespan must re-raise (not swallow)."""
    from job_agent.main import lifespan

    async def _run():
        fake_app = MagicMock()
        with patch("job_agent.main.prepare_database", side_effect=RuntimeError("disk full")):
            with patch("job_agent.main._onboarding_complete", return_value=True):
                async with lifespan(fake_app):
                    pass

    with pytest.raises(RuntimeError, match="disk full"):
        import asyncio

        asyncio.run(_run())


def test_lifespan_continues_when_seed_fails(caplog):
    """If seed_reference_data() raises, lifespan must log warning but not crash."""
    import logging
    from job_agent.main import lifespan

    async def _run():
        fake_app = MagicMock()
        with patch("job_agent.main.prepare_database"):
            with patch("job_agent.main._onboarding_complete", return_value=True):
                with patch("job_agent.main.seed_reference_data", side_effect=Exception("seed failed")):
                    with patch("job_agent.main.get_db") as mock_get_db:
                        mock_session = MagicMock()
                        mock_get_db.return_value = iter([mock_session])
                        async with lifespan(fake_app):
                            pass

    with caplog.at_level(logging.WARNING, logger="job_agent.main"):
        import asyncio

        asyncio.run(_run())

    assert any("seed" in rec.message.lower() for rec in caplog.records)
