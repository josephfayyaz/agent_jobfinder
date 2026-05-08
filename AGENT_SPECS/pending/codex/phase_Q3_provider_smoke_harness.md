# Phase Q3 — Provider Smoke Harness

Status: pending

## Goal

Add a standalone smoke harness so every provider can be tested with realistic
workflow-sized calls, not only lightweight validation probes.

## Write Scope

- `job_agent/provider_smoke.py` (new)
- `job_agent/__main__.py`
- `tests/test_provider_smoke.py` (new)
- `docs/PROVIDER_ARCHITECTURE.md` (only if a command reference must be added)

## Do Not Touch

- onboarding UI
- workflow services
- database schema

## Exact Changes

### 1. Add new file `job_agent/provider_smoke.py`

Create a small CLI module with:

- `SMOKE_CASES` dict for:
  - `probe`
  - `small_json`
  - `medium_json`
  - `large_intake`
- one helper that builds deterministic prompts
- one helper that validates returned JSON shape
- `run_provider_smoke(case: str, role: str = "small") -> dict[str, Any]`

Use this exact prompt builder style:

```python
def _case_payload(case: str) -> tuple[str, str]:
    if case == "probe":
        return (
            "Return strict JSON only.",
            'Return {"ok": true}.',
        )
    if case == "small_json":
        return (
            "Return strict JSON only.",
            'Return {"items": ["alpha", "beta"], "count": 2}.',
        )
    if case == "medium_json":
        return (
            "Summarize the input into strict JSON only.",
            (
                "Given this short profile:\\n"
                "- Python\\n- SQL\\n- Italy\\n"
                'Return {"skills": [...], "location": "...", "summary": "..."}'
            ),
        )
    if case == "large_intake":
        large_block = ("Experience: built ETL pipelines with Python and SQL.\\n" * 300).strip()
        return (
            "Extract a compact fact summary. Return strict JSON only.",
            (
                f"{large_block}\\n\\n"
                'Return {"summary": "...", "skills": ["..."], "target_roles": ["..."]}'
            ),
        )
    raise ValueError(f"Unknown smoke case: {case}")
```

Use `LLMRouter().generate_with_retry(...)` for execution.

Return:

```python
{
    "provider_mode": provider_mode,
    "case": case,
    "ok": True,
    "keys": sorted(payload.keys()),
}
```

### 2. Wire a simple CLI entry

In `job_agent/__main__.py`, add a very small argparse-based path:

- `python -m job_agent provider-smoke --case probe`
- `python -m job_agent provider-smoke --case large_intake`

Do not break any existing `python -m job_agent` behavior. If the module
currently delegates elsewhere, preserve that and add a guarded branch.

### 3. Add tests

Create `tests/test_provider_smoke.py` with monkeypatched router behavior.

Required tests:

- `probe` returns `ok=True`
- `large_intake` path generates a much larger prompt than `probe`
- invalid JSON from the provider raises a failure

## Verification

Run:

```bash
pytest tests/test_provider_smoke.py -q
ruff check job_agent/provider_smoke.py job_agent/__main__.py tests/test_provider_smoke.py
python -m job_agent provider-smoke --case probe
```

## Stop Conditions

Stop and report if:

- `__main__.py` is more complex than expected and this branch would break
  existing CLI behavior
