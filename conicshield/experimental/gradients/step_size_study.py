"""Log-grid step-size study for finite-difference Jacobians (R11).

Reports truncation vs noise regimes, stable interval, selected step, and
agreement sensitivity across a logarithmic h grid.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from conicshield.experimental.gradients.finite_difference import (
    ActiveSetFn,
    ArrayFn,
    central_finite_difference_jacobian,
    fd_agreement_metric,
)


@dataclass(slots=True)
class StepSizeSample:
    h: float
    jacobian_norm: float
    agreement_vs_neighbor: float | None
    active_set_changed: bool
    failure_status: str | None
    regime: str  # truncation | stable | noise | failed | unknown

    def as_dict(self) -> dict[str, Any]:
        return {
            "h": self.h,
            "jacobian_norm": self.jacobian_norm,
            "agreement_vs_neighbor": self.agreement_vs_neighbor,
            "active_set_changed": self.active_set_changed,
            "failure_status": self.failure_status,
            "regime": self.regime,
        }


@dataclass(slots=True)
class StepSizeStudyReport:
    parameter_name: str
    grid: tuple[float, ...]
    samples: list[StepSizeSample] = field(default_factory=list)
    stable_interval: tuple[float, float] | None = None
    selected_step: float | None = None
    truncation_regime_hs: tuple[float, ...] = ()
    noise_regime_hs: tuple[float, ...] = ()
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "parameter_name": self.parameter_name,
            "grid": list(self.grid),
            "samples": [s.as_dict() for s in self.samples],
            "stable_interval": None if self.stable_interval is None else list(self.stable_interval),
            "selected_step": self.selected_step,
            "truncation_regime_hs": list(self.truncation_regime_hs),
            "noise_regime_hs": list(self.noise_regime_hs),
            "notes": self.notes,
            "study": "fd_step_size_log_grid_r11",
        }


def default_log_grid(
    *,
    h_min: float = 1e-8,
    h_max: float = 1e-2,
    n: int = 8,
) -> tuple[float, ...]:
    if n < 2:
        return (float(h_max),)
    return tuple(float(h) for h in np.geomspace(float(h_min), float(h_max), int(n)))


def run_step_size_study(
    f: ArrayFn,
    x: np.ndarray,
    *,
    parameter_name: str = "proposed_action",
    grid: tuple[float, ...] | list[float] | None = None,
    active_set_fn: ActiveSetFn | None = None,
    stable_agreement_threshold: float = 5e-2,
) -> StepSizeStudyReport:
    """Evaluate central FD on a log grid and classify truncation/stable/noise."""

    hs = tuple(grid) if grid is not None else default_log_grid()
    x0 = np.asarray(x, dtype=np.float64).reshape(-1)
    jacs: list[np.ndarray | None] = []
    samples: list[StepSizeSample] = []

    for h in hs:
        fd = central_finite_difference_jacobian(
            f, x0, h=float(h), parameter_name=parameter_name, active_set_fn=active_set_fn
        )
        if fd.failure_status is not None or fd.jacobian.size == 0 or not np.all(np.isfinite(fd.jacobian)):
            jacs.append(None)
            samples.append(
                StepSizeSample(
                    h=float(h),
                    jacobian_norm=float("nan"),
                    agreement_vs_neighbor=None,
                    active_set_changed=bool(fd.active_set_changed),
                    failure_status=fd.failure_status or "non_finite_jacobian",
                    regime="failed",
                )
            )
            continue
        jacs.append(fd.jacobian)
        samples.append(
            StepSizeSample(
                h=float(h),
                jacobian_norm=float(np.linalg.norm(fd.jacobian, ord="fro")),
                agreement_vs_neighbor=None,
                active_set_changed=bool(fd.active_set_changed),
                failure_status=None,
                regime="unknown",
            )
        )

    # Neighbor agreement: compare each sample to next finer step (smaller h).
    # Grid is ascending; neighbor with smaller truncation is previous index.
    for i in range(len(samples)):
        if jacs[i] is None:
            continue
        # Prefer agreement with next-smaller h if available, else next-larger.
        neighbor_idx = i - 1 if i > 0 and jacs[i - 1] is not None else (i + 1 if i + 1 < len(jacs) else None)
        if neighbor_idx is not None and jacs[neighbor_idx] is not None:
            agree = fd_agreement_metric(jacs[i], jacs[neighbor_idx])  # type: ignore[arg-type]
            samples[i].agreement_vs_neighbor = agree

    # Classify regimes: large h → truncation (poor neighbor agree + large h),
    # small h → noise (poor agree + small h), mid → stable if agree good.
    mid = 0.5 * (math_log_mid(hs) if hs else 1e-5)
    for s in samples:
        if s.regime == "failed":
            continue
        agree = s.agreement_vs_neighbor
        if agree is None or not np.isfinite(agree):
            s.regime = "unknown"
            continue
        if agree <= stable_agreement_threshold and not s.active_set_changed:
            s.regime = "stable"
        elif s.h >= mid:
            s.regime = "truncation"
        else:
            s.regime = "noise"

    stable_hs = [s.h for s in samples if s.regime == "stable"]
    trunc_hs = tuple(s.h for s in samples if s.regime == "truncation")
    noise_hs = tuple(s.h for s in samples if s.regime == "noise")
    stable_interval = (min(stable_hs), max(stable_hs)) if stable_hs else None

    selected: float | None = None
    if stable_hs:
        # Geometric-mean preference inside stable interval.
        selected = float(np.exp(np.mean(np.log(np.asarray(stable_hs, dtype=np.float64)))))
        # Snap to nearest grid point in stable set.
        selected = min(stable_hs, key=lambda h: abs(np.log(h) - np.log(selected)))
    elif samples:
        # Fall back to mid-grid successful sample.
        ok = [s for s in samples if s.failure_status is None]
        if ok:
            selected = ok[len(ok) // 2].h

    return StepSizeStudyReport(
        parameter_name=parameter_name,
        grid=hs,
        samples=samples,
        stable_interval=stable_interval,
        selected_step=selected,
        truncation_regime_hs=trunc_hs,
        noise_regime_hs=noise_hs,
        notes=(
            "Log-grid central FD study. Stable = neighbor relative Frobenius "
            f"≤ {stable_agreement_threshold} without active-set change. "
            "Truncation tends to large h; noise to small h."
        ),
    )


def math_log_mid(hs: tuple[float, ...] | list[float]) -> float:
    arr = np.asarray(list(hs), dtype=np.float64)
    arr = arr[np.isfinite(arr) & (arr > 0)]
    if arr.size == 0:
        return 1e-5
    return float(np.exp(0.5 * (np.log(arr.min()) + np.log(arr.max()))))
