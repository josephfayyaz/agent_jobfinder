# Codex Completion Report — Phase 1.4

## Phase
Phase 1.4 — Multi-Candidate Support + Fact Sheet JSON Schema Ingestion

## Status
COMPLETE

## Completion Timestamp
2026-04-13T00:23:15+02:00

## Files Created
job_agent/services/fact_sheet_json.py  (468 lines)
job_agent/services/fact_sheet_renderer.py  (5 lines)
tests/test_fact_sheet_json.py  (169 lines)

## Files Modified
job_agent/models.py  — added Candidate, MatchProfile, FactConflict, EvidenceIndexItem, FactSheetChangeLog, and nullable candidate_id columns on legacy fact models
job_agent/db.py  — extended prepare_database() with candidate-related ALTER TABLE statements
job_agent/config.py  — added DEFAULT_CANDIDATE_ID setting
job_agent/main.py  — added candidate JSON ingestion/export endpoints and fact-sheet text export stub endpoint
.env.example  — documented DEFAULT_CANDIDATE_ID for public setup
completed_agent_specs.txt  — appended the Phase B1 completion entry

## DB Changes Applied
Tables created via Base.metadata.create_all():
candidates
match_profiles
fact_conflicts
evidence_index_items
fact_sheet_change_log

Columns added via prepare_database():
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS completion_status VARCHAR(20)
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS confidence_summary JSONB
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS spoken_languages JSONB
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS skills_json JSONB
ALTER TABLE experience_facts ADD COLUMN IF NOT EXISTS candidate_id VARCHAR(36)
ALTER TABLE project_facts ADD COLUMN IF NOT EXISTS candidate_id VARCHAR(36)
ALTER TABLE education_facts ADD COLUMN IF NOT EXISTS candidate_id VARCHAR(36)
ALTER TABLE summary_variants ADD COLUMN IF NOT EXISTS candidate_id VARCHAR(36)
ALTER TABLE keyword_sets ADD COLUMN IF NOT EXISTS candidate_id VARCHAR(36)
ALTER TABLE fact_sources ADD COLUMN IF NOT EXISTS candidate_id VARCHAR(36)

## Tests Added
test_ingest_json_creates_candidate_and_match_profile  [tests/test_fact_sheet_json.py]
test_ingest_json_preserves_conflicts_and_evidence  [tests/test_fact_sheet_json.py]
test_ingest_json_is_idempotent  [tests/test_fact_sheet_json.py]
test_export_json_roundtrip  [tests/test_fact_sheet_json.py]
test_legacy_profile_endpoint_still_works_after_migration  [tests/test_fact_sheet_json.py]
test_invalid_json_rejected_with_jsonschema_error  [tests/test_fact_sheet_json.py]

## Test Run Output
176 passed, 2 warnings in 2.09s

## Ruff Output
All checks passed!

## Deviations From Spec
Implemented against the real vendored JSON schema and the correction mapping file, not the simplified sample field names in the original B1 spec.
No pyproject.toml dependency change was needed because jsonschema>=4.20,<5 was already present.
No Alembic files were created; schema changes follow the project’s existing prepare_database() bootstrap pattern.
GET /candidates/{candidate_id}/fact-sheet-text currently returns 501 through a NotImplementedError stub until Phase B2 lands.
Legacy /profile and /fact-sources endpoints remain on MasterProfile and the existing text-ingestion flow; DEFAULT_CANDIDATE_ID is defined and documented, but this phase does not remap those endpoints onto Candidate data.

## Issues Encountered
The original B1 spec examples were structurally incompatible with the canonical schema vendored in Phase B0, especially around person.contact.email, match_profile.availability, experience field names, and required top-level keys. The correction prompt resolved those conflicts and was used as the implementation source of truth.
