"""Advanced solver assurance plane (Track 2 R1)."""

from __future__ import annotations

from conicshield.experimental.solver_assurance.disagreement import (
    DisagreementTaxonomy,
    SolverDisagreement,
    compare_projections,
    summarize_by_family,
    summarize_disagreements,
)
from conicshield.experimental.solver_assurance.disagreement_corpus import (
    build_disagreement_corpus,
)
from conicshield.experimental.solver_assurance.hypotheses_eval import (
    HypothesisEvaluation,
    HypothesisEvaluationReport,
    HypothesisVerdict,
    build_evaluation_report,
)
from conicshield.experimental.solver_assurance.promotion_protocol import (
    CandidateStackPromotionProtocol,
    run_candidate_stack_promotion,
)
from conicshield.experimental.solver_assurance.sampling import SamplingPolicyId, all_sampling_policies
from conicshield.experimental.solver_assurance.sampling_study import (
    SamplingStudyReport,
    run_sampling_study,
)
from conicshield.experimental.solver_assurance.shadow_harness import run_shadow_harness

__all__ = [
    "CandidateStackPromotionProtocol",
    "DisagreementTaxonomy",
    "HypothesisEvaluation",
    "HypothesisEvaluationReport",
    "HypothesisVerdict",
    "SamplingPolicyId",
    "SamplingStudyReport",
    "SolverDisagreement",
    "all_sampling_policies",
    "build_disagreement_corpus",
    "build_evaluation_report",
    "compare_projections",
    "run_candidate_stack_promotion",
    "run_sampling_study",
    "run_shadow_harness",
    "summarize_by_family",
    "summarize_disagreements",
]
