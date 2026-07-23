"""S7 governance hardening: workflows, stack policy, schema, command naming."""

from __future__ import annotations

import json
import re
from pathlib import Path


def test_windows_ci_is_required_public_workflow() -> None:
    text = Path(".github/workflows/windows-ci.yml").read_text(encoding="utf-8")
    assert "windows-public" in text
    assert "solver-public" in text
    assert "assert_min_executed_tests.py" in text
    devenv = Path("docs/DEVENV.md").read_text(encoding="utf-8")
    assert "windows-ci" in devenv
    assert "required" in devenv.lower() or "Windows public" in devenv


def test_solver_stack_policy_pins_production_defaults() -> None:
    policy = json.loads(Path("packaging/solver_stack_policy.json").read_text(encoding="utf-8"))
    defaults = policy["production_defaults"]
    assert "solver-public" in defaults
    assert "solver-moreau-cpu" in defaults
    for name, row in defaults.items():
        path = Path(row["constraints_file"])
        assert path.is_file(), name
    quarantine = policy.get("quarantine") or {}
    assert "candidates" in quarantine


def test_reference_authority_fails_on_dirty_verify() -> None:
    text = Path(".github/workflows/reference-authority.yml").read_text(encoding="utf-8")
    assert "assert_git_clean.py" in text
    assert "verify-reference-system" in text


def test_public_ci_has_min_executed_and_fallback_tests() -> None:
    text = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "assert_min_executed_tests.py" in text
    assert "test_verification_release.py" in text
    assert "test_client_fallback.py" in text
    assert "check_schema_compatibility.py" in text


def test_solver_touch_covers_verification_platform_compilation() -> None:
    text = Path(".github/workflows/solver-touch.yml").read_text(encoding="utf-8")
    for needle in (
        "conicshield/compilation/**",
        "conicshield/verification/**",
        "conicshield/platform/**",
        "conicshield/workers/**",
        "tests/verification/**",
        "tests/platform/**",
    ):
        assert needle in text


def test_qualification_workflow_does_not_promote_candidates() -> None:
    text = Path(".github/workflows/solver-stack-qualification.yml").read_text(encoding="utf-8")
    assert "quarantine" in text.lower()
    assert "check_solver_stack_policy.py" in text
    assert "assert_git_clean.py" in text


_MUTATING_MAKE_LEAF = re.compile(r"(?:^|[\s])(?:sync|refresh|generate)-[\w-]+")


def test_verify_makefile_targets_do_not_call_writers() -> None:
    text = Path("Makefile").read_text(encoding="utf-8")
    # Extract verify-* target headers + bodies; ban mutating sync-/refresh-/generate- leaves.
    for match in re.finditer(
        r"^(verify-[\w-]+):([^\n]*)\n((?:[ \t].*\n)*)",
        text,
        flags=re.MULTILINE,
    ):
        name = match.group(1)
        prereqs = match.group(2)
        body = match.group(3)
        combined = prereqs + "\n" + body
        if name == "verify-extended":
            assert "sync-community-metadata" not in combined
            continue
        assert _MUTATING_MAKE_LEAF.search(combined) is None, name
        assert "sync-community-metadata" not in combined, name
