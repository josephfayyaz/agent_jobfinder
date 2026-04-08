# Spec: Phase 3.1 — Fix Job-to-Track Matching Score Formula
Status: pending

## Context
The current matching formula has a base score of 45, meaning even a job with zero
keyword matches scores 45/100. This makes the 60% revise threshold meaningless.
Lower the base to 20 so scores reflect actual relevance.

## Changes

### File: `job_agent/services/matching.py`
#### Change 1: Lower the base score from 45 to 20, increase per-keyword weight

BEFORE:
```python
        score = min(100, 45 + len(matched_keywords) * 6 + keyword_hits * 2 + family_bonus)
```
AFTER:
```python
        score = min(100, 20 + len(matched_keywords) * 8 + keyword_hits * 3 + family_bonus)
```

No other changes to this file.

## Why This Formula
- Base 20: a job with no matching keywords gets ~20 (clearly not relevant)
- Each matched keyword: +8 points (up from +6)
- Each keyword frequency hit: +3 (up from +2)
- A job matching 5 keywords + 3 hits + family bonus = 20 + 40 + 9 + 8 = 77 → "revise" territory
- A job matching 8 keywords = 20 + 64 = 84 → near "pass" threshold

## Verification
```bash
# Run the API and check that a clearly matching job scores > 60
curl -s localhost:8000/jobs/<any_existing_job_id>/track-fit | python3 -m json.tool
# Expected: top track should score > 60 for relevant jobs

/Users/youseffayyaz/miniforge3/bin/conda run -n ML python -m ruff check job_agent/
# Expected: no errors
```

## Git
```bash
git add job_agent/services/matching.py
git commit -m "fix: lower matching score base from 45 to 20 for meaningful thresholds

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```
