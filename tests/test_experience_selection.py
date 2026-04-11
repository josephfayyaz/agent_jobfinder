from __future__ import annotations

from unittest.mock import MagicMock


def _make_exp(title, org, bullets, start_date="2022-01", keywords=None):
    exp = MagicMock()
    exp.title = title
    exp.organization = org
    exp.bullets = bullets
    exp.start_date = start_date
    exp.end_date = None
    exp.keywords = keywords or []
    return exp


def _make_job(title="Data Engineer", description="Python ETL Airflow Spark"):
    job = MagicMock()
    job.title = title
    job.description = description
    return job


def test_select_experiences_for_job_returns_top_relevant_roles():
    from job_agent.services.experience_selection import select_experiences_for_job

    experiences = [
        _make_exp("Data Engineer", "Corp A", ["built ETL pipelines with Airflow", "Python"], "2023-01"),
        _make_exp("Marketing Coordinator", "Corp B", ["organized events", "managed budget"], "2021-01"),
        _make_exp("ML Engineer", "Corp C", ["trained models", "Python TensorFlow"], "2022-06"),
    ]

    results = select_experiences_for_job(experiences, _make_job(), ["python", "airflow"], "junior")

    assert len(results) >= 2
    assert results[0].experience_fact.title == "Data Engineer" or any(
        result.experience_fact.title == "Data Engineer" for result in results
    )


def test_select_experiences_for_job_preserves_minimum_three_roles():
    from job_agent.services.experience_selection import select_experiences_for_job

    experiences = [_make_exp(f"Role {index}", f"Org {index}", ["did work"], f"202{index}-01") for index in range(5)]

    results = select_experiences_for_job(experiences, _make_job(description="generic work"), [], "junior")

    assert len(results) >= 3


def test_select_experiences_drops_at_most_one_role_per_job():
    from job_agent.services.experience_selection import select_experiences_for_job

    experiences = [
        _make_exp("Data Engineer", "Org", ["python airflow etl"], "2023-01"),
        _make_exp("Data Analyst", "Org", ["sql analytics python"], "2022-01"),
        _make_exp("ML Engineer", "Org", ["python tensorflow"], "2021-01"),
        _make_exp("Backend Engineer", "Org", ["python fastapi"], "2020-01"),
        _make_exp("Waiter", "Restaurant", ["served food cleaned tables"], "2018-01"),
    ]

    results = select_experiences_for_job(
        experiences,
        _make_job(description="Python ETL data pipelines"),
        ["python", "etl"],
        "junior",
        max_roles=5,
    )

    dropped = 5 - len(results)
    assert dropped <= 1


def test_select_bullets_keeps_2_to_3_for_junior_mode():
    from job_agent.services.experience_selection import select_experiences_for_job

    experiences = [
        _make_exp(
            "Data Engineer",
            "Org",
            [
                "built airflow pipelines",
                "wrote python etl scripts",
                "optimized sql queries",
                "maintained spark jobs",
            ],
            "2023-01",
        ),
    ]

    results = select_experiences_for_job(experiences, _make_job(), ["airflow", "python"], "junior")

    assert len(results) == 1
    assert 2 <= len(results[0].selected_bullets) <= 3


def test_select_bullets_keeps_3_to_4_for_senior_mode():
    from job_agent.services.experience_selection import select_experiences_for_job

    experiences = [
        _make_exp(
            "Senior Data Engineer",
            "Org",
            [
                "led team of 4 engineers",
                "architected ETL platform",
                "reduced costs by 40%",
                "migrated to cloud",
            ],
            "2023-01",
        ),
    ]

    results = select_experiences_for_job(experiences, _make_job(), ["data", "pipeline"], "senior")

    assert len(results) == 1
    assert 3 <= len(results[0].selected_bullets) <= 4


def test_bullet_selection_scores_against_job_keywords():
    from job_agent.services.experience_selection import select_experiences_for_job

    experiences = [
        _make_exp(
            "Engineer",
            "Org",
            [
                "built spark streaming pipelines",
                "organized team meetings",
                "wrote kafka consumers in python",
            ],
            "2023-01",
        ),
    ]

    job = _make_job(description="kafka spark streaming python real-time")
    results = select_experiences_for_job(experiences, job, ["kafka", "spark", "streaming"], "junior")
    selected = results[0].selected_bullets

    assert any("kafka" in bullet.lower() or "spark" in bullet.lower() for bullet in selected)


def test_roles_returned_in_chronological_order_for_display():
    from job_agent.services.experience_selection import select_experiences_for_job

    experiences = [
        _make_exp("Role A", "Org", ["python etl airflow"], "2020-01"),
        _make_exp("Role B", "Org", ["python etl spark"], "2023-01"),
        _make_exp("Role C", "Org", ["python data pipeline"], "2021-06"),
    ]

    results = select_experiences_for_job(experiences, _make_job(), ["python"], "junior")
    dates = [result.experience_fact.start_date for result in results]

    assert dates == sorted(dates, reverse=True)
