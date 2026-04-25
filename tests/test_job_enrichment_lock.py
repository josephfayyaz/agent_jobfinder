from __future__ import annotations


def test_queue_cv_blocks_when_job_needs_input(client, db_session, db_job, db_track):
    from job_agent.models import JobPost

    job = db_session.get(JobPost, db_job.id)
    job.enrichment_status = "needs_input"
    job.description = ""
    job.role_track_hint = db_track.slug
    db_session.add(job)
    db_session.commit()

    response = client.post(f"/ui/jobs/{job.id}/queue-cv?resume_track_slug={db_track.slug}")

    assert response.status_code == 409
    assert response.headers["X-Toast-Error"].startswith("This job still needs a real description")
