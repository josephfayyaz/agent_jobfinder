from __future__ import annotations


def test_ui_analytics_returns_200(client, monkeypatch):
    monkeypatch.setattr(
        "job_agent.main.RejectionAnalyticsService.aggregate",
        lambda self, db: {
            "total_applications": 10,
            "funnel": {"discovered": 10, "applied": 7, "responded": 3, "offer": 1, "rejected": 2},
            "score_buckets": {"90-100": 2, "75-89": 4, "50-74": 3, "below-50": 1},
            "by_track": {"data-engineer": 5},
            "skill_gaps": [{"keyword": "Kubernetes", "miss_count": 3}],
            "weekly_activity": [{"week": "2026-04-14", "count": 3}],
            "top_companies": [{"company": "Acme", "count": 2}],
        },
    )

    response = client.get("/ui/analytics")

    assert response.status_code == 200
    assert "Kubernetes" in response.text


def test_ui_analytics_shows_empty_state(client, monkeypatch):
    monkeypatch.setattr(
        "job_agent.main.RejectionAnalyticsService.aggregate",
        lambda self, db: (_ for _ in ()).throw(ValueError("insufficient_data")),
    )

    response = client.get("/ui/analytics")

    assert response.status_code == 200
    assert "Not enough data" in response.text


def test_ui_analytics_velocity_section_renders(client, monkeypatch):
    monkeypatch.setattr(
        "job_agent.main.RejectionAnalyticsService.aggregate",
        lambda self, db: (_ for _ in ()).throw(ValueError("insufficient_data")),
    )

    response = client.get("/ui/analytics")

    assert response.status_code == 200
    assert "Posting Velocity" in response.text
