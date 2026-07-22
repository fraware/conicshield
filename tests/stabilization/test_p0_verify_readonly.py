"""CS-SOLVER-007: verification commands must not mutate the repository."""

from __future__ import annotations

import re
from pathlib import Path

import pytest


def _makefile_target_body(name: str) -> str:
    text = Path("Makefile").read_text(encoding="utf-8")
    pattern = rf"^{re.escape(name)}:\n((?:[ \t].*\n)*)"
    match = re.search(pattern, text, flags=re.MULTILINE)
    assert match is not None, f"Makefile target {name!r} not found"
    return match.group(1)


@pytest.mark.xfail(
    strict=True,
    reason="CS-SOLVER-007: scripts/sync_community_metadata.py has no read-only --check mode",
)
def test_sync_community_metadata_supports_check_mode() -> None:
    src = Path("scripts/sync_community_metadata.py").read_text(encoding="utf-8")
    assert "--check" in src
    assert "argparse" in src


@pytest.mark.xfail(
    strict=True,
    reason="CS-SOLVER-007: make verify-reference-system invokes mutating sync-community-metadata",
)
def test_verify_reference_system_is_read_only_makefile_target() -> None:
    body = _makefile_target_body("verify-reference-system")
    assert "sync-community-metadata" not in body
    # Prefer check-/verify- only leaves under a verify target.
    assert "sync-" not in body
    assert "refresh-" not in body
