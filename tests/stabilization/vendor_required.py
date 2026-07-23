"""Shared vendor-required skip policy (CS-SOLVER-003 / S7).

Local and public CI may skip when Moreau/license is unavailable.
When ``CONICSHIELD_VENDOR_REQUIRED=1``, a would-be skip must hard-fail instead.

Vendor CI sets this variable and pairs it with JUnit post-gates so empty or
all-skipped suites cannot pass.
"""

from __future__ import annotations

import os
from typing import Any

import pytest

_TRUTHY = frozenset({"1", "true", "yes", "on"})
_VENDOR_MARKERS = frozenset({"requires_moreau", "vendor_moreau"})


def vendor_required() -> bool:
    return os.environ.get("CONICSHIELD_VENDOR_REQUIRED", "").strip().lower() in _TRUTHY


def skip_or_fail_vendor(reason: str) -> None:
    """Skip when vendor is optional; fail immediately when vendor is required."""
    if vendor_required():
        pytest.fail(f"CONICSHIELD_VENDOR_REQUIRED=1 but vendor capability missing: {reason}")
    pytest.skip(reason)


def _item_requires_vendor(item: pytest.Item) -> bool:
    names = {m.name for m in item.iter_markers()}
    if names & _VENDOR_MARKERS:
        return True
    path = str(getattr(item, "fspath", "") or getattr(item, "path", "")).replace("\\", "/").lower()
    return "/tests/vendor/" in path or path.endswith("/tests/vendor") or "/vendor/" in path


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[Any]) -> Any:
    """Convert vendor skips into failures when CONICSHIELD_VENDOR_REQUIRED=1."""
    outcome = yield
    if not vendor_required():
        return
    rep = outcome.get_result()
    if not rep.skipped:
        return
    if call.when not in ("setup", "call"):
        return
    if not _item_requires_vendor(item):
        return
    reason = str(rep.longrepr) if rep.longrepr is not None else "skipped"
    rep.outcome = "failed"
    rep.longrepr = f"CONICSHIELD_VENDOR_REQUIRED=1: vendor test must not skip ({reason})"


def _is_vendor_nodeid(nodeid: str) -> bool:
    n = nodeid.replace("\\", "/").lower()
    return "/tests/vendor/" in n or n.startswith("tests/vendor/") or "moreau" in n


@pytest.hookimpl(hookwrapper=True)
def pytest_make_collect_report(collector: pytest.Collector) -> Any:
    """Fail collection-time vendor skips (e.g. module-level importorskip)."""
    outcome = yield
    if not vendor_required():
        return
    report = outcome.get_result()
    if not report.skipped:
        return
    nodeid = report.nodeid or str(getattr(collector, "path", collector.nodeid))
    if not _is_vendor_nodeid(nodeid):
        return
    report.outcome = "failed"
    report.longrepr = f"CONICSHIELD_VENDOR_REQUIRED=1: vendor collection must not skip ({nodeid}: {report.longrepr})"
