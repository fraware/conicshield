"""Structural vs numerical fingerprints for projector / solver caches.

Structural fingerprints intentionally exclude proposals, previous actions,
parametric bounds/rates/refs/weights, and free-form metadata when those values
can be represented as fill-ins on a fixed row/cone topology.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from conicshield.specs.schema import (
    BoxConstraint,
    ClearanceConstraint,
    ConstraintKind,
    ProgressConstraint,
    RateConstraint,
    SafetySpec,
    SimplexConstraint,
    TurnFeasibilityConstraint,
)


def _kind_value(kind: Any) -> str:
    if isinstance(kind, ConstraintKind):
        return kind.value
    return str(kind)


@dataclass(frozen=True, slots=True)
class StructuralFingerprint:
    """Opaque structural cache key plus the canonical payload used to derive it."""

    digest: str
    payload: tuple[Any, ...]

    def __str__(self) -> str:
        return self.digest


@dataclass(frozen=True, slots=True)
class NumericalSignature:
    """Numeric / parametric values that may change without altering CSR topology."""

    digest: str
    payload: tuple[Any, ...]

    def __str__(self) -> str:
        return self.digest


def _hash_payload(payload: Any) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:24]


def structural_fingerprint(
    spec: SafetySpec,
    *,
    backend: str | None = None,
    structural_options: Mapping[str, Any] | None = None,
) -> StructuralFingerprint:
    """Fingerprint action dim, constraint kinds, row/cone topology hints, backend options.

    Includes turn-feasibility admissible indices (equality-row topology) and which
    constraint kinds are present. Excludes box/rate numeric values, slack weight,
    proposals, previous action, and metadata.
    """
    kinds: list[str] = []
    turn_allowed: list[int] | None = None
    has_box = False
    has_rate = False
    has_simplex = False
    has_progress = False
    has_clearance = False
    for c in spec.constraints:
        kinds.append(_kind_value(c.kind))
        if isinstance(c, TurnFeasibilityConstraint):
            turn_allowed = sorted(int(i) for i in c.allowed_actions)
        elif isinstance(c, BoxConstraint):
            has_box = True
        elif isinstance(c, RateConstraint):
            has_rate = True
        elif isinstance(c, SimplexConstraint):
            has_simplex = True
        elif isinstance(c, ProgressConstraint):
            has_progress = True
        elif isinstance(c, ClearanceConstraint):
            has_clearance = True

    opts = dict(structural_options or {})
    # Only backend-relevant *structural* options belong here (not tolerances / weights).
    structural_opts = {
        k: opts[k]
        for k in sorted(opts)
        if k
        in {
            "use_compiled_solver",
            "device",
            "batch_size",
            "auto_tune",
            "enable_grad",
        }
    }
    payload = (
        int(spec.action_dim),
        tuple(kinds),
        has_box,
        has_rate,
        has_simplex,
        has_progress,
        has_clearance,
        None if turn_allowed is None else tuple(turn_allowed),
        None if backend is None else str(backend),
        tuple(sorted((str(k), structural_opts[k]) for k in structural_opts)),
    )
    return StructuralFingerprint(digest=_hash_payload(payload), payload=payload)


def numerical_signature(spec: SafetySpec) -> NumericalSignature:
    """Fingerprint parametric numeric fields that do not redefine CSR sparsity alone."""
    boxes: list[tuple[tuple[float, ...], tuple[float, ...]]] = []
    rates: list[tuple[float, ...]] = []
    simplex_totals: list[float] = []
    progress: list[float] = []
    clearance: list[float] = []
    for c in spec.constraints:
        if isinstance(c, BoxConstraint):
            boxes.append((tuple(float(x) for x in c.lower), tuple(float(x) for x in c.upper)))
        elif isinstance(c, RateConstraint):
            rates.append(tuple(float(x) for x in c.max_delta))
        elif isinstance(c, SimplexConstraint):
            simplex_totals.append(float(c.total))
        elif isinstance(c, ProgressConstraint):
            progress.append(float(c.min_progress))
        elif isinstance(c, ClearanceConstraint):
            clearance.append(float(c.min_clearance))
    payload = (
        str(spec.spec_id),
        str(spec.version),
        float(spec.slack_weight),
        None if spec.fail_safe_policy is None else str(spec.fail_safe_policy),
        tuple(boxes),
        tuple(rates),
        tuple(simplex_totals),
        tuple(progress),
        tuple(clearance),
    )
    return NumericalSignature(digest=_hash_payload(payload), payload=payload)
