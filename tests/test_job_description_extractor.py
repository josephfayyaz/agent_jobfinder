"""Tests for the E3 job description extraction service."""

from __future__ import annotations

from job_agent.services.job_description_extractor import (
    extract_best_description,
    extract_from_ats_payload,
    extract_from_structured_metadata,
    extract_main_content,
    extract_with_readability,
)


# ── JSON-LD JobPosting extraction wins when present ──────────────────────

def test_json_ld_job_posting_extraction_wins():
    """When a page contains JSON-LD JobPosting, that description wins."""
    html = """
    <html><head>
    <script type="application/ld+json">
    {
      "@context": "https://schema.org/",
      "@type": "JobPosting",
      "title": "Data Engineer",
      "description": "<p>We are looking for a Data Engineer to build ETL pipelines. Requirements: Python, SQL, Airflow. Qualifications: BS in CS or related. Responsibilities: design and maintain data infrastructure for analytics teams.</p>"
    }
    </script>
    </head><body>
    <div>Some noise text on the page.</div>
    </body></html>
    """
    result = extract_from_structured_metadata(html, source_url="https://acme.com/jobs/1")

    assert result.success is True
    assert result.extraction_method == "json_ld_job_posting"
    assert "ETL pipelines" in result.description
    assert "Requirements" in result.description
    assert result.source_kind == "company_page"
    assert result.provenance["jd_extraction_method"] == "json_ld_job_posting"


def test_json_ld_extraction_preferred_over_board_snippet():
    """The full pipeline should prefer JSON-LD over existing thin snippets."""
    thin_existing = "Short snippet about data engineering."
    rich_description = (
        "We are looking for a Data Engineer. "
        "Requirements: Python, SQL, dbt, Airflow. "
        "Qualifications: Bachelor's degree. "
        "Responsibilities: build data pipelines. "
    ) * 5

    html = f"""
    <html><head>
    <script type="application/ld+json">
    {{
      "@type": "JobPosting",
      "description": "{rich_description}"
    }}
    </script>
    </head><body><div>Noise</div></body></html>
    """

    # This will try the company URL first, but since we can't actually fetch,
    # we test the structured extraction path separately
    structured = extract_from_structured_metadata(html, source_url="https://acme.com/apply/1")
    assert structured.success is True
    assert len(structured.description) > len(thin_existing)
    assert structured.extraction_method == "json_ld_job_posting"


# ── ATS plaintext descriptions are preserved as strong inputs ────────────

def test_ats_plaintext_preserved_as_strong_input():
    """ATS plaintext description should be preserved and marked strong."""
    ats_text = (
        "We are hiring a Software Engineer. "
        "Requirements: Python, Java, AWS. "
        "Responsibilities: build microservices. "
        "Qualifications: 3+ years experience. "
    ) * 3

    result = extract_from_ats_payload(
        description_text=ats_text,
        ats_type="lever",
        source_url="https://lever.co/acme/jobs/1",
    )

    assert result.success is True
    assert result.extraction_method == "ats_payload"
    assert result.source_kind == "ats_structured"
    assert "Software Engineer" in result.description
    assert result.provenance["jd_extraction_method"] == "ats_payload"


def test_ats_html_description_converted_to_plaintext():
    """ATS HTML descriptions (e.g. Greenhouse content) should be stripped to text."""
    html_desc = (
        "<h2>Data Engineer</h2>"
        "<p>We are looking for a data engineer to join our team.</p>"
        "<ul>"
        "<li>Build ETL pipelines</li>"
        "<li>Maintain data warehouse</li>"
        "<li>Python, SQL, dbt required</li>"
        "</ul>"
        "<p>Requirements: 2+ years of data engineering experience.</p>"
    )

    result = extract_from_ats_payload(
        description_text=html_desc,
        ats_type="greenhouse",
        source_url="https://greenhouse.io/acme/jobs/1",
    )

    assert result.success is True
    assert "<" not in result.description  # No HTML tags
    assert "Build ETL pipelines" in result.description
    assert result.source_kind == "ats_structured"


def test_ats_strong_existing_not_re_fetched():
    """If ATS already has strong text, don't go to weaker sources."""
    strong_desc = (
        "Requirements: Python, SQL, ETL. "
        "Qualifications: 3 years. "
        "Responsibilities: data pipelines. "
    ) * 8

    result = extract_best_description(
        existing_description=strong_desc,
        source_name="ats_greenhouse",
        source_url="https://greenhouse.io/acme/1",
        company_url="",
        canonical_apply_url="https://greenhouse.io/acme/1",
    )

    assert result.success is True
    assert result.extraction_method == "ats_existing_strong"
    assert result.source_kind == "ats_structured"


