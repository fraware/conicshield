from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def _get(obj: Any, *keys: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, Mapping):
        for k in keys:
            if k in obj:
                return obj[k]
        return default
    for k in keys:
        if hasattr(obj, k):
            return getattr(obj, k)
    return default


def normalize_moreau_info(
    info: Mapping[str, Any] | Any | None,
    *,
    warm_started: bool,
    objective_value: float | None = None,
) -> dict[str, Any]:
    """Map vendor solve metadata to stable keys for ``ProjectionResult`` / JSON.

    Accepts a dict-like object or an object with attributes (e.g. ``moreau`` SolveInfo).
    Unknown fields become ``None``.
    """
    status = _get(info, "status", "solver_status", default=None)
    if status is not None:
        status = str(status)

    out: dict[str, Any] = {
        "solver_status": status,
        "objective_value": objective_value
        if objective_value is not None
        else _get(info, "objective", "obj_val", "objective_value", default=None),
        "solve_time_sec": _get(info, "solve_time", "solve_time_sec", default=None),
        "setup_time_sec": _get(info, "setup_time", "setup_time_sec", default=None),
        "construction_time_sec": _get(info, "construction_time", "construction_time_sec", default=None),
        "iterations": _get(info, "iterations", "iter", "k", default=None),
        "device": _get(info, "device", default=None),
        "warm_started": warm_started,
    }
    if out["device"] is not None:
        out["device"] = str(out["device"])
    for key in ("solve_time_sec", "setup_time_sec", "construction_time_sec"):
        v = out[key]
        if v is not None:
            out[key] = float(v)
    it = out["iterations"]
    if it is not None:
        out["iterations"] = int(it)
    return out


def telemetry_into_projection_fields(telemetry: Mapping[str, Any]) -> dict[str, Any]:
    """Subset of kwargs accepted by ``ProjectionResult`` for telemetry slots."""
    return {
        "solver_status": telemetry.get("solver_status") or "unknown",
        "objective_value": telemetry.get("objective_value"),
        "solve_time_sec": telemetry.get("solve_time_sec"),
        "setup_time_sec": telemetry.get("setup_time_sec"),
        "construction_time_sec": telemetry.get("construction_time_sec"),
        "iterations": telemetry.get("iterations"),
        "device": telemetry.get("device"),
        "warm_started": bool(telemetry.get("warm_started", False)),
    }


def extract_cvxpy_telemetry(problem: Any, *, warm_started: bool) -> dict[str, Any]:
    """Best-effort telemetry from a solved ``cvxpy.Problem`` (Moreau backend)."""
    obj_val = getattr(problem, "value", None)
    if obj_val is not None and not isinstance(obj_val, int | float):
        try:
            obj_val = float(obj_val)
        except (TypeError, ValueError):
            obj_val = None

    stats = getattr(problem, "solver_stats", None)
    raw: dict[str, Any] = {}
    if stats is not None:
        for attr in dir(stats):
            if attr.startswith("_"):
                continue
            try:
                raw[attr] = getattr(stats, attr)
            except Exception:
                continue

    status = getattr(problem, "status", None)
    info_payload: dict[str, Any] = {**raw, "status": status}
    return normalize_moreau_info(info_payload, warm_started=warm_started, objective_value=obj_val)
