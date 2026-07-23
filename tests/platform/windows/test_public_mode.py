"""Windows Public mode qualification (CS-SOLVER-111 / S6)."""

from __future__ import annotations

import json
import sys

import numpy as np

from conicshield.backends.base import Backend, resolve_backend
from conicshield.core.solver_factory import create_projector
from conicshield.platform.doctor import run_solver_doctor
from conicshield.platform.windows_modes import WindowsOperatingMode, describe_modes
from conicshield.specs.schema import BoxConstraint, SafetySpec, SimplexConstraint


def _spec() -> SafetySpec:
    return SafetySpec(
        spec_id="windows/public-mode",
        version="0.1.0",
        action_dim=2,
        constraints=[
            SimplexConstraint(total=1.0),
            BoxConstraint(lower=[0.0, 0.0], upper=[1.0, 1.0]),
        ],
    )


def test_windows_public_clarabel_releases_verified_action() -> None:
    projector = create_projector(spec=_spec(), backend=Backend.PUBLIC_CLARABEL)
    result = projector.project(np.array([0.8, 0.2], dtype=np.float64))
    assert result.verification is not None
    assert result.verification.passed
    assert result.release_decision is not None
    assert str(result.release_decision).startswith("accepted_")
    assert abs(float(np.sum(result.corrected_action)) - 1.0) < 1e-5


def test_windows_public_auto_resolves_without_vendor() -> None:
    assert resolve_backend(Backend.AUTO) is Backend.PUBLIC_CLARABEL
    projector = create_projector(spec=_spec(), backend=Backend.AUTO)
    result = projector.project(np.array([0.55, 0.45], dtype=np.float64))
    assert result.verification is not None and result.verification.passed


def test_solver_doctor_json_on_host() -> None:
    report = run_solver_doctor(run_license_check=False)
    payload = report.as_dict()
    # Round-trip JSON (CLI contract).
    raw = json.dumps(payload, default=str)
    loaded = json.loads(raw)
    assert "selected_solver_settings" in loaded
    auto = loaded["selected_solver_settings"]["auto_policy"]
    assert auto["auto_resolves_to"] == "public_clarabel"
    if sys.platform == "win32":
        notes = " ".join(loaded.get("platform_notes") or [])
        assert "moreau" in notes.lower() or loaded.get("os_name")


def test_modes_document_no_native_moreau_claim() -> None:
    modes = describe_modes()
    assert {m["mode"] for m in modes} == {m.value for m in WindowsOperatingMode}
    assert all(m["claims_native_moreau_on_windows"] is False for m in modes)
