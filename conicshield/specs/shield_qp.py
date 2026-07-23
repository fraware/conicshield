"""Canonical shield QP intermediate representation (IR) shared by all compilers.

``ShieldQPData`` is the **only** declared mathematical view consumed by:

* ``conicshield.specs.compiler.CVXPYMoreauProjector`` (CVXPY path)
* ``conicshield.specs.native_moreau_builder.build_moreau_standard_form`` (native path)

Both backends must encode the same inequalities / equalities implied by this IR.

Supported ``SafetySpec`` constraint kinds for v1: ``simplex``, ``turn_feasibility``,
``box``, ``rate``. Others raise ``NotImplementedError``.

Default when ``BoxConstraint`` is absent: unit box ``[0, 1]^n`` (probability family).
When present, box bounds are taken exactly as declared (finite).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from conicshield.specs.errors import (
    InvalidObjectiveWeightError,
    MissingFailSafePolicyError,
    NoAdmissibleActionError,
)

if TYPE_CHECKING:
    from conicshield.specs.schema import FailSafePolicy, SafetySpec


SUPPORTED_KINDS = frozenset({"simplex", "turn_feasibility", "box", "rate"})


@dataclass(frozen=True, slots=True)
class ShieldQPData:
    """Canonical dense IR for the action-simplex shield QP family.

    Mathematical meaning
    --------------------
    Variables ``x ∈ R^n`` with ``n = action_dim``:

    * Equality: ``sum_i x_i = simplex_total``
    * Equality: ``x_i = 0`` for every ``i`` with ``allowed_mask[i] is False``
    * Box: ``lower_i <= x_i <= upper_i`` for every ``i`` (finite bounds)
    * Rate (when a previous action ``p`` is supplied at solve time):
      ``|x_i - p_i| <= max_delta_i`` for finite ``max_delta_i``
    """

    n: int
    simplex_total: float
    lower: np.ndarray
    upper: np.ndarray
    allowed_mask: np.ndarray  # bool length n — False means x[i] must be 0
    max_delta: np.ndarray
    fail_safe_policy: FailSafePolicy | None = None


def validate_objective_weights(
    policy_weight: float,
    reference_weight: float,
    *,
    reference_present: bool,
) -> tuple[float, float]:
    """Validate and return ``(policy_weight, effective_reference_weight)``.

    Rules (identical for CVXPY and native):

    * ``policy_weight`` finite and ``>= 0``
    * ``reference_weight`` finite and ``>= 0``
    * when no reference action is supplied, effective reference weight is ``0``
    * ``policy_weight + effective_reference_weight > 0``

    No silent clipping or ``1e-12`` coercion.
    """
    pw = float(policy_weight)
    rw_declared = float(reference_weight)
    if not math.isfinite(pw):
        raise InvalidObjectiveWeightError(f"policy_weight must be finite (got {policy_weight!r})")
    if pw < 0.0:
        raise InvalidObjectiveWeightError(f"policy_weight must be >= 0 (got {pw})")
    if not math.isfinite(rw_declared):
        raise InvalidObjectiveWeightError(
            f"reference_weight must be finite (got {reference_weight!r})"
        )
    if rw_declared < 0.0:
        raise InvalidObjectiveWeightError(f"reference_weight must be >= 0 (got {rw_declared})")

    rw = rw_declared if reference_present else 0.0
    if pw + rw <= 0.0:
        raise InvalidObjectiveWeightError(
            "policy_weight + reference_weight must be strictly positive "
            f"(got policy_weight={pw}, effective_reference_weight={rw})"
        )
    return pw, rw


def parse_safety_spec_for_shield(spec: SafetySpec) -> ShieldQPData:
    """Lower a validated ``SafetySpec`` into the canonical ``ShieldQPData`` IR."""
    from conicshield.specs.schema import (
        BoxConstraint,
        ConstraintKind,
        FailSafePolicy,
        RateConstraint,
        SimplexConstraint,
        TurnFeasibilityConstraint,
    )

    n = spec.action_dim
    simplex_total = 1.0
    # Unit-box default for the probability-simplex shield family when no BoxConstraint.
    lower = np.zeros(n, dtype=np.float64)
    upper = np.ones(n, dtype=np.float64)
    allowed = np.ones(n, dtype=bool)
    max_delta = np.full(n, np.inf, dtype=np.float64)
    saw_turn = False

    for c in spec.constraints:
        kind_v = getattr(c, "kind", None)
        if kind_v is None:
            raise TypeError("constraint missing kind")
        kind = kind_v.value if isinstance(kind_v, ConstraintKind) else str(kind_v)
        if kind not in SUPPORTED_KINDS:
            raise NotImplementedError(
                f"Constraint kind {kind!r} is not implemented for solver-backed projection. "
                f"Supported: {sorted(SUPPORTED_KINDS)}."
            )
        if isinstance(c, SimplexConstraint):
            simplex_total = float(c.total)
        elif isinstance(c, BoxConstraint):
            lower = np.asarray(c.lower, dtype=np.float64).reshape(-1).copy()
            upper = np.asarray(c.upper, dtype=np.float64).reshape(-1).copy()
            if lower.shape[0] != n or upper.shape[0] != n:
                raise ValueError("box bound length mismatch against action_dim")
        elif isinstance(c, TurnFeasibilityConstraint):
            saw_turn = True
            allowed[:] = False
            for idx in c.allowed_actions:
                if idx < 0 or idx >= n:
                    raise ValueError(f"allowed_actions index out of range: {idx}")
                allowed[idx] = True
        elif isinstance(c, RateConstraint):
            max_delta = np.asarray(c.max_delta, dtype=np.float64).reshape(-1).copy()
            if max_delta.shape[0] != n:
                raise ValueError("max_delta length mismatch against action_dim")

    if saw_turn and not np.any(allowed):
        # No silent "all actions allowed" recovery — require explicit fail-safe.
        policy = spec.fail_safe_policy
        if policy is None:
            raise MissingFailSafePolicyError(
                "no action is admissible; set SafetySpec.fail_safe_policy explicitly "
                f"(e.g. FailSafePolicy.{FailSafePolicy.REJECT.name})"
            )
        # Empty admissible set cannot be recovered by any fail-safe synthesizer.
        raise NoAdmissibleActionError(
            "no action is admissible; fail-safe policies cannot synthesize an "
            f"action from an empty allowed set (policy={policy!r})"
        )

    return ShieldQPData(
        n=n,
        simplex_total=simplex_total,
        lower=lower,
        upper=upper,
        allowed_mask=allowed,
        max_delta=max_delta,
        fail_safe_policy=spec.fail_safe_policy,
    )


def objective_pq(
    proposed: np.ndarray,
    reference: np.ndarray | None,
    *,
    policy_weight: float,
    reference_weight: float,
    n: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Return ``(P_dense, q)`` for Moreau standard form ``min 0.5 x'Px + q'x``."""
    pw, rw = validate_objective_weights(
        policy_weight,
        reference_weight,
        reference_present=reference is not None,
    )
    p = np.asarray(proposed, dtype=np.float64).reshape(-1)
    if p.shape[0] != n:
        raise ValueError(f"proposed_action length {p.shape[0]} != action_dim {n}")
    scale = pw + rw
    p_mat = np.eye(n, dtype=np.float64) * (2.0 * scale)
    q = -2.0 * pw * p
    if reference is not None and rw > 0.0:
        r = np.asarray(reference, dtype=np.float64).reshape(-1)
        if r.shape[0] != n:
            raise ValueError(f"reference_action length {r.shape[0]} != action_dim {n}")
        q = q - 2.0 * rw * r
    return p_mat, q
