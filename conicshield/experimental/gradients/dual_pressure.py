"""Dual-pressure analysis (do not equate dual magnitude with causal importance)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

INTERPRETATION_WARNING = (
    "Do not equate dual magnitude with causal importance without validating the interpretation. "
    "Normalized pressure is correlational evidence only."
)


@dataclass(slots=True)
class DualPressureReport:
    constraint_ids: tuple[str, ...]
    dual_values: np.ndarray
    normalized_pressure: np.ndarray
    interpretation_warning: str = INTERPRETATION_WARNING

    def as_dict(self) -> dict[str, Any]:
        return {
            "constraint_ids": list(self.constraint_ids),
            "dual_values": self.dual_values.tolist(),
            "normalized_pressure": self.normalized_pressure.tolist(),
            "interpretation_warning": self.interpretation_warning,
        }


def normalize_dual_pressure(
    *,
    constraint_ids: tuple[str, ...],
    dual_values: np.ndarray,
) -> DualPressureReport:
    d = np.asarray(dual_values, dtype=np.float64).reshape(-1)
    if len(constraint_ids) != d.size:
        raise ValueError("constraint_ids length must match dual_values")
    scale = float(np.max(np.abs(d))) if d.size else 1.0
    if scale <= 0.0:
        scale = 1.0
    return DualPressureReport(
        constraint_ids=constraint_ids,
        dual_values=d,
        normalized_pressure=d / scale,
    )


@dataclass(slots=True)
class DualPressureCorrelationStudy:
    """Correlational study vs intervention / transitions / disagreement / gradients / fallback."""

    n_samples: int
    pearson: dict[str, float | None] = field(default_factory=dict)
    spearman: dict[str, float | None] = field(default_factory=dict)
    interpretation_warning: str = INTERPRETATION_WARNING
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "n_samples": self.n_samples,
            "pearson": dict(self.pearson),
            "spearman": dict(self.spearman),
            "interpretation_warning": self.interpretation_warning,
            "notes": list(self.notes),
        }


def _pearson(a: np.ndarray, b: np.ndarray) -> float | None:
    if a.size < 3 or b.size < 3:
        return None
    if float(np.std(a)) < 1e-15 or float(np.std(b)) < 1e-15:
        return None
    return float(np.corrcoef(a, b)[0, 1])


def _spearman(a: np.ndarray, b: np.ndarray) -> float | None:
    if a.size < 3 or b.size < 3:
        return None
    ra = a.argsort().argsort().astype(np.float64)
    rb = b.argsort().argsort().astype(np.float64)
    return _pearson(ra, rb)


def correlate_dual_pressure(
    *,
    max_abs_normalized_pressure: np.ndarray,
    intervention_size: np.ndarray,
    active_set_transition: np.ndarray,
    disagreement_l2: np.ndarray | None = None,
    gradient_agreement: np.ndarray | None = None,
    fallback_indicator: np.ndarray | None = None,
) -> DualPressureCorrelationStudy:
    """Compute correlational associations; never claim causal importance."""

    p = np.asarray(max_abs_normalized_pressure, dtype=np.float64).reshape(-1)
    n = p.size
    targets: dict[str, np.ndarray] = {
        "intervention_size": np.asarray(intervention_size, dtype=np.float64).reshape(-1),
        "active_set_transition": np.asarray(active_set_transition, dtype=np.float64).reshape(-1),
    }
    if disagreement_l2 is not None:
        targets["disagreement_l2"] = np.asarray(disagreement_l2, dtype=np.float64).reshape(-1)
    if gradient_agreement is not None:
        targets["gradient_agreement"] = np.asarray(gradient_agreement, dtype=np.float64).reshape(-1)
    if fallback_indicator is not None:
        targets["fallback"] = np.asarray(fallback_indicator, dtype=np.float64).reshape(-1)

    for name, arr in targets.items():
        if arr.size != n:
            raise ValueError(f"{name} length {arr.size} != pressure length {n}")

    pearson = {k: _pearson(p, v) for k, v in targets.items()}
    spearman = {k: _spearman(p, v) for k, v in targets.items()}
    notes = [
        "Correlations are descriptive only.",
        "dual magnitude ≠ causal importance",
    ]
    if all(v is None for v in pearson.values()):
        notes.append("negative_result: insufficient variance or sample size for correlations")
    return DualPressureCorrelationStudy(
        n_samples=n,
        pearson=pearson,
        spearman=spearman,
        notes=notes,
    )
