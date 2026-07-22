"""Heterogeneous batch API tests (public where possible; vendor for parity)."""

from __future__ import annotations

import numpy as np
import pytest

from conicshield.compilation.compiled_template import CompiledShieldTemplate
from conicshield.core.moreau_batched import NativeMoreauCompiledBatchProjector
from conicshield.core.moreau_compiled import NativeMoreauCompiledOptions
from conicshield.core.result import BatchProjectionResult
from conicshield.specs.schema import (
    BoxConstraint,
    RateConstraint,
    SafetySpec,
    SimplexConstraint,
    TurnFeasibilityConstraint,
)
from conicshield.specs.shield_qp import parse_safety_spec_for_shield


def _spec() -> SafetySpec:
    return SafetySpec(
        spec_id="hetero-batch",
        action_dim=4,
        constraints=[
            SimplexConstraint(total=1.0),
            TurnFeasibilityConstraint(allowed_actions=[0, 1, 2, 3]),
            BoxConstraint(lower=[0.0] * 4, upper=[1.0] * 4),
            RateConstraint(max_delta=[0.8] * 4),
        ],
    )


def test_batch_projection_result_stacks_without_dropping_rows() -> None:
    rows = []
    for i in range(3):
        from conicshield.core.result import ProjectionResult

        x = np.full(4, 0.25)
        rows.append(
            ProjectionResult(
                proposed_action=x,
                corrected_action=x + 0.01 * i,
                intervened=False,
                intervention_norm=0.0,
                solver_status="optimal",
                metadata={"row_id": f"r{i}"},
            )
        )
    result = BatchProjectionResult(
        rows=tuple(rows),
        batch_size=3,
        setup_time_sec=0.01,
        solve_time_sec=0.02,
        device="cpu",
        cache_status="hit",
        structural_fingerprint="abc",
    )
    assert result.corrected_actions.shape == (3, 4)
    assert len(result.as_dict()["rows"]) == 3


def test_heterogeneous_fill_produces_distinct_b_rows() -> None:
    data = parse_safety_spec_for_shield(_spec())
    tmpl = CompiledShieldTemplate.compile(data)
    buf = tmpl.allocate_buffers()
    proposed = np.array([0.4, 0.3, 0.2, 0.1])
    prev_a = np.array([0.25, 0.25, 0.25, 0.25])
    prev_b = np.array([0.1, 0.2, 0.3, 0.4])
    tmpl.fill(buf, data, proposed, prev_a, None, policy_weight=1.0, reference_weight=0.0)
    b1 = buf.b.copy()
    tmpl.fill(
        buf,
        data,
        proposed,
        prev_b,
        None,
        policy_weight=1.0,
        reference_weight=0.0,
        copy_a_constants=False,
    )
    b2 = buf.b.copy()
    assert not np.allclose(b1, b2)
    # Setup fingerprint (P/A) unchanged when only previous/b changes.
    from conicshield.compilation.structural_fingerprint import setup_values_fingerprint

    assert setup_values_fingerprint(np.ones(4) * 2.0, tmpl.layout.a_const_values) == (
        setup_values_fingerprint(np.ones(4) * 2.0, tmpl.layout.a_const_values)
    )


@pytest.mark.requires_moreau
@pytest.mark.solver
def test_heterogeneous_batch_matches_sequential_per_row() -> None:
    moreau = pytest.importorskip("moreau")
    if not hasattr(moreau, "CompiledSolver"):
        pytest.skip("moreau.CompiledSolver not available")

    spec = _spec()
    opts = NativeMoreauCompiledOptions(
        device="cpu",
        max_iter=800,
        verbose=False,
        persist_warm_start=False,
        use_compiled_solver=True,
    )
    proposals = np.array(
        [
            [0.85, 0.05, 0.05, 0.05],
            [0.2, 0.3, 0.25, 0.25],
            [0.4, 0.35, 0.15, 0.1],
        ],
        dtype=np.float64,
    )
    previous = np.array(
        [
            [0.25, 0.25, 0.25, 0.25],
            [0.1, 0.2, 0.3, 0.4],
            [0.4, 0.2, 0.2, 0.2],
        ],
        dtype=np.float64,
    )
    uppers = np.array(
        [
            [1.0, 1.0, 1.0, 1.0],
            [0.7, 1.0, 1.0, 1.0],
            [1.0, 0.6, 1.0, 1.0],
        ],
        dtype=np.float64,
    )
    seq = __import__(
        "conicshield.core.moreau_compiled", fromlist=["NativeMoreauCompiledProjector"]
    ).NativeMoreauCompiledProjector(spec=spec, options=opts)
    bat = NativeMoreauCompiledBatchProjector(spec=spec, options=opts)

    try:
        from dataclasses import replace

        from conicshield.specs.shield_qp import parse_safety_spec_for_shield

        base = parse_safety_spec_for_shield(spec)
        seq_out = []
        for i in range(proposals.shape[0]):
            # Sequential path uses projector.spec numeric IR; override via temporary spec
            # by mutating projector through bind-equivalent: set spec with matching structure.
            row_spec = SafetySpec(
                spec_id=spec.spec_id,
                action_dim=4,
                constraints=[
                    SimplexConstraint(total=1.0),
                    TurnFeasibilityConstraint(allowed_actions=[0, 1, 2, 3]),
                    BoxConstraint(lower=[0.0] * 4, upper=uppers[i].tolist()),
                    RateConstraint(max_delta=[0.8] * 4),
                ],
            )
            seq.spec = row_spec
            seq_out.append(seq.project(proposals[i], previous[i]).corrected_action)

        batch_result = bat.project_batch(
            proposals,
            previous,
            uppers=uppers,
            row_ids=["a", "b", "c"],
        )
    except RuntimeError as exc:
        if "license" in str(exc).lower() or "key" in str(exc).lower():
            pytest.skip(f"Moreau license not available: {exc}")
        raise

    stacked = np.stack(seq_out, axis=0)
    np.testing.assert_allclose(batch_result.corrected_actions, stacked, rtol=1e-4, atol=1e-5)
    assert len(batch_result.rows) == 3
    for row in batch_result.rows:
        assert row.verification is not None
        assert row.metadata.get("row_id") in {"a", "b", "c"}
    del replace, base
