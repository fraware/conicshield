"""Active-set transition protocol for FD / observatory (R11).

Compare active sets at base / +ε / −ε and classify:
  stable | one_sided | two_sided | ambiguous

At transitions, report one-sided derivatives; do not treat central FD as a
unique Jacobian.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import numpy as np

from conicshield.experimental.gradients.finite_difference import (
    ActiveSetFn,
    ArrayFn,
    one_sided_finite_difference_jacobian,
)
from conicshield.experimental.gradients.modes import GradientMode


class ActiveSetTransitionClass(StrEnum):
    STABLE = "stable"
    ONE_SIDED = "one_sided"
    TWO_SIDED = "two_sided"
    AMBIGUOUS = "ambiguous"


@dataclass(slots=True)
class ActiveSetTransitionReport:
    classification: ActiveSetTransitionClass
    epsilon: float
    active_set_base: tuple[str, ...]
    active_set_plus: tuple[str, ...]
    active_set_minus: tuple[str, ...]
    plus_differs: bool
    minus_differs: bool
    plus_equals_minus: bool
    prefer_one_sided_derivatives: bool
    notes: str = ""
    extras: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "classification": str(self.classification),
            "epsilon": self.epsilon,
            "active_set_base": list(self.active_set_base),
            "active_set_plus": list(self.active_set_plus),
            "active_set_minus": list(self.active_set_minus),
            "plus_differs": self.plus_differs,
            "minus_differs": self.minus_differs,
            "plus_equals_minus": self.plus_equals_minus,
            "prefer_one_sided_derivatives": self.prefer_one_sided_derivatives,
            "notes": self.notes,
            "extras": dict(self.extras),
            "central_fd_not_unique_jacobian": self.prefer_one_sided_derivatives,
        }


def _as_set(ids: tuple[str, ...] | list[str] | None) -> frozenset[str]:
    return frozenset(ids or ())


def classify_active_set_transition(
    *,
    active_set_base: tuple[str, ...] | list[str],
    active_set_plus: tuple[str, ...] | list[str],
    active_set_minus: tuple[str, ...] | list[str],
    epsilon: float,
) -> ActiveSetTransitionReport:
    """Classify transition from base / +ε / −ε active-set triple."""

    base = _as_set(active_set_base)
    plus = _as_set(active_set_plus)
    minus = _as_set(active_set_minus)
    plus_differs = plus != base
    minus_differs = minus != base
    plus_eq_minus = plus == minus

    if not plus_differs and not minus_differs:
        cls = ActiveSetTransitionClass.STABLE
        prefer_one = False
        notes = "Active set identical at base, +ε, and −ε."
    elif plus_differs and minus_differs:
        if plus_eq_minus:
            # Both sides jump to the same new set — treat as ambiguous for central FD.
            cls = ActiveSetTransitionClass.AMBIGUOUS
            prefer_one = True
            notes = "Both +ε and −ε differ from base but agree with each other; central FD ambiguous."
        else:
            cls = ActiveSetTransitionClass.TWO_SIDED
            prefer_one = True
            notes = "Both +ε and −ε differ from base (and from each other); report one-sided derivatives."
    elif plus_differs or minus_differs:
        cls = ActiveSetTransitionClass.ONE_SIDED
        prefer_one = True
        notes = "Exactly one side of ±ε differs from base; prefer one-sided derivatives."
    else:
        cls = ActiveSetTransitionClass.AMBIGUOUS
        prefer_one = True
        notes = "Unexpected active-set triple; treat as ambiguous."

    return ActiveSetTransitionReport(
        classification=cls,
        epsilon=float(epsilon),
        active_set_base=tuple(sorted(base)),
        active_set_plus=tuple(sorted(plus)),
        active_set_minus=tuple(sorted(minus)),
        plus_differs=plus_differs,
        minus_differs=minus_differs,
        plus_equals_minus=plus_eq_minus,
        prefer_one_sided_derivatives=prefer_one,
        notes=notes,
    )


def probe_active_set_transition(
    *,
    x: np.ndarray,
    epsilon: float,
    active_set_fn: ActiveSetFn,
    coordinate: int = 0,
) -> ActiveSetTransitionReport:
    """Probe active sets at base / +ε e_i / −ε e_i for one coordinate."""

    x0 = np.asarray(x, dtype=np.float64).reshape(-1)
    i = int(coordinate) % max(x0.size, 1)
    xp = x0.copy()
    xm = x0.copy()
    if x0.size:
        xp[i] += float(epsilon)
        xm[i] -= float(epsilon)
    try:
        base = tuple(active_set_fn(x0))
        plus = tuple(active_set_fn(xp))
        minus = tuple(active_set_fn(xm))
    except Exception as exc:  # noqa: BLE001
        return ActiveSetTransitionReport(
            classification=ActiveSetTransitionClass.AMBIGUOUS,
            epsilon=float(epsilon),
            active_set_base=(),
            active_set_plus=(),
            active_set_minus=(),
            plus_differs=True,
            minus_differs=True,
            plus_equals_minus=False,
            prefer_one_sided_derivatives=True,
            notes=f"active_set_probe_failed:{type(exc).__name__}:{exc}",
        )
    report = classify_active_set_transition(
        active_set_base=base,
        active_set_plus=plus,
        active_set_minus=minus,
        epsilon=float(epsilon),
    )
    report.extras["coordinate"] = i
    return report


def probe_active_set_transition_all_coords(
    *,
    x: np.ndarray,
    epsilon: float,
    active_set_fn: ActiveSetFn,
) -> ActiveSetTransitionReport:
    """Aggregate per-coordinate probes; escalate to the strongest transition class."""

    x0 = np.asarray(x, dtype=np.float64).reshape(-1)
    if x0.size == 0:
        return classify_active_set_transition(
            active_set_base=(),
            active_set_plus=(),
            active_set_minus=(),
            epsilon=float(epsilon),
        )

    rank = {
        ActiveSetTransitionClass.STABLE: 0,
        ActiveSetTransitionClass.ONE_SIDED: 1,
        ActiveSetTransitionClass.TWO_SIDED: 2,
        ActiveSetTransitionClass.AMBIGUOUS: 3,
    }
    worst = probe_active_set_transition(
        x=x0, epsilon=epsilon, active_set_fn=active_set_fn, coordinate=0
    )
    per_coord: list[dict[str, Any]] = [worst.as_dict()]
    for j in range(1, x0.size):
        r = probe_active_set_transition(
            x=x0, epsilon=epsilon, active_set_fn=active_set_fn, coordinate=j
        )
        per_coord.append(r.as_dict())
        if rank[r.classification] > rank[worst.classification]:
            worst = r
    worst.extras["per_coordinate"] = per_coord
    worst.extras["n_coordinates"] = int(x0.size)
    return worst


def transition_aware_jacobians(
    f: ArrayFn,
    x: np.ndarray,
    *,
    h: float,
    parameter_name: str = "proposed_action",
    active_set_fn: ActiveSetFn | None = None,
) -> dict[str, Any]:
    """Return FD jacobians with transition classification; prefer one-sided at transitions."""

    x0 = np.asarray(x, dtype=np.float64).reshape(-1)
    if active_set_fn is None:
        transition = classify_active_set_transition(
            active_set_base=(),
            active_set_plus=(),
            active_set_minus=(),
            epsilon=h,
        )
        transition.notes = "No active_set_fn; classification defaults to stable."
    else:
        transition = probe_active_set_transition_all_coords(
            x=x0, epsilon=h, active_set_fn=active_set_fn
        )

    from conicshield.experimental.gradients.finite_difference import (
        central_finite_difference_jacobian,
    )

    central = central_finite_difference_jacobian(
        f, x0, h=h, parameter_name=parameter_name, active_set_fn=active_set_fn
    )
    forward = one_sided_finite_difference_jacobian(
        f, x0, h=h, parameter_name=parameter_name, forward=True, active_set_fn=active_set_fn
    )
    backward = one_sided_finite_difference_jacobian(
        f, x0, h=h, parameter_name=parameter_name, forward=False, active_set_fn=active_set_fn
    )

    preferred_mode = (
        str(GradientMode.ONE_SIDED_FINITE_DIFFERENCE)
        if transition.prefer_one_sided_derivatives
        else str(GradientMode.CENTRAL_FINITE_DIFFERENCE)
    )
    preferred = forward if transition.prefer_one_sided_derivatives else central

    return {
        "transition": transition.as_dict(),
        "central": central.as_dict(),
        "one_sided_forward": forward.as_dict(),
        "one_sided_backward": backward.as_dict(),
        "preferred_mode": preferred_mode,
        "preferred_jacobian": preferred.jacobian.tolist(),
        "central_fd_not_unique_jacobian": bool(transition.prefer_one_sided_derivatives),
    }
