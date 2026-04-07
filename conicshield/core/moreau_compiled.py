from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from conicshield.core.result import ProjectionResult
from conicshield.core.telemetry import normalize_moreau_info, telemetry_into_projection_fields
from conicshield.solver_errors import require_solver_module
from conicshield.specs.native_moreau_builder import build_moreau_standard_form
from conicshield.specs.schema import SafetySpec
from conicshield.specs.shield_qp import parse_safety_spec_for_shield


@dataclass(slots=True)
class NativeMoreauCompiledOptions:
    device: str = "cpu"
    auto_tune: bool = False
    enable_grad: bool = False
    max_iter: int = 200
    time_limit: float = float("inf")
    verbose: bool = False
    active_tol: float = 1e-6
    persist_warm_start: bool = True
    policy_weight: float = 1.0
    reference_weight: float = 0.0


class NativeMoreauCompiledProjector:
    """Native Moreau ``Solver`` path (same QP family as ``CVXPYMoreauProjector``)."""

    def __init__(
        self,
        *,
        spec: SafetySpec,
        options: NativeMoreauCompiledOptions | None = None,
    ) -> None:
        self.spec = spec
        self.options = options or NativeMoreauCompiledOptions()
        self._warm: Any = None

    def project(
        self,
        proposed_action: np.ndarray,
        previous_action: np.ndarray | None = None,
        *,
        reference_action: np.ndarray | None = None,
        policy_weight: float = 1.0,
        reference_weight: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> ProjectionResult:
        require_solver_module("moreau", "native Moreau projector")
        import moreau

        data = parse_safety_spec_for_shield(self.spec)
        p_csr, q, a_csr, b_full, cones = build_moreau_standard_form(
            data,
            proposed_action,
            previous_action,
            reference_action,
            policy_weight=policy_weight,
            reference_weight=reference_weight,
        )

        dev = self.options.device
        if dev in ("auto", ""):
            dev = "cpu"

        settings_kw: dict[str, Any] = {
            "max_iter": int(self.options.max_iter),
            "verbose": bool(self.options.verbose),
        }
        if np.isfinite(self.options.time_limit) and self.options.time_limit > 0:
            settings_kw["time_limit"] = float(self.options.time_limit)
        for opt_key in ("auto_tune", "enable_grad"):
            val = getattr(self.options, opt_key, None)
            if val is not None:
                settings_kw[opt_key] = bool(val)
        settings = moreau.Settings(device=str(dev), **settings_kw)

        solver = moreau.Solver(p_csr, q, a_csr, b_full, cones=cones, settings=settings)

        warm_started = False
        warm = self._warm if self.options.persist_warm_start else None
        try:
            solution = solver.solve(warm_start=warm)
        except Exception:
            self._warm = None
            raise

        if self.options.persist_warm_start and hasattr(solution, "to_warm_start"):
            try:
                self._warm = solution.to_warm_start()
                warm_started = warm is not None
            except Exception:
                self._warm = None

        xv = np.asarray(solution.x, dtype=np.float64).reshape(-1)
        proposed = np.asarray(proposed_action, dtype=np.float64).reshape(-1)
        diff = float(np.linalg.norm(xv - proposed))
        intervened = diff > 1e-8

        info = getattr(solver, "info", None)
        obj = None
        if hasattr(solution, "obj_val"):
            try:
                obj = float(solution.obj_val)
            except (TypeError, ValueError):
                obj = None
        tel = normalize_moreau_info(info, warm_started=warm_started, objective_value=obj)
        tel_fields = telemetry_into_projection_fields(tel)

        active: list[str] = []
        if np.any(~data.allowed_mask):
            active.append("turn_feasibility")

        return ProjectionResult(
            proposed_action=proposed,
            corrected_action=xv,
            intervened=intervened,
            intervention_norm=diff,
            active_constraints=active,
            metadata=dict(metadata or {}),
            **tel_fields,
        )
