"""Public (no-Moreau) tests for fixed-structure compilation."""

from __future__ import annotations

import numpy as np
import pytest

from conicshield.compilation.capabilities import (
    DEFAULT_COMPILATION_CAPABILITIES,
    CompilationCapabilities,
    resolve_capabilities,
)
from conicshield.compilation.compiled_template import CompiledShieldTemplate
from conicshield.compilation.structural_fingerprint import setup_values_fingerprint
from conicshield.compilation.topology import topology_from_shield_qp
from conicshield.specs.schema import (
    BoxConstraint,
    RateConstraint,
    SafetySpec,
    SimplexConstraint,
    TurnFeasibilityConstraint,
)
from conicshield.specs.shield_qp import parse_safety_spec_for_shield


def _spec(*, rate: float = 0.5, allowed: list[int] | None = None) -> SafetySpec:
    return SafetySpec(
        spec_id="compilation-test",
        action_dim=4,
        constraints=[
            SimplexConstraint(total=1.0),
            TurnFeasibilityConstraint(allowed_actions=allowed or [0, 1, 2, 3]),
            BoxConstraint(lower=[0.0] * 4, upper=[1.0] * 4),
            RateConstraint(max_delta=[rate] * 4),
        ],
    )


def test_topology_fingerprint_stable_under_numeric_bound_changes() -> None:
    a = parse_safety_spec_for_shield(_spec(rate=0.2))
    b_spec = SafetySpec(
        spec_id="compilation-test",
        action_dim=4,
        constraints=[
            SimplexConstraint(total=1.0),
            TurnFeasibilityConstraint(allowed_actions=[0, 1, 2, 3]),
            BoxConstraint(lower=[0.0] * 4, upper=[0.9, 1.0, 1.0, 1.0]),
            RateConstraint(max_delta=[0.8] * 4),
        ],
    )
    b = parse_safety_spec_for_shield(b_spec)
    ta = topology_from_shield_qp(a)
    tb = topology_from_shield_qp(b)
    assert ta.structural_fingerprint == tb.structural_fingerprint


def test_topology_changes_when_admissibility_mask_changes() -> None:
    a = topology_from_shield_qp(parse_safety_spec_for_shield(_spec(allowed=[0, 1, 2, 3])))
    b = topology_from_shield_qp(parse_safety_spec_for_shield(_spec(allowed=[1])))
    assert a.structural_fingerprint != b.structural_fingerprint
    assert "prohibit:0" in b.equality_ids


def test_compiled_template_fill_without_dense_intermediates() -> None:
    data = parse_safety_spec_for_shield(_spec())
    tmpl = CompiledShieldTemplate.compile(data)
    buf = tmpl.allocate_buffers()
    proposed = np.array([0.4, 0.3, 0.2, 0.1], dtype=np.float64)
    prev = np.full(4, 0.25, dtype=np.float64)
    fp1 = tmpl.fill(
        buf,
        data,
        proposed,
        prev,
        None,
        policy_weight=1.0,
        reference_weight=0.0,
    )
    assert buf.p_values.shape == (4,)
    assert buf.q.shape == (4,)
    assert buf.b.shape == (tmpl.layout.m,)
    assert np.allclose(buf.p_values, 2.0)
    # Second fill with same weights reuses A constants path.
    fp2 = tmpl.fill(
        buf,
        data,
        proposed,
        prev,
        None,
        policy_weight=1.0,
        reference_weight=0.0,
        copy_a_constants=False,
    )
    assert fp1 == fp2
    # Weight scale change alters setup fingerprint.
    fp3 = tmpl.fill(
        buf,
        data,
        proposed,
        prev,
        None,
        policy_weight=2.0,
        reference_weight=0.0,
        copy_a_constants=False,
    )
    assert fp3 != fp1


def test_setup_values_fingerprint_ignores_q_and_b() -> None:
    p = np.ones(4)
    a = np.array([1.0, -1.0, 1.0])
    assert setup_values_fingerprint(p, a) == setup_values_fingerprint(p.copy(), a.copy())
    assert setup_values_fingerprint(p, a) != setup_values_fingerprint(2 * p, a)


def test_sparse_ax_residual_matches_manual_simplex() -> None:
    data = parse_safety_spec_for_shield(_spec())
    tmpl = CompiledShieldTemplate.compile(data)
    buf = tmpl.allocate_buffers()
    x = np.array([0.25, 0.25, 0.25, 0.25], dtype=np.float64)
    tmpl.fill(buf, data, x, x, None, policy_weight=1.0, reference_weight=0.0)
    resid = tmpl.sparse_ax_residual(buf, x)
    # Simplex equality residual should be ~0 for a feasible point.
    assert abs(resid[tmpl.layout.b_simplex_index]) < 1e-12


def test_capability_flags_default_off() -> None:
    caps = resolve_capabilities(None)
    assert caps == DEFAULT_COMPILATION_CAPABILITIES
    assert caps.enable_direct_variable_cones is False
    assert caps.enable_cpu_algorithm_autotune is False


def test_direct_variable_cones_flag_rejected_by_batch_projector() -> None:
    from conicshield.core.moreau_batched import NativeMoreauCompiledBatchProjector

    with pytest.raises(ValueError, match="enable_direct_variable_cones"):
        NativeMoreauCompiledBatchProjector(
            spec=_spec(),
            capabilities=CompilationCapabilities(enable_direct_variable_cones=True),
        )


def test_template_bind_rebuilds_on_structure_change() -> None:
    from conicshield.core.moreau_batched import NativeMoreauCompiledBatchProjector

    bat = NativeMoreauCompiledBatchProjector(spec=_spec(allowed=[0, 1, 2, 3]))
    fp0 = bat.structural_fingerprint
    assert bat.bind_spec(_spec(allowed=[0, 1, 2, 3], rate=0.9)) == "reused"
    assert bat.structural_fingerprint == fp0
    assert bat.bind_spec(_spec(allowed=[1])) == "rebuild"
    assert bat.structural_fingerprint != fp0
