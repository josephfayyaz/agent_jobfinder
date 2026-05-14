import logging

from sqlalchemy.orm import Session

from job_agent.models import JobSource, MasterProfile, ResumeTrack

logger = logging.getLogger(__name__)


TRACK_SEEDS = [
    {
        "slug": "data-engineering-analytics",
        "title": "Structured Data & Pipeline Track",
        "role_family": "data",
        "baseline_summary": (
            "Emphasize reliable ETL and ELT workflows, warehouse-oriented datasets, "
            "and analytics-ready pipelines."
        ),
        "target_keywords": [
            "data engineer",
            "analytics engineer",
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
        "linkedin_strategy": "Present a strong data-platform story with warehousing, SQL, ETL, ELT, and reporting outcomes.",
        "github_strategy": "Highlight ETL, warehouse, SQL, data automation, and pipeline work.",
    },
    {
        "slug": "data-analyst-bi-product",
        "title": "Analysis, BI & Reporting Track",
        "role_family": "analytics",
        "baseline_summary": (
            "Emphasize reporting, forecasting, dashboards, and business-facing insights "
            "built from operational and customer data."
        ),
        "target_keywords": [
            "data analyst",
            "bi analyst",
            "business intelligence",
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
        "linkedin_strategy": "Position the profile around business impact, reporting, and KPI ownership.",
        "github_strategy": "Highlight notebooks, BI, forecasting, and business-facing analytics work.",
    },
    {
        "slug": "consulting-strategy-operations",
        "title": "Consulting, Strategy & Transformation Track",
        "role_family": "consulting",
        "baseline_summary": (
            "Emphasize structured problem solving, process diagnostics, stakeholder work, "
            "and executive-ready communication across transformation initiatives."
        ),
        "target_keywords": [
            "consultant",
            "business analyst",
            "strategy",
            "transformation",
            "process mapping",
            "stakeholder",
            "workshop",
            "business case",
            "powerpoint",
            "excel",
            "operating model",
            "kpi",
        ],
        "emphasis": {
            "experiences": ["process diagnostics", "stakeholder management", "analysis", "storytelling"],
            "projects": ["transformation", "business case", "operating model", "performance improvement"],
            "skills": ["excel", "powerpoint", "sql", "process mapping", "kpi"],
        },
        "linkedin_strategy": "Position the profile around business analysis, transformation support, and executive communication.",
        "github_strategy": "If technical evidence exists, frame it as analytics support for business decisions rather than engineering depth.",
    },
    {
        "slug": "finance-fpa-accounting",
        "title": "Finance, FP&A & Accounting Track",
        "role_family": "finance",
        "baseline_summary": (
            "Emphasize financial analysis, planning, reporting, reconciliation, "
            "and disciplined control over budgets, forecasts, and close activities."
        ),
        "target_keywords": [
            "financial analyst",
            "fp&a",
            "budgeting",
            "forecasting",
            "variance analysis",
            "management reporting",
            "accounting",
            "reconciliation",
            "month-end",
            "sap",
            "excel",
            "controlling",
        ],
        "emphasis": {
            "experiences": ["forecasting", "reporting", "close", "variance analysis"],
            "projects": ["financial modeling", "planning", "reporting packs"],
            "skills": ["excel", "sap", "power bi", "forecasting", "reconciliation"],
        },
        "linkedin_strategy": "Position the profile around forecasting, reporting, and business-partnering credibility.",
        "github_strategy": "Feature finance-oriented models, reporting packs, and analysis artifacts when available.",
    },
    {
        "slug": "sales-business-development",
        "title": "Sales, Pipeline & Business Development Track",
        "role_family": "sales",
        "baseline_summary": (
            "Emphasize pipeline generation, CRM discipline, account support, "
            "and consultative selling behaviors across outbound and customer-facing work."
        ),
        "target_keywords": [
            "sales",
            "business development",
            "account executive",
            "account manager",
            "pipeline",
            "crm",
            "salesforce",
            "hubspot",
            "prospecting",
            "lead generation",
            "discovery",
            "renewal",
        ],
        "emphasis": {
            "experiences": ["prospecting", "qualification", "crm hygiene", "commercial support"],
            "projects": ["outbound messaging", "account planning", "pipeline reporting"],
            "skills": ["salesforce", "hubspot", "excel", "communication", "discovery"],
        },
        "linkedin_strategy": "Position the profile around pipeline impact, discovery quality, and disciplined commercial execution.",
        "github_strategy": "If non-code evidence exists, prioritize commercial playbooks and reporting artifacts over technical repositories.",
    },
    {
        "slug": "operations-process-improvement",
        "title": "Operations, Service Delivery & Process Improvement Track",
        "role_family": "operations",
        "baseline_summary": (
            "Emphasize workflow reliability, KPI reporting, service coordination, "
            "and practical process improvement across cross-functional operations."
        ),
        "target_keywords": [
            "operations",
            "operations analyst",
            "service delivery",
            "process improvement",
            "workflow",
            "continuous improvement",
            "sla",
            "kpi",
            "reporting",
            "root cause",
            "cross-functional",
            "coordination",
        ],
        "emphasis": {
            "experiences": ["kpi reporting", "workflow coordination", "issue tracking", "continuous improvement"],
            "projects": ["operations reviews", "issue logs", "process redesign"],
            "skills": ["excel", "power bi", "sql", "documentation", "root cause analysis"],
        },
        "linkedin_strategy": "Position the profile around operations reliability, reporting discipline, and process improvement ownership.",
        "github_strategy": "Feature structured reporting, workflow tools, and operations-improvement artifacts where possible.",
    },
    {
        "slug": "ai-ml-engineering",
        "title": "Applied Models & Evaluation Track",
        "role_family": "ai",
        "baseline_summary": (
            "Emphasize building, evaluating, and iterating on model-driven systems "
            "with production awareness."
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
            "Show a practical model-building identity: from experimentation to shipping usable model-backed tools."
        ),
        "github_strategy": "Feature model experiments, inference APIs, and production-minded ML demos.",
    },
    {
        "slug": "cloud-mlops-ai-platform",
        "title": "Platform, Automation & Infrastructure Track",
        "role_family": "cloud",
        "baseline_summary": (
            "Emphasize infrastructure-aware work across Kubernetes, identity management, "
            "orchestration, and platform operations for model and data workloads."
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
            "Position the profile as platform-aware, with identity, orchestration, and workflow support."
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
        "role_families": ["data", "analytics", "ai", "cloud", "consulting", "finance", "sales", "operations"],
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
        "role_families": ["ai", "cloud", "research", "consulting", "finance", "sales", "operations"],
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
        "role_families": ["data", "analytics", "ai", "cloud", "consulting", "finance", "sales", "operations"],
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
        "role_families": ["data", "analytics", "ai", "cloud", "consulting", "finance", "sales", "operations"],
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
        "role_families": ["data", "analytics", "ai", "cloud", "consulting", "finance", "sales", "operations"],
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
        "role_families": ["data", "analytics", "ai", "cloud", "consulting", "finance", "sales", "operations"],
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
        "role_families": ["data", "analytics", "ai", "cloud", "consulting", "finance", "sales", "operations"],
        "access_mode": "manual_only",
        "compliance_notes": "Manual discovery only. Do not use automated scraping or bot crawling against authenticated LinkedIn pages.",
        "priority": 90,
    },
]


def seed_career_pages(session: Session) -> None:
    """Deprecated: career-page sources are user-selected, not startup-seeded."""
    logger.debug("Skipping career-page source seeding; discovery sources are user-initiated.")


def seed_reference_data(session: Session) -> None:
    profile = session.get(MasterProfile, 1)
    if profile is None:
        profile = MasterProfile(
            id=1,
            public_brand_summary=(
                "Early-career candidate using role-specific resumes and evidence-backed applications."
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
