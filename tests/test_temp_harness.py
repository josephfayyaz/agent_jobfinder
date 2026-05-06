from __future__ import annotations

from pathlib import Path


BOOTSTRAP_SH = Path("temp_mac_test/bootstrap.sh")


def test_temp_harness_bootstrap_does_not_hardcode_repo_root():
    content = BOOTSTRAP_SH.read_text(encoding="utf-8")
    assert "/Users/youseffayyaz/Local_LLM/temp_mac_test" not in content
    assert 'SCRIPT_DIR_ENV=$SCRIPT_DIR' in content
