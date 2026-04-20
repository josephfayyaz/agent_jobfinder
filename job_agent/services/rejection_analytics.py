from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session, joinedload

from job_agent.config import settings
from job_agent.models import Application

COMPLETED_STATUSES = {"applied", "responded", "phone_screen", "interview", "offer", "rejected", "discarded"}
RESPONSE_STATUSES = {"responded", "phone_screen", "interview", "offer"}
INTERVIEW_STATUSES = {"interview", "offer"}
STATUS_PRIORITY = {
    "offer": 5,
    "interview": 4,
    "responded": 3,
    "applied": 2,
    "rejected": 1,
    "discarded": 0,
}
SCORE_BUCKETS: list[tuple[str, int, int | None]] = [
    ("< 60", 0, 59),
    ("60-74", 60, 74),
    ("75-84", 75, 84),
    ("85-100", 85, 100),
]


def _safe_pct(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100.0, 2)


def _normalize_status(status: str) -> str:
    if status == "phone_screen":
        return "responded"
    if status == "discovered":
        return "applied"
    return status


def _bucket_for_score(score: float) -> tuple[str, int] | None:
    for label, threshold, upper in SCORE_BUCKETS:
        if upper is None and score >= threshold:
            return label, threshold
        if upper is not None and threshold <= score <= upper:
            return label, threshold
    return None


