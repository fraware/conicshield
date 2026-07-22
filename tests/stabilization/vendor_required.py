"""Shared vendor-required skip policy stub (CS-SOLVER-003 / S7).

Local and public CI may skip when Moreau/license is unavailable.
When ``CONICSHIELD_VENDOR_REQUIRED=1``, a would-be skip must hard-fail instead.

Production vendor CI does not yet set this variable (documented in the S0 ledger).
"""

from __future__ import annotations

import os

import pytest

_TRUTHY = frozenset({"1", "true", "yes", "on"})


def vendor_required() -> bool:
    return os.environ.get("CONICSHIELD_VENDOR_REQUIRED", "").strip().lower() in _TRUTHY


def skip_or_fail_vendor(reason: str) -> None:
    """Skip when vendor is optional; fail immediately when vendor is required."""
    if vendor_required():
        pytest.fail(f"CONICSHIELD_VENDOR_REQUIRED=1 but vendor capability missing: {reason}")
    pytest.skip(reason)