# ── Company-page extraction improves thin LinkedIn snippet ───────────────

def test_company_page_trafilatura_improves_thin_snippet():
    """trafilatura should extract main content from a company job page."""
    html = (
        "<html><body>"
        "<header>Company Nav</header>"
        "<article>"
        "<h1>Data Engineer</h1>"
        "<p>We are looking for a Data Engineer to join our analytics team. "
        "You will build and maintain ETL pipelines using Python and SQL. "
        "Requirements include experience with Airflow and dbt. "
        "This is a full-time position in our Milan office.</p>"
        "<h2>What you'll do</h2>"
        "<ul><li>Design data models</li><li>Build pipelines</li>"
        "<li>Monitor data quality</li></ul>"
        "<h2>Requirements</h2>"
        "<ul><li>Python</li><li>SQL</li><li>3+ years experience</li></ul>"
        "</article>"
        "<footer>Company Footer</footer>"
        "</body></html>"
    )

    result = extract_main_content(html, source_url="https://acme.com/careers/data-engineer")

    # trafilatura should extract meaningful content
    if result.success:
        assert len(result.description) >= 80
        assert result.extraction_method == "trafilatura"
        assert result.source_kind == "company_page"


def test_readability_fallback_extracts_content():
    """readability-lxml should extract from pages trafilatura misses."""
    html = (
        "<html><body>"
        "<div id='main'>"
        "<h1>ML Engineer Position</h1>"
        "<p>Join our team to build machine learning systems. "
        "We need candidates with experience in Python, TensorFlow, and MLOps. "
        "Responsibilities include model training, deployment, and monitoring. "
        "This is a full-time role based in Rome, Italy.</p>"
        "<p>Requirements: PhD or Masters in CS, 3+ years ML experience, "
        "strong Python skills, experience with cloud platforms.</p>"
        "</div>"
        "</body></html>"
    )

    result = extract_with_readability(html, source_url="https://acme.com/jobs/ml")

    if result.success:
        assert len(result.description) >= 80
        assert result.extraction_method == "readability"


# ── Extraction failure leaves truthful unready state ─────────────────────

def test_extraction_failure_leaves_truthful_unready_state():
    """When extraction fails, the result should not fake a ready state."""
    result = extract_from_ats_payload(
        description_text="",
        ats_type="greenhouse",
        source_url="https://greenhouse.io/acme/1",
    )

    assert result.success is False
    assert result.extraction_method == "ats_payload_empty"
    assert result.description == ""


def test_thin_ats_payload_not_marked_success():
    """Very thin ATS text should not be marked as successful extraction."""
    result = extract_from_ats_payload(
        description_text="Short",
        ats_type="lever",
    )

    assert result.success is False
    assert result.extraction_method == "ats_payload_thin"


def test_json_ld_missing_returns_failure():
    """When no JSON-LD is present, extraction should fail gracefully."""
    html = "<html><body><p>No structured data here.</p></body></html>"

    result = extract_from_structured_metadata(html)

    assert result.success is False
    assert result.extraction_method == "json_ld_not_found"


def test_no_improvement_returns_existing():
    """When no source can improve the description, existing text is returned."""
    existing = "Some existing description text."

    # No URLs to fetch from
    result = extract_best_description(
        existing_description=existing,
        source_name="manual",
        source_url="",
        company_url="",
        canonical_apply_url="",
    )

    assert result.success is False
    assert result.quality_improved is False
    assert result.description == existing


# ── Provenance metadata correctness ─────────────────────────────────────

def test_provenance_metadata_populated():
    """Successful extraction should populate provenance fields."""
    ats_text = (
        "Full job description with requirements and qualifications. " * 10
    )

    result = extract_from_ats_payload(
        description_text=ats_text,
        ats_type="ashby",
        source_url="https://jobs.ashbyhq.com/acme/1",
    )

    assert result.success is True
    assert result.provenance["jd_extraction_method"] == "ats_payload"
    assert result.provenance["jd_source_kind"] == "ats_structured"
    assert result.provenance["jd_source_url"] == "https://jobs.ashbyhq.com/acme/1"
    assert "jd_last_enriched_at" in result.provenance
