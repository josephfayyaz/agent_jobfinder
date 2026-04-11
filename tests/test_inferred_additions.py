from __future__ import annotations

import json

from job_agent.models import ResumeDraft


def test_inferred_additions_not_auto_merged_into_body(db_session, db_job, db_track):
    draft = ResumeDraft(
        job_post_id=db_job.id,
        resume_track_id=db_track.id,
        content={"professional_summary": "Clean draft body with no additions."},
        inferred_additions=[
            {
                "id": "add_1",
                "tier": "skill",
                "text": "Kafka consumer experience",
                "reason": "candidate uses Python + streaming tools",
                "confidence": "med",
                "attached_to": "skills",
            }
        ],
    )
    db_session.add(draft)
    db_session.commit()

    assert "Kafka" not in json.dumps(draft.content)


def test_accept_inferred_additions_endpoint_merges_into_body(client, db_session, db_job, db_track):
    draft = ResumeDraft(
        job_post_id=db_job.id,
        resume_track_id=db_track.id,
        content={"selected_skills": [], "selected_experiences": [], "selected_projects": [], "tailoring_notes": []},
        inferred_additions=[
            {
                "id": "add_1",
                "tier": "skill",
                "text": "Kafka",
                "reason": "plausible",
                "confidence": "high",
                "attached_to": "skills",
            }
        ],
    )
    db_session.add(draft)
    db_session.commit()

    response = client.post(
        f"/drafts/{draft.id}/inferred-additions/accept",
        json={"accepted_ids": ["add_1"]},
    )

    assert response.status_code == 200
    assert response.json()["accepted"] == 1
    db_session.refresh(draft)
    assert draft.accepted_inferred_additions is not None
    assert len(draft.accepted_inferred_additions) == 1
    assert "Kafka" in draft.content["selected_skills"]


def test_reject_inferred_additions_endpoint_drops_items(client, db_session, db_job, db_track):
    draft = ResumeDraft(
        job_post_id=db_job.id,
        resume_track_id=db_track.id,
        content={"professional_summary": "Base draft."},
        inferred_additions=[
            {
                "id": "add_1",
                "tier": "tool",
                "text": "dbt",
                "reason": "SQL transforms",
                "confidence": "med",
                "attached_to": "skills",
            },
            {
                "id": "add_2",
                "tier": "metric",
                "text": "reduced latency 30%",
                "reason": "plausible based on ETL work",
                "confidence": "low",
                "attached_to": "experience[0]",
            },
        ],
    )
    db_session.add(draft)
    db_session.commit()

    response = client.post(
        f"/drafts/{draft.id}/inferred-additions/reject",
        json={"rejected_ids": ["add_1"]},
    )

    assert response.status_code == 200
    db_session.refresh(draft)
    assert len(draft.inferred_additions) == 1
    assert draft.inferred_additions[0]["id"] == "add_2"


def test_get_inferred_additions_endpoint_returns_pending_list(client, db_session, db_job, db_track):
    draft = ResumeDraft(
        job_post_id=db_job.id,
        resume_track_id=db_track.id,
        content={"professional_summary": "Draft."},
        inferred_additions=[{"id": "add_1", "tier": "skill", "text": "Ray"}],
    )
    db_session.add(draft)
    db_session.commit()

    response = client.get(f"/drafts/{draft.id}/inferred-additions")

    assert response.status_code == 200
    assert len(response.json()["inferred_additions"]) == 1


def test_rejected_additions_do_not_appear_in_accepted(client, db_session, db_job, db_track):
    draft = ResumeDraft(
        job_post_id=db_job.id,
        resume_track_id=db_track.id,
        content={"professional_summary": "Draft."},
        inferred_additions=[{"id": "add_1", "tier": "skill", "text": "Flink"}],
    )
    db_session.add(draft)
    db_session.commit()

    client.post(f"/drafts/{draft.id}/inferred-additions/reject", json={"rejected_ids": ["add_1"]})
    db_session.refresh(draft)

    assert (draft.accepted_inferred_additions or []) == []


def test_writer_response_inferred_additions_parsed_into_draft():
    raw = json.dumps(
        {
            "summary": "Data engineer.",
            "experience": [],
            "projects": [],
            "education": [],
            "skills": {},
            "inferred_additions": [
                {
                    "id": "add_1",
                    "tier": "tool",
                    "text": "Great Expectations",
                    "reason": "data quality tool adjacent to ETL work",
                    "attached_to": "skills",
                    "confidence": "high",
                }
            ],
        }
    )

    data = json.loads(raw)
    additions = data.pop("inferred_additions", [])

    assert "inferred_additions" not in data
    assert len(additions) == 1
    assert additions[0]["id"] == "add_1"
