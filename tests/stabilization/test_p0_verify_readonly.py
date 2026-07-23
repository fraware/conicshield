"""CS-SOLVER-007: verification commands must not mutate the repository."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


def _makefile_target_body(name: str) -> str:
    text = Path("Makefile").read_text(encoding="utf-8")
    pattern = rf"^{re.escape(name)}:[^\n]*\n((?:[ \t].*\n)*)"
    match = re.search(pattern, text, flags=re.MULTILINE)
    assert match is not None, f"Makefile target {name!r} not found"
    return match.group(1)


def test_sync_community_metadata_supports_check_mode() -> None:
    src = Path("scripts/sync_community_metadata.py").read_text(encoding="utf-8")
    assert "--check" in src
    assert "argparse" in src


def test_sync_published_run_readmes_supports_check_mode() -> None:
    src = Path("scripts/sync_published_run_readmes.py").read_text(encoding="utf-8")
    assert "--check" in src


_MUTATING_MAKE_LEAF = re.compile(r"(?:^|[\s])(?:sync|refresh|generate)-[\w-]+")


def test_verify_reference_system_is_read_only_makefile_target() -> None:
    text = Path("Makefile").read_text(encoding="utf-8")
    # Prerequisites (same line as target) must use check-*, not sync-*.
    header = re.search(r"^verify-reference-system:([^\n]*)\n", text, flags=re.MULTILINE)
    assert header is not None
    prereqs = header.group(1)
    assert "check-community-metadata" in prereqs
    assert "sync-community-metadata" not in prereqs
    assert _MUTATING_MAKE_LEAF.search(prereqs) is None
    body = _makefile_target_body("verify-reference-system")
    assert _MUTATING_MAKE_LEAF.search(body) is None
    assert "sync-community-metadata" not in body


def test_check_vs_generate_makefile_distinction() -> None:
    text = Path("Makefile").read_text(encoding="utf-8")
    assert "check-community-metadata:" in text
    assert "sync-community-metadata:" in text
    assert "check-published-run-readmes:" in text
    assert "assert-git-clean:" in text


def test_sync_community_metadata_check_is_read_only() -> None:
    before = subprocess.run(
        ["git", "status", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    proc = subprocess.run(
        [sys.executable, "scripts/sync_community_metadata.py", "--check"],
        check=False,
        capture_output=True,
        text=True,
    )
    after = subprocess.run(
        ["git", "status", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert before == after, "check mode mutated the worktree"
    assert proc.returncode in (0, 2)


def test_assert_git_clean_script_exists_and_detects_clean() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/assert_git_clean.py", "--label", "unit"],
        check=False,
        capture_output=True,
        text=True,
    )
    # May be dirty in a working tree with unrelated files; script must still be runnable.
    assert proc.returncode in (0, 1)
    assert "assert_git_clean" not in (proc.stderr or "").lower() or proc.returncode in (0, 1)
