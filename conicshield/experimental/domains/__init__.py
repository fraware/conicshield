"""R5 domain — uncertainty-aware CBF 2D motion (one domain only)."""

from __future__ import annotations

from conicshield.experimental.domains.cbf_2d import (
    CBF2DDomain,
    CBF2DDomainScaffold,
    apply_cbf_filter,
    apply_cbf_filter_batched,
    apply_cbf_filter_soc_robust,
    compute_cbf_metrics,
    demo_stage1_scenario,
    demo_stage2_batch,
    demo_stage3_soc_robust,
    nominal_cbf_qp_placeholder,
    stage4_gate_status,
)
from conicshield.experimental.domains.cbf_corpus import (
    CBF_CORPUS_VERSION,
    generate_cbf_corpus,
    load_cbf_cases,
)
from conicshield.experimental.domains.cbf_rh import (
    RH_EXPERIMENT_VERSION,
    demo_rh_scenario,
    describe_rh_capability,
    run_receding_horizon_filter,
)
from conicshield.experimental.domains.infeasibility_taxonomy import (
    audit_infeasibility,
    classify_filter_result,
)
from conicshield.experimental.domains.stage4_gate import evaluate_stage4_gate

__all__ = [
    "CBF2DDomain",
    "CBF2DDomainScaffold",
    "CBF_CORPUS_VERSION",
    "RH_EXPERIMENT_VERSION",
    "apply_cbf_filter",
    "apply_cbf_filter_batched",
    "apply_cbf_filter_soc_robust",
    "audit_infeasibility",
    "classify_filter_result",
    "compute_cbf_metrics",
    "demo_rh_scenario",
    "demo_stage1_scenario",
    "demo_stage2_batch",
    "demo_stage3_soc_robust",
    "describe_rh_capability",
    "evaluate_stage4_gate",
    "generate_cbf_corpus",
    "load_cbf_cases",
    "nominal_cbf_qp_placeholder",
    "run_receding_horizon_filter",
    "stage4_gate_status",
]
