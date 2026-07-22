"""Memory / cache behaviour for compiled templates (no vendor required)."""

from __future__ import annotations

import numpy as np

from conicshield.compilation.compiled_template import CompiledShieldTemplate
from conicshield.compilation.metrics import LifecycleMetrics
from conicshield.core.moreau_batched import NativeMoreauCompiledBatchProjector
from conicshield.specs.schema import (
    BoxConstraint,
    RateConstraint,
    SafetySpec,
    SimplexConstraint,
    TurnFeasibilityConstraint,
)
from conicshield.specs.shield_qp import parse_safety_spec_for_shield


def _spec(allowed: list[int] | None = None) -> SafetySpec:
    return SafetySpec(
        spec_id="cache-mem",
        action_dim=4,
        constraints=[
            SimplexConstraint(total=1.0),
            TurnFeasibilityConstraint(allowed_actions=allowed or [0, 1, 2, 3]),
            BoxConstraint(lower=[0.0] * 4, upper=[1.0] * 4),
            RateConstraint(max_delta=[0.5] * 4),
        ],
    )


def test_template_buffers_are_preallocated_and_reused() -> None:
    tmpl = CompiledShieldTemplate.compile(parse_safety_spec_for_shield(_spec()))
    buf = tmpl.allocate_buffers()
    p_ptr = buf.p_values.__array_interface__["data"][0]
    proposed = np.full(4, 0.25)
    tmpl.fill(
        buf,
        parse_safety_spec_for_shield(_spec()),
        proposed,
        proposed,
        None,
        policy_weight=1.0,
        reference_weight=0.0,
    )
    assert buf.p_values.__array_interface__["data"][0] == p_ptr


def test_bind_spec_reuses_structure_for_numeric_only_changes() -> None:
    metrics = LifecycleMetrics()
    bat = NativeMoreauCompiledBatchProjector(spec=_spec(), metrics=metrics)
    rebuilds_before = metrics.snapshot()["solver_rebuilds"]
    assert bat.bind_spec(_spec()) == "reused"
    # Numeric rate change keeps topology.
    assert (
        bat.bind_spec(
            SafetySpec(
                spec_id="cache-mem",
                action_dim=4,
                constraints=[
                    SimplexConstraint(total=1.0),
                    TurnFeasibilityConstraint(allowed_actions=[0, 1, 2, 3]),
                    BoxConstraint(lower=[0.0] * 4, upper=[0.95] * 4),
                    RateConstraint(max_delta=[0.9] * 4),
                ],
            )
        )
        == "reused"
    )
    assert metrics.snapshot()["solver_rebuilds"] == rebuilds_before
    assert bat.bind_spec(_spec(allowed=[1])) == "rebuild"
    assert metrics.snapshot()["solver_rebuilds"] == rebuilds_before + 1
