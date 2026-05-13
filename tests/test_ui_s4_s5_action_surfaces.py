from pathlib import Path


REVIEW_JS = Path("frontend/static/onboarding/review.js")
JOB_ROW = Path("frontend/templates/partials/job_row.html")
DRAFT_DETAIL = Path("frontend/templates/draft_detail.html")
DRAFT_HEADER = Path("frontend/templates/partials/drafts/header.html")
DRAFT_FOOTER = Path("frontend/templates/partials/drafts/footer_panels.html")
DRAFT_SIDEBAR = Path("frontend/templates/partials/drafts/sidebar.html")


def test_onboarding_review_renders_geography_without_remote_or_availability_questions():
    source = REVIEW_JS.read_text()

    assert "review-target-countries" in source
    assert "review-preferred-cities" in source
    assert "match_profile.location_preferences.preferred_countries" in source
    assert "match_profile.location_preferences.preferred_cities" in source
    assert "review-remote" not in source
    assert "review-availability" not in source
    assert "review-start-date" not in source


def test_onboarding_review_save_preserves_location_preferences_shape():
    source = REVIEW_JS.read_text()

    assert "existingLocationPreferences" in source
    assert "preferred_countries: preferredCountries.length ? preferredCountries : [\"Italy\"]" in source
    assert "preferred_cities: preferredCities" in source


def test_job_row_groups_decision_evaluation_and_maintenance_actions():
    source = JOB_ROW.read_text()

    assert 'data-job-action-groups' in source
    assert 'data-action-group="primary"' in source
    assert 'data-action-group="review"' in source
    assert 'data-action-group="maintenance"' in source
    assert "Shortlist" in source
    assert "View JD" in source
    assert "Readiness" in source
    assert "Refresh trust" in source
    assert "Enrich" in source


def test_draft_page_has_visible_primary_section_and_supporting_action_groups():
    header = DRAFT_HEADER.read_text()
    detail = DRAFT_DETAIL.read_text()
    footer = DRAFT_FOOTER.read_text()

    assert 'data-draft-action-group="primary"' in header
    assert "Approve" in header
    assert "Reject" in header
    assert "Download PDF" in header
    assert 'data-draft-action-group="section"' in detail
    assert "Save summary" in detail
    assert "Rewrite" in detail
    assert 'data-draft-action-group="supporting"' in footer
    assert "Save to profile memory" in footer
    assert "Generate cover letter" in footer


def test_draft_rewrite_controls_are_not_documented_as_hover_only():
    combined = "\n".join([DRAFT_DETAIL.read_text(), DRAFT_SIDEBAR.read_text()])

    assert "group-hover" not in combined
    assert "Hover over any bullet" not in combined
