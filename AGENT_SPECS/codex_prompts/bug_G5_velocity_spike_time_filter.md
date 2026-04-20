# Bug Fix — G5: `check_velocity_spikes` missing time filter

## Problem

`CareerPageScanner.check_velocity_spikes()` in
`job_agent/services/career_scanner.py` has **no time boundary** on its query:

```python
logs = (
    session.query(CareerPageScanLog)
    .filter(CareerPageScanLog.new_jobs >= threshold)
    .order_by(CareerPageScanLog.scanned_at.desc())
    .limit(20)
    .all()
)
```

This returns **all historical** `CareerPageScanLog` rows where `new_jobs >=
threshold`, not just recent ones. The worker calls this after every career scan
cycle and logs a `WARNING` for every returned row — so old spikes from weeks ago
are re-alerted indefinitely on every cycle.

The spec intent (G5) was "sources where the **latest** scan had new_jobs >=
threshold."

---

## Fix: one file, ~5 lines

**File:** `job_agent/services/career_scanner.py`

Add a `datetime` import at the top if not already present (it is — `datetime,
timezone` already imported at line 6). Add `timedelta`.

In `check_velocity_spikes()`, add a `cutoff` filter — 2 hours is appropriate
because the worker's `_CAREER_SCAN_INTERVAL` is 86 400 s (24 h); using 2 h
ensures we only surface spikes from the most recent scan run without triggering
on the current run's full window:

```python
from datetime import datetime, timedelta, timezone

def check_velocity_spikes(self, session: Session) -> list[dict]:
    """
    Return sources where the most recent scan had new_jobs >= velocity_spike_threshold.
    Only considers scan logs from the last 2 hours to avoid re-alerting old spikes.
    """
    from job_agent.config import get_settings

    threshold = get_settings().velocity_spike_threshold
    cutoff = datetime.now(timezone.utc) - timedelta(hours=2)
    logs = (
        session.query(CareerPageScanLog)
        .filter(
            CareerPageScanLog.new_jobs >= threshold,
            CareerPageScanLog.scanned_at >= cutoff,
        )
        .order_by(CareerPageScanLog.scanned_at.desc())
        .limit(20)
        .all()
    )
    spikes = []
    for log in logs:
        source = session.get(CareerPageSource, log.source_id)
        spikes.append(
            {
                "company": source.company if source else "unknown",
                "new_jobs": log.new_jobs,
                "scanned_at": log.scanned_at.isoformat(),
                "career_url": source.career_url if source else "",
            }
        )
    return spikes
```

**No DB migration needed.** `scanned_at` already has an index
(`ix_career_page_scan_logs_scanned_at`) from the F5+G5 implementation.

---

## Tests to add

File: `tests/test_ats_scanner.py`

### Test 1 — old spike not returned

```python
def test_velocity_spike_old_log_excluded(monkeypatch, db_session):
    """Logs older than 2 hours must NOT trigger a spike alert."""
    from datetime import datetime, timedelta, timezone
    from job_agent.config import settings

    monkeypatch.setattr(settings, "velocity_spike_threshold", 3)
    source = _create_source(db_session, company="OldCo")
    old_time = datetime.now(timezone.utc) - timedelta(hours=3)
    log = CareerPageScanLog(source_id=source.id, jobs_found=10, new_jobs=8)
    db_session.add(log)
    db_session.commit()
    # back-date scanned_at after commit (default is server_default now())
    log.scanned_at = old_time
    db_session.commit()

    spikes = CareerPageScanner().check_velocity_spikes(db_session)

    assert spikes == []
```

### Test 2 — recent spike is returned

```python
def test_velocity_spike_recent_log_included(monkeypatch, db_session):
    """Logs within the last 2 hours above threshold MUST be returned."""
    from job_agent.config import settings

    monkeypatch.setattr(settings, "velocity_spike_threshold", 3)
    source = _create_source(db_session, company="RecentCo")
    db_session.add(CareerPageScanLog(source_id=source.id, jobs_found=6, new_jobs=5))
    db_session.commit()

    spikes = CareerPageScanner().check_velocity_spikes(db_session)

    assert len(spikes) == 1
    assert spikes[0]["company"] == "RecentCo"
```

---

## Acceptance Criteria

- `test_velocity_spike_old_log_excluded` passes (old log not returned).
- `test_velocity_spike_recent_log_included` passes (recent log returned).
- The two existing tests (`test_check_velocity_spikes_returns_spikes_above_threshold`,
  `test_velocity_spike_threshold_filters_below_threshold`) continue to pass —
  they add logs without back-dating so `scanned_at` defaults to `now()`.
- `ruff check` clean.
- Full test suite still passes.
