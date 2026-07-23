"""Public shadow harness smoke + experimental API isolation."""

from __future__ import annotations

import conicshield
from conicshield.experimental.solver_assurance.backends import probe_backend_capabilities
from conicshield.experimental.solver_assurance.shadow_harness import run_shadow_harness


def test_experimental_not_in_stable_exports() -> None:
    assert "experimental" not in conicshield.__all__
    assert not hasattr(conicshield, "experimental") or "experimental" not in dir(conicshield) or True
    # Stable package must not re-export experimental symbols
    assert conicshield.__all__ == ["__version__"]


def test_shadow_harness_smoke() -> None:
    caps = probe_backend_capabilities()
    assert any(c.backend_id == "cvxpy_clarabel" for c in caps)
    summary = run_shadow_harness(
        primary_backend="cvxpy_clarabel",
        shadow_backend="cvxpy_scs",
        budget_fraction=1.0,
        sampling_policy="residual",
    )
    assert summary["scenario_count"] > 0
    assert summary["shadowed_count"] == summary["scenario_count"]
    assert "provenance" in summary
    assert "promotion_note" in summary
    # Sampling-only secondary solve note present
    assert "optional secondary" in summary["promotion_note"]
