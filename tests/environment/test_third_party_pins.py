"""§7.1 hygiene: vendor pin file matches git HEAD when checkout is present."""

from __future__ import annotations

import subprocess

import pytest

from tests._repo import repo_root

REPO = repo_root()
REVISION_FILE = REPO / "third_party" / "inter-sim-rl" / "REVISION"
CHECKOUT = REPO / "third_party" / "inter-sim-rl" / "checkout"


def _recorded_intersim_sha() -> str:
    text = REVISION_FILE.read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("sha="):
            return line.split("=", 1)[1].strip()
    raise AssertionError("sha= not found in REVISION")


def test_intersim_revision_matches_checkout_git_head() -> None:
    if not (CHECKOUT / ".git").exists():
        pytest.skip("inter-sim-rl checkout has no .git (shallow export)")
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=CHECKOUT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert (
        _recorded_intersim_sha() == head
    ), f"Update third_party/inter-sim-rl/REVISION sha= to {head} or sync checkout to recorded pin"
