from __future__ import annotations

from types import SimpleNamespace

from conicshield.core.telemetry import (
    extract_cvxpy_telemetry,
    normalize_moreau_info,
    telemetry_into_projection_fields,
)


def test_normalize_moreau_info_mapping() -> None:
    raw = {
        "status": "optimal",
        "objective": 1.25,
        "solve_time": 0.01,
        "setup_time": 0.002,
        "construction_time": 0.001,
        "iterations": 12,
        "device": "cpu",
    }
    n = normalize_moreau_info(raw, warm_started=True)
    assert n["solver_status"] == "optimal"
    assert n["objective_value"] == 1.25
    assert n["solve_time_sec"] == 0.01
    assert n["iterations"] == 12
    assert n["warm_started"] is True


def test_normalize_moreau_info_object_attributes() -> None:
    info = SimpleNamespace(
        status="optimal",
        solve_time=0.03,
        iterations=5,
        device="cuda",
    )
    n = normalize_moreau_info(info, warm_started=False, objective_value=-0.5)
    assert n["objective_value"] == -0.5
    assert n["device"] == "cuda"


def test_normalize_empty_info() -> None:
    n = normalize_moreau_info(None, warm_started=False)
    assert n["solver_status"] is None
    assert n["warm_started"] is False


def test_telemetry_into_projection_fields_defaults_status() -> None:
    fields = telemetry_into_projection_fields({"warm_started": False})
    assert fields["solver_status"] == "unknown"


def test_extract_cvxpy_telemetry_minimal() -> None:
    prob = SimpleNamespace(value=0.5, status="optimal", solver_stats=SimpleNamespace(solve_time=0.1))
    tel = extract_cvxpy_telemetry(prob, warm_started=False)
    assert tel.get("objective_value") == 0.5
    assert tel.get("solver_status") == "optimal"
