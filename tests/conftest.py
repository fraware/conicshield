"""Pytest hooks: capture Moreau-related metrics during live runs (writes output/moreau_metrics.json)."""

from __future__ import annotations

import importlib.util
import json
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from _pytest.reports import TestReport


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _metrics_path() -> Path:
    override = os.environ.get("CONICSHIELD_MOREAU_METRICS_OUT")
    if override:
        return Path(override).expanduser()
    return _repo_root() / "output" / "moreau_metrics.json"


def _moreau_metrics_enabled() -> bool:
    return os.environ.get("CONICSHIELD_MOREAU_METRICS", "1") not in ("0", "false", "False", "no")


def _is_moreau_related(item: pytest.Item) -> bool:
    """Classify tests that exercise or validate Moreau (avoid bare 'moreau' in nodeid — false positives)."""
    names = {m.name for m in item.iter_markers()}
    if names & {"vendor_moreau", "requires_moreau"}:
        return True
    fname = Path(str(item.fspath)).name.lower()
    if "moreau" in fname:
        return True
    nid = item.nodeid.lower()
    if "cvxpy_moreau" in nid or "native_moreau" in nid:
        return True
    # Telemetry helpers: normalize_moreau_* in solver telemetry module only.
    return fname == "test_solver_telemetry.py" and "moreau" in nid


def _env_snapshot() -> dict[str, Any]:
    snap: dict[str, Any] = {
        "moreau_importable": False,
        "cvxpy_moreau_registered": False,
    }
    try:
        snap["moreau_importable"] = importlib.util.find_spec("moreau") is not None
    except Exception as exc:  # noqa: BLE001 — best-effort probe
        snap["moreau_import_error"] = str(exc)[:200]
    try:
        import cvxpy as cp

        snap["cvxpy_moreau_registered"] = hasattr(cp, "MOREAU")
    except Exception as exc:  # noqa: BLE001
        snap["cvxpy_import_error"] = str(exc)[:200]
    return snap


@dataclass
class MoreauSessionState:
    collected_moreau: int = 0
    per_node: dict[str, dict[str, Any]] = field(default_factory=dict)

    def merge_report(self, item: pytest.Item, rep: TestReport) -> None:
        nodeid = item.nodeid
        row = self.per_node.setdefault(
            nodeid,
            {
                "nodeid": nodeid,
                "path": str(item.fspath),
                "markers": sorted({m.name for m in item.iter_markers()}),
                "phases": {},
            },
        )
        phase = rep.when
        entry: dict[str, Any] = {
            "outcome": rep.outcome,
            "duration_sec": float(rep.duration),
        }
        if rep.skipped:
            lr = rep.longrepr
            entry["skip_reason"] = str(lr)[:500] if lr is not None else None
        if rep.failed and rep.longrepr is not None:
            entry["longrepr_excerpt"] = str(rep.longrepr)[:400]
        row["phases"][phase] = entry


_MOREAU_STASH_KEY = pytest.StashKey[MoreauSessionState]()


def pytest_configure(config: pytest.Config) -> None:
    if not _moreau_metrics_enabled():
        return
    config.stash[_MOREAU_STASH_KEY] = MoreauSessionState()


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if not _moreau_metrics_enabled():
        return
    st = config.stash.get(_MOREAU_STASH_KEY, None)
    if st is None:
        return
    st.collected_moreau = sum(1 for it in items if _is_moreau_related(it))


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[None]) -> Any:
    outcome = yield
    if not _moreau_metrics_enabled():
        return
    rep = outcome.get_result()
    session = item.session
    st = session.config.stash.get(_MOREAU_STASH_KEY, None)
    if st is None or not _is_moreau_related(item):
        return
    st.merge_report(item, rep)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    if not _moreau_metrics_enabled():
        return
    st = session.config.stash.get(_MOREAU_STASH_KEY, None)
    if st is None:
        return

    per = list(st.per_node.values())
    call_durations: list[float] = []
    passed = skipped = failed = setup_failed = 0
    for row in per:
        phases = row.get("phases", {})
        setup = phases.get("setup")
        if setup and setup.get("outcome") == "failed":
            setup_failed += 1
        call = phases.get("call")
        if not call:
            continue
        call_durations.append(float(call.get("duration_sec", 0.0)))
        o = call.get("outcome")
        if o == "passed":
            passed += 1
        elif o == "skipped":
            skipped += 1
        elif o == "failed":
            failed += 1

    total_call = sum(call_durations)
    n = len(call_durations)
    mean = total_call / n if n else 0.0
    mx = max(call_durations) if call_durations else 0.0

    payload: dict[str, Any] = {
        "generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pytest_version": pytest.__version__,
        "pytest_exitstatus": exitstatus,
        "environment": _env_snapshot(),
        "summary": {
            "collected_moreau_related": st.collected_moreau,
            "executed_moreau_related": len(st.per_node),
            "call_phase": {
                "passed": passed,
                "skipped": skipped,
                "failed": failed,
                "setup_failed": setup_failed,
                "total_call_time_sec": round(total_call, 6),
                "mean_call_time_sec": round(mean, 6),
                "max_call_time_sec": round(mx, 6),
                "call_samples": n,
            },
        },
        "per_test": sorted(per, key=lambda r: r["nodeid"]),
    }

    out = _metrics_path()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
