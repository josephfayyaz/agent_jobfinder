from sqlalchemy.orm import Session

from job_agent.models import JobSource, MasterProfile, ResumeTrack


TRACK_SEEDS = [
    {
        "slug": "data-engineering-analytics",
        "title": "Junior Data Engineer / Analytics Engineer",
        "role_family": "data",
        "baseline_summary": (
            "Position the candidate as a data engineer who builds reliable ETL and ELT workflows, "
            "warehouse-oriented datasets, and analytics-ready pipelines."
        ),
        "target_keywords": [
            "sql",
            "python",
            "etl",
            "elt",
            "data pipeline",
            "postgresql",
            "bigquery",
            "dataform",
            "datastream",
            "cdc",
            "airflow",
            "warehouse",
        ],
        "emphasis": {
            "experiences": ["warehousing", "etl", "elt", "reporting", "pipeline reliability"],
            "projects": ["pipelines", "warehouse", "data quality", "analytics engineering"],
            "skills": ["sql", "python", "postgresql", "bigquery", "dataform", "power bi"],
        },
        "linkedin_strategy": (
            "Present a strong data-platform story with warehousing, SQL, ETL, ELT, and reporting outcomes."
        ),
        "github_strategy": "Highlight ETL, warehouse, SQL, data automation, and analytics engineering work.",
    },
    {
        "slug": "data-analyst-bi-product",
        "title": "Junior Data Analyst / BI / Product Data Analyst",
        "role_family": "analytics",
        "baseline_summary": (
            "Position the candidate as an analyst who turns operational and customer data into reporting, "
            "forecasting, dashboards, and business-facing insights."
        ),
        "target_keywords": [
            "sql",
            "python",
            "power bi",
            "power query",
            "dashboard",
            "reporting",
            "forecasting",
            "analytics",
            "kpi",
        ],
        "emphasis": {
            "experiences": ["reporting", "forecasting", "bi", "stakeholder support"],
            "projects": ["analysis", "dashboards", "forecasting"],
            "skills": ["sql", "python", "power bi", "power query", "forecasting"],
        },
        "linkedin_strategy": "Position the profile as analytics-capable with business impact, reporting, and KPI ownership.",
        "github_strategy": "Highlight notebooks, BI, forecasting, and business-facing analytics work.",
    },
    {
        "slug": "ai-ml-engineering",
        "title": "Junior AI / Machine Learning Engineer",
        "role_family": "ai",
        "baseline_summary": (
            "Position the candidate as an applied AI engineer who can build, evaluate, and iterate on "
            "machine learning systems with production awareness."
        ),
        "target_keywords": [
            "machine learning",
            "model evaluation",
            "python",
            "pytorch",
            "transformers",
            "inference",
            "experimentation",
            "reinforcement learning",
            "multimodal",
        ],
        "emphasis": {
            "experiences": ["model building", "evaluation", "deployment", "automation"],
            "projects": ["ml apps", "experiments", "inference services", "research prototypes"],
            "skills": ["python", "pytorch", "scikit-learn", "transformers", "docker", "fastapi"],
        },
        "linkedin_strategy": (
            "Show a practical AI identity: from experimentation to shipping usable model-backed tools."
        ),
        "github_strategy": "Feature model experiments, inference APIs, and production-minded ML demos.",
    },
    {
        "slug": "cloud-mlops-ai-platform",
        "title": "Junior Cloud ML Engineer / MLOps / AI Platform",
        "role_family": "cloud",
        "baseline_summary": (
            "Position the candidate as an infrastructure-aware engineer who supports AI and data workloads "
            "through Kubernetes, identity management, orchestration, and ML platform operations."
        ),
        "target_keywords": [
            "kubernetes",
            "docker",
            "mlops",
            "kubeflow",
            "keycloak",
            "dex",
            "oauth2 proxy",
            "istio",
            "platform",
            "workflows",
        ],
        "emphasis": {
            "experiences": ["identity", "kubernetes", "platform automation", "workflow support"],
            "projects": ["ml platform", "cloud workflows", "deployment support"],
            "skills": ["kubernetes", "docker", "kubeflow", "keycloak", "istio", "python"],
        },
        "linkedin_strategy": (
            "Position the profile as platform-aware for AI and data teams, with identity, orchestration, and ML workflow support."
        ),
        "github_strategy": "Pin infrastructure, ML workflow, and platform-support projects with operational detail.",
    },
]