class RejectionAnalyticsService:
    def __init__(self, session: Session):
        self.session = session

    def aggregate(self, session: Session | None = None) -> dict:
        if session is not None:
            self.session = session
        return self.analyse()

    def analyse(self) -> dict:
        apps = (
            self.session.query(Application)
            .options(
                joinedload(Application.job_post),
                joinedload(Application.resume_draft),
                joinedload(Application.resume_track),
            )
            .filter(Application.status.notin_(["pending"]))
            .all()
        )

        if len(apps) < 5:
            raise ValueError("insufficient_data")

        total = len(apps)
        normalized_statuses = [_normalize_status(app.status or "") for app in apps]
        status_counts = Counter(normalized_statuses)
        responded_for_rate = sum(status_counts.get(status, 0) for status in RESPONSE_STATUSES)
        interview_for_rate = sum(status_counts.get(status, 0) for status in INTERVIEW_STATUSES)
        funnel = {
            "total": total,
            "applied": total,
            "responded": status_counts.get("responded", 0),
            "interview": status_counts.get("interview", 0),
            "offer": status_counts.get("offer", 0),
            "rejected": status_counts.get("rejected", 0),
            "discarded": status_counts.get("discarded", 0),
            "response_rate_pct": _safe_pct(responded_for_rate, total),
            "interview_rate_pct": _safe_pct(interview_for_rate, total),
            "offer_rate_pct": _safe_pct(status_counts.get("offer", 0), total),
        }

        bucket_stats: dict[str, dict[str, int]] = {
            label: {"count": 0, "response_count": 0, "interview_count": 0}
            for label, _, _ in SCORE_BUCKETS
        }
        threshold_by_bucket = {label: threshold for label, threshold, _ in SCORE_BUCKETS}
        for app in apps:
            draft = app.resume_draft
            if draft is None or draft.score is None:
                continue
            bucket = _bucket_for_score(float(draft.score))
            if bucket is None:
                continue
            label, _ = bucket
            bucket_stats[label]["count"] += 1
            normalized = _normalize_status(app.status or "")
            if normalized in RESPONSE_STATUSES:
                bucket_stats[label]["response_count"] += 1
            if normalized in INTERVIEW_STATUSES:
                bucket_stats[label]["interview_count"] += 1

        bucket_entries = [
            {
                "range": label,
                "count": bucket_stats[label]["count"],
                "response_count": bucket_stats[label]["response_count"],
                "interview_count": bucket_stats[label]["interview_count"],
            }
            for label, _, _ in SCORE_BUCKETS
        ]

        bucket_rates: list[tuple[str, int, float, int]] = []
        for entry in bucket_entries:
            count = entry["count"]
            rate = _safe_pct(entry["response_count"], count) if count else 0.0
            bucket_rates.append((entry["range"], threshold_by_bucket[entry["range"]], rate, count))

        recommended_threshold = int(settings.cv_pass_score)
        threshold_note = "No scored drafts available yet; using current threshold."
        viable_buckets = [item for item in bucket_rates if item[3] > 0 and item[2] >= 30.0]
        if viable_buckets:
            best = sorted(viable_buckets, key=lambda item: item[1])[0]
            recommended_threshold = best[1]
            threshold_note = (
                f"Bucket {best[0]} reaches a {best[2]:.1f}% response rate; "
                f"recommended threshold is {recommended_threshold}."
            )
        elif any(item[3] > 0 for item in bucket_rates):
            best = sorted(bucket_rates, key=lambda item: (item[2], item[3], item[1]), reverse=True)[0]
            recommended_threshold = best[1]
            threshold_note = (
                f"No bucket reached 30% response rate; best-performing bucket is {best[0]} "
                f"at {best[2]:.1f}% response."
            )

        score_analysis = {
            "buckets": bucket_entries,
            "recommended_threshold": recommended_threshold,
            "current_threshold": int(settings.cv_pass_score),
            "threshold_note": threshold_note,
        }

        by_track_stats: dict[str, dict[str, int | str]] = {}
        for app in apps:
            track_slug = app.resume_track.slug if app.resume_track is not None else "unknown"
            track_title = app.resume_track.title if app.resume_track is not None else "Unknown"
            if track_slug not in by_track_stats:
                by_track_stats[track_slug] = {
                    "track_slug": track_slug,
                    "track_title": track_title,
                    "applied": 0,
                    "responses": 0,
                }
            by_track_stats[track_slug]["applied"] = int(by_track_stats[track_slug]["applied"]) + 1
            if _normalize_status(app.status or "") in RESPONSE_STATUSES:
                by_track_stats[track_slug]["responses"] = int(by_track_stats[track_slug]["responses"]) + 1

        by_track = []
        for row in by_track_stats.values():
            applied = int(row["applied"])
            responses = int(row["responses"])
            by_track.append(
                {
                    "track_slug": row["track_slug"],
                    "track_title": row["track_title"],
                    "applied": applied,
                    "responses": responses,
                    "conversion_pct": _safe_pct(responses, applied),
                }
            )
        by_track.sort(key=lambda item: (item["conversion_pct"], item["applied"]), reverse=True)

        by_seniority_stats: dict[str, dict[str, int | str]] = {}
        for app in apps:
            seniority = (
                (app.job_post.seniority or "unknown").strip().lower()
                if app.job_post is not None
                else "unknown"
            ) or "unknown"
            if seniority not in by_seniority_stats:
                by_seniority_stats[seniority] = {
                    "seniority": seniority,
                    "applied": 0,
                    "responses": 0,
                }
            by_seniority_stats[seniority]["applied"] = int(by_seniority_stats[seniority]["applied"]) + 1
            if _normalize_status(app.status or "") in RESPONSE_STATUSES:
                by_seniority_stats[seniority]["responses"] = (
                    int(by_seniority_stats[seniority]["responses"]) + 1
                )

        by_seniority = []
        for row in by_seniority_stats.values():
            applied = int(row["applied"])
            responses = int(row["responses"])
            by_seniority.append(
                {
                    "seniority": row["seniority"],
                    "applied": applied,
                    "responses": responses,
                    "conversion_pct": _safe_pct(responses, applied),
                }
            )
        by_seniority.sort(key=lambda item: (item["conversion_pct"], item["applied"]), reverse=True)

        gap_counter: Counter[str] = Counter()
        for app in apps:
            if _normalize_status(app.status or "") != "rejected":
                continue
            draft = app.resume_draft
            if draft is None or not isinstance(draft.review_feedback, dict):
                continue
            gaps = draft.review_feedback.get("gaps") or []
            if not isinstance(gaps, list):
                continue
            for gap in gaps:
                text = str(gap).strip()
                if text:
                    gap_counter[text] += 1
        skill_gaps = [
            {"gap": gap, "occurrences": count}
            for gap, count in gap_counter.most_common(10)
        ]

        now = datetime.now(timezone.utc)
        window_start = now - timedelta(weeks=12)
        weekly_counter: defaultdict[str, int] = defaultdict(int)
        for app in apps:
            event_dt = app.applied_at or app.created_at
            if event_dt is None:
                continue
            if event_dt.tzinfo is None:
                event_dt = event_dt.replace(tzinfo=timezone.utc)
            if event_dt < window_start:
                continue
            iso = event_dt.isocalendar()
            key = f"{iso.year}-W{iso.week:02d}"
            weekly_counter[key] += 1
        weekly_activity = [
            {"week": week, "applied": count}
            for week, count in sorted(weekly_counter.items())
        ]

        company_statuses: defaultdict[str, list[str]] = defaultdict(list)
        company_counts: Counter[str] = Counter()
        for app in apps:
            company = (
                app.job_post.company.strip()
                if app.job_post is not None and app.job_post.company
                else "Unknown"
            )
            normalized = _normalize_status(app.status or "")
            if normalized not in COMPLETED_STATUSES:
                normalized = "applied"
            company_counts[company] += 1
            company_statuses[company].append(normalized)

        top_companies = []
        for company, applied in company_counts.most_common(10):
            statuses = company_statuses.get(company, [])
            best_status = "applied"
            if statuses:
                best_status = max(statuses, key=lambda status: STATUS_PRIORITY.get(status, 0))
            top_companies.append(
                {"company": company, "applied": applied, "best_status": best_status}
            )

        return {
            "funnel": funnel,
            "score_analysis": score_analysis,
            "by_track": by_track,
            "by_seniority": by_seniority,
            "skill_gaps": skill_gaps,
            "weekly_activity": weekly_activity,
            "top_companies": top_companies,
        }
