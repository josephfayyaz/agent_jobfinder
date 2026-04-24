"""Compatibility shim that re-exports shared router helpers from focused modules."""

from job_agent.routers.form_utils import _append_unique as _append_unique
from job_agent.routers.form_utils import _blank_to_none as _blank_to_none
from job_agent.routers.form_utils import _parse_urlencoded_body as _parse_urlencoded_body
from job_agent.routers.job_views import _build_job_ui_payload as _build_job_ui_payload
from job_agent.routers.job_views import _default_jobspy_query as _default_jobspy_query
from job_agent.routers.job_views import _get_dashboard_data as _get_dashboard_data
from job_agent.routers.job_views import _get_priority_jobs as _get_priority_jobs
from job_agent.routers.job_views import _get_recent_jobs_with_scores as _get_recent_jobs_with_scores
from job_agent.routers.job_views import _job_language_rows as _job_language_rows
from job_agent.routers.job_views import _job_passes_language_filter as _job_passes_language_filter
from job_agent.routers.job_views import _query_jobs_for_ui as _query_jobs_for_ui
from job_agent.routers.job_views import _score_rows_for_jobs as _score_rows_for_jobs
from job_agent.routers.setup_state import VALID_VERIFIED_FACT_TYPES as VALID_VERIFIED_FACT_TYPES
from job_agent.routers.setup_state import _USER_SETTINGS_FILE as _USER_SETTINGS_FILE
from job_agent.routers.setup_state import _active_candidate_id as _active_candidate_id
from job_agent.routers.setup_state import _onboarding_complete as _onboarding_complete
from job_agent.routers.setup_state import _owner_candidate as _owner_candidate
from job_agent.routers.setup_state import _persist_default_candidate_id as _persist_default_candidate_id
from job_agent.routers.setup_state import _provider_setup_status as _provider_setup_status
from job_agent.routers.setup_state import _raise_if_setup_required as _raise_if_setup_required
from job_agent.routers.setup_state import _redirect_if_setup_required as _redirect_if_setup_required
from job_agent.routers.setup_state import _sanitize_verified_fact_type as _sanitize_verified_fact_type
from job_agent.routers.setup_state import _setup_gate_enabled as _setup_gate_enabled
from job_agent.routers.setup_state import _setup_status_payload as _setup_status_payload
from job_agent.routers.setup_state import _verified_fact_key as _verified_fact_key
from job_agent.routers.setup_state import _verified_fact_scope_filter as _verified_fact_scope_filter
from job_agent.routers.templates import templates as templates
from job_agent.routers.ui_context import _get_candidate_display_name as _get_candidate_display_name
from job_agent.routers.ui_context import _ui_context as _ui_context
from job_agent.routers.ui_context import _ui_provider_mode as _ui_provider_mode

__all__ = [
    "VALID_VERIFIED_FACT_TYPES",
    "_USER_SETTINGS_FILE",
    "_active_candidate_id",
    "_append_unique",
    "_blank_to_none",
    "_build_job_ui_payload",
    "_default_jobspy_query",
    "_get_candidate_display_name",
    "_get_dashboard_data",
    "_get_priority_jobs",
    "_get_recent_jobs_with_scores",
    "_job_language_rows",
    "_job_passes_language_filter",
    "_onboarding_complete",
    "_owner_candidate",
    "_parse_urlencoded_body",
    "_persist_default_candidate_id",
    "_provider_setup_status",
    "_query_jobs_for_ui",
    "_raise_if_setup_required",
    "_redirect_if_setup_required",
    "_sanitize_verified_fact_type",
    "_score_rows_for_jobs",
    "_setup_gate_enabled",
    "_setup_status_payload",
    "_ui_context",
    "_ui_provider_mode",
    "_verified_fact_key",
    "_verified_fact_scope_filter",
    "templates",
]