JOB_SOURCE_SEEDS = [
    {
        "slug": "eures",
        "name": "EURES",
        "source_type": "official_portal",
        "base_url": "https://eures.europa.eu",
        "target_regions": ["Italy", "EU"],
        "role_families": ["data", "analytics", "ai", "cloud"],
        "access_mode": "public_portal",
        "compliance_notes": "Official EU job mobility portal. Prefer manual review plus structured import where supported.",
        "priority": 10,
    },
    {
        "slug": "euraxess",
        "name": "EURAXESS",
        "source_type": "official_portal",
        "base_url": "https://euraxess.ec.europa.eu",
        "target_regions": ["Italy", "EU"],
        "role_families": ["ai", "cloud", "research"],
        "access_mode": "public_portal",
        "compliance_notes": "Best for research engineer, ML systems, and academic-industry roles in Europe.",
        "priority": 20,
    },
    {
        "slug": "greenhouse",
        "name": "Greenhouse Job Board",
        "source_type": "public_api",
        "base_url": "https://boards-api.greenhouse.io/v1/boards",
        "target_regions": ["Italy", "EU"],
        "role_families": ["data", "analytics", "ai", "cloud"],
        "access_mode": "public_api",
        "compliance_notes": "Prefer company-specific Greenhouse boards and store canonical apply links.",
        "priority": 30,
    },
    {
        "slug": "lever",
        "name": "Lever Postings",
        "source_type": "public_api",
        "base_url": "https://api.lever.co/v0/postings",
        "target_regions": ["Italy", "EU"],
        "role_families": ["data", "analytics", "ai", "cloud"],
        "access_mode": "public_api",
        "compliance_notes": "Public company postings API. Use canonical job URLs and deduplicate by apply link.",
        "priority": 40,
    },
    {
        "slug": "ashby",
        "name": "Ashby Public Jobs",
        "source_type": "public_board",
        "base_url": "https://jobs.ashbyhq.com",
        "target_regions": ["Italy", "EU"],
        "role_families": ["data", "analytics", "ai", "cloud"],
        "access_mode": "public_board",
        "compliance_notes": "Use public job boards and respect robots and published endpoints.",
        "priority": 50,
    },
    {
        "slug": "company-careers",
        "name": "Company Careers Pages",
        "source_type": "public_board",
        "base_url": "",
        "target_regions": ["Italy", "EU"],
        "role_families": ["data", "analytics", "ai", "cloud"],
        "access_mode": "manual_review",
        "compliance_notes": "Use public careers pages as canonical sources when discovered elsewhere.",
        "priority": 60,
    },
    {
        "slug": "linkedin-manual",
        "name": "LinkedIn Manual Discovery",
        "source_type": "manual_only",
        "base_url": "https://www.linkedin.com/jobs",
        "target_regions": ["Italy", "EU"],
        "role_families": ["data", "analytics", "ai", "cloud"],
        "access_mode": "manual_only",
        "compliance_notes": "Manual discovery only. Do not use automated scraping or bot crawling against authenticated LinkedIn pages.",
        "priority": 90,
    },
]


def seed_reference_data(session: Session) -> None:
    profile = session.get(MasterProfile, 1)
    if profile is None:
        profile = MasterProfile(
            id=1,
            public_brand_summary=(
                "Early-career builder targeting data, AI, and NLP roles with role-specific resumes."
            ),
            additional_notes={
                "next_step": "Replace placeholder profile content with real achievements and metrics."
            },
        )
        session.add(profile)

    existing_tracks = {track.slug: track for track in session.query(ResumeTrack).all()}
    for track_seed in TRACK_SEEDS:
        existing = existing_tracks.get(track_seed["slug"])
        if existing is None:
            session.add(ResumeTrack(**track_seed))
            continue
        for key, value in track_seed.items():
            setattr(existing, key, value)
        existing.active = True

    allowed_slugs = {track_seed["slug"] for track_seed in TRACK_SEEDS}
    for track in existing_tracks.values():
        if track.slug not in allowed_slugs:
            track.active = False

    existing_sources = {source.slug: source for source in session.query(JobSource).all()}
    for source_seed in JOB_SOURCE_SEEDS:
        existing = existing_sources.get(source_seed["slug"])
        if existing is None:
            session.add(JobSource(**source_seed))
            continue
        for key, value in source_seed.items():
            setattr(existing, key, value)
        existing.active = True

    session.commit()
