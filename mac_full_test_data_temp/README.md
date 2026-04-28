# Mac Full Test Data

This folder contains a generated local test corpus for broad manual QA.

- `build_dataset.py`
  - creates 20 synthetic single-user candidate packs
  - writes both `.txt` and `.pdf` CV inputs
  - writes matching profile JSON and synthetic target-job briefs
- `generated/manifest.json`
  - quick index of all candidate packs
- `generated/role_sources.json`
  - official public occupation references used as role-family seeds

The candidate content is synthetic by design. The role families and baseline
requirement themes are grounded in public occupation references so the test
corpus covers realistic variation without shipping any personal CV data.
