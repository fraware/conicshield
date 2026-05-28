"""Shared helpers for runnable examples under ``examples/``."""

from __future__ import annotations

import sys
from pathlib import Path

from conicshield.specs.schema import (
    BoxConstraint,
    RateConstraint,
    SafetySpec,
    SimplexConstraint,
    TurnFeasibilityConstraint,
)

FLAGSHIP_RUN_ID = "host-realistic-20260525"
FAMILY_ID = "conicshield-transition-bank-v1"


def repo_root() -> Path:
    """Repository root (parent of ``examples/``)."""
    return Path(__file__).resolve().parents[1]


def configure_stdio() -> None:
    """Best-effort UTF-8 stdout on Windows consoles."""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (OSError, ValueError):
            pass


def section(title: str) -> None:
    print(f"\n=== {title} ===")


def minimal_spec() -> SafetySpec:
    """Minimal 4-action spec supported by reference and native compiled paths."""
    return SafetySpec(
        spec_id="examples/minimal",
        version="0.1.0",
        action_dim=4,
        constraints=[
            SimplexConstraint(total=1.0),
            TurnFeasibilityConstraint(allowed_actions=[0, 1, 2, 3]),
            BoxConstraint(lower=[0.0] * 4, upper=[1.0] * 4),
            RateConstraint(max_delta=[0.9] * 4),
        ],
    )


def skip(message: str, *, detail: object | None = None) -> int:
    """Print a skip line and return exit code 0 (examples must not fail CI without vendor stack)."""
    print(f"SKIP: {message}")
    if detail is not None:
        print(f"  ({detail})")
    return 0
