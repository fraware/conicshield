"""R6 decision-report scaffold: whether intervention-aware training is scientifically justified.

States BLOCKED and lists required evidence. Does **not** contain training results
or claim that safer policies were learned. This is a scientific decision document
(evidence matrix), not an experiment results report.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from conicshield.experimental.corpus.paths import CORPUS_VERSION, RESEARCH_ROOT
from conicshield.experimental.training.intervention_aware_stub import InterventionAwareTrainingPlan

R6_DECISION_SCHEMA_ID = "research.r6_decision_report_scaffold.v1"
R6_DECISION_DOC_VERSION = "r6-decision-v0.2.0"


@dataclass(slots=True)
class RequiredEvidenceItem:
    evidence_id: str
    description: str
    status: str = "missing"  # missing | partial | present | blocked_dependency
    scientific_role: str = "required"  # required | supporting | negative_retention
    depends_on_gates: tuple[str, ...] = ()
    evidence_pointers: tuple[str, ...] = ()
    acceptance_criterion: str = ""
    blocking_for_execution: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "description": self.description,
            "status": self.status,
            "scientific_role": self.scientific_role,
            "depends_on_gates": list(self.depends_on_gates),
            "evidence_pointers": list(self.evidence_pointers),
            "acceptance_criterion": self.acceptance_criterion,
            "blocking_for_execution": self.blocking_for_execution,
        }


@dataclass(slots=True)
class R6DecisionReportScaffold:
    schema_id: str = R6_DECISION_SCHEMA_ID
    document_version: str = R6_DECISION_DOC_VERSION
    decision_status: str = "BLOCKED"
    document_type: str = "scientific_decision_evidence_matrix"
    question: str = "Is intervention-aware training scientifically justified for ConicShield?"
    charter_question_id: str = "Q8"
    corpus_version_context: str = CORPUS_VERSION
    blocked_until: tuple[str, ...] = ("R2_promotion_gate", "R4_promotion_gate")
    required_evidence: list[RequiredEvidenceItem] = field(default_factory=list)
    non_claims: list[str] = field(default_factory=list)
    decision_logic: list[str] = field(default_factory=list)
    training_plan: dict[str, Any] = field(default_factory=dict)
    results: None = None  # explicit: no results in scaffold

    def as_dict(self) -> dict[str, Any]:
        missing_blocking = [
            e.evidence_id
            for e in self.required_evidence
            if e.blocking_for_execution and e.status in {"missing", "blocked_dependency", "partial"}
        ]
        return {
            "schema_id": self.schema_id,
            "document_version": self.document_version,
            "decision_status": self.decision_status,
            "document_type": self.document_type,
            "question": self.question,
            "charter_question_id": self.charter_question_id,
            "corpus_version_context": self.corpus_version_context,
            "blocked_until": list(self.blocked_until),
            "required_evidence": [e.as_dict() for e in self.required_evidence],
            "blocking_evidence_incomplete": missing_blocking,
            "non_claims": list(self.non_claims),
            "decision_logic": list(self.decision_logic),
            "training_plan": dict(self.training_plan),
            "results": self.results,
            "note": (
                "Scientific decision document / evidence matrix only. No training loops "
                "executed. No claim that safer policies were learned. Fill results only "
                "after R2+R4 gates pass and independent safety metrics improve under "
                "distribution shift. Checklist completeness here does not unblock R6."
            ),
        }


def build_r6_decision_report_scaffold() -> R6DecisionReportScaffold:
    plan = InterventionAwareTrainingPlan()
    evidence = [
        RequiredEvidenceItem(
            "r2_native_or_validated_gradients",
            "R2 gate: corpus-validated gradients with active-set coverage and exact-vs-FD "
            "agreement for the claimed differentiation path (native backends implemented; "
            "live Moreau required for AVAILABLE). "
            "Research KKT/smoothed adapters are distinct evidence kinds and do not satisfy "
            "the native exact-vs-FD promotion gate.",
            status="partial",
            scientific_role="required",
            depends_on_gates=("R2",),
            evidence_pointers=(
                "research/solver-assurance-and-gradients/PROMOTION_GATES.md#r2",
                "conicshield.experimental.gradients.agreement_study",
                "conicshield.experimental.gradients.exact_backend",
                "conicshield.experimental.gradients.smoothed_backend",
            ),
            acceptance_criterion=(
                "Claimed differentiation path has documented exact-vs-FD agreement on "
                "active-set coverage corpus; research adapters must not be silently "
                "aliased as native Moreau backends."
            ),
        ),
        RequiredEvidenceItem(
            "r4_assurance_reproduction",
            "R4 gate: multi-host clean-env soak on >=2 real hosts, schema/replay/corruption "
            "tests, and governed hash policy integrated with production release tooling "
            "(research adapter exists; production wiring absent).",
            status="partial",
            scientific_role="required",
            depends_on_gates=("R4",),
            evidence_pointers=(
                "research/solver-assurance-and-gradients/PROMOTION_GATES.md#r4",
                "conicshield.experimental.assurance.platform_soak",
                "conicshield.experimental.assurance.multi_host_soak_sim",
                "conicshield.experimental.assurance.governed_hash_policy",
            ),
            acceptance_criterion=(
                ">=2 distinct real hosts reproduce assurance artifacts; synthetic "
                "second-host fixtures do not count; production governed-hash wiring present."
            ),
        ),
        RequiredEvidenceItem(
            "track1_s4_hetero_batch_attestation",
            "Track 1 S4 heterogeneous batch interface attested; frontiers no longer "
            "watermarked sequential_adapter for publication-grade claims.",
            status="missing",
            scientific_role="required",
            depends_on_gates=("Track1_S4", "R3"),
            evidence_pointers=(
                "conicshield.experimental.adapters.track1_probe.probe_track1_research_readiness",
                "conicshield.experimental.frontiers.sweeps.probe_track1_hetero_batch_attestation",
            ),
            acceptance_criterion=(
                "probe_track1_research_readiness().reduce_watermarks is True with S4 "
                "research_attested=True on the reporting host."
            ),
        ),
        RequiredEvidenceItem(
            "independent_safety_metrics_under_shift",
            "Held-out safety margin / robustness improvements under distribution shift "
            "(not intervention-rate alone). Must include failure cases.",
            status="missing",
            scientific_role="required",
            depends_on_gates=("R2", "R4", "R6"),
            evidence_pointers=(
                "research/solver-assurance-and-gradients/CHARTER.md",
                "conicshield.experimental.domains.cbf_corpus",
            ),
            acceptance_criterion=(
                "Pre-registered held-out safety metrics improve under shift vs baselines; "
                "intervention-rate reduction alone is insufficient."
            ),
        ),
        RequiredEvidenceItem(
            "robustness_to_solver_and_smoothing",
            "Results stable across solver backends and smoothing choices; failure cases included.",
            status="missing",
            scientific_role="required",
            depends_on_gates=("R6",),
            evidence_pointers=(),
            acceptance_criterion=(
                "Sign of safety conclusions unchanged across declared solver/smoothing "
                "sensitivity grid; negatives retained."
            ),
        ),
        RequiredEvidenceItem(
            "no_verifier_or_gradient_exploitation",
            "Training does not exploit known verifier or gradient weaknesses; adversarial "
            "checks against documented failure modes from R1/R2 corpora.",
            status="missing",
            scientific_role="required",
            depends_on_gates=("R6",),
            evidence_pointers=(
                "conicshield.experimental.solver_assurance.disagreement_corpus",
                "conicshield.experimental.gradients.agreement_study",
            ),
            acceptance_criterion=(
                "Adversarial / known-failure probes do not show metric gaming of verifier or gradient weaknesses."
            ),
        ),
        RequiredEvidenceItem(
            "comparison_battery",
            "Documented comparisons vs unshielded / inference-only shield / exact / smoothed / "
            "penalty-only / dual-pressure baselines with pre-registered metrics.",
            status="missing",
            scientific_role="required",
            depends_on_gates=("R6",),
            evidence_pointers=("conicshield.experimental.training.intervention_aware_stub",),
            acceptance_criterion=(
                "All listed baselines present with identical metrics and seed control; "
                "exact/smoothed baseline entries require live native backend availability "
                "and must not be silently substituted by research adapters."
            ),
        ),
        RequiredEvidenceItem(
            "decision_report_with_negative_results",
            "Written decision report answering CHARTER Q8 with negative results retained; "
            "no claim of learning safer policies without independent safety-metric gains.",
            status="partial",
            scientific_role="required",
            depends_on_gates=("R6",),
            evidence_pointers=(
                "research/solver-assurance-and-gradients/CHARTER.md",
                "conicshield.experimental.training.r6_decision_scaffold",
                "research/solver-assurance-and-gradients/reports/R6_DECISION_REPORT_SCAFFOLD.md",
            ),
            acceptance_criterion=(
                "Final report includes negatives and an explicit go/no-go under the "
                "acceptance criteria above; this scaffold alone is insufficient."
            ),
            blocking_for_execution=True,
        ),
        RequiredEvidenceItem(
            "negative_retention_protocol",
            "Protocol for retaining failed seeds, infeasible episodes, and non-improving "
            "shift splits — required before any positive R6 claim.",
            status="partial",
            scientific_role="negative_retention",
            depends_on_gates=("R6",),
            evidence_pointers=("conicshield.experimental.training.r6_decision_scaffold",),
            acceptance_criterion=(
                "Artifact store includes failed runs with hashes; omission of negatives is a gate failure."
            ),
            blocking_for_execution=True,
        ),
    ]
    return R6DecisionReportScaffold(
        training_plan=plan.as_dict(),
        required_evidence=evidence,
        decision_logic=[
            "IF R2 and R4 promotion gates are not passed THEN decision_status remains BLOCKED "
            "and no training execution is authorized.",
            "IF independent held-out safety metrics do not improve under shift THEN do not "
            "claim scientifically justified intervention-aware training.",
            "IF only intervention rate decreases without safety-metric gains THEN treat as "
            "negative / inconclusive result.",
            "IF native exact/smoothed gradients are unavailable on the training host "
            "THEN do not claim native differentiable training success "
            "(research adapters are distinct evidence).",
            "Stage-4 CBF experimental RH availability does not satisfy R2 or R4 and does not unblock R6.",
        ],
        non_claims=[
            "No claim of learning safer policies.",
            "No training results are present in this scaffold.",
            "Research KKT / smoothed adapters are not native Moreau gradients.",
            "Intervention-rate reduction alone is insufficient evidence of safety.",
            "Checklist completeness here does not unblock R6 training execution.",
            "Stage-4 CBF checklist green / experimental RH does not imply R2/R4 promotion gates passed.",
            "Track 1 S4/S5 scaffolding without vendor attestation does not clear publication-grade frontiers.",
        ],
    )


def write_r6_decision_scaffold(*, path: Path | None = None) -> Path:
    report = build_r6_decision_report_scaffold()
    out = path or (RESEARCH_ROOT / "reports" / "R6_DECISION_REPORT_SCAFFOLD.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md = out.with_suffix(".md")
    md.write_text(_render_markdown(report), encoding="utf-8")
    return out


def _render_markdown(report: R6DecisionReportScaffold) -> str:
    lines = [
        "# R6 decision report scaffold",
        "",
        f"**Status: {report.decision_status}**",
        "",
        f"Document type: `{report.document_type}`  ",
        f"Version: `{report.document_version}`  ",
        f"CHARTER question: `{report.charter_question_id}`",
        "",
        report.question,
        "",
        "## Blocked until",
        "",
    ]
    for g in report.blocked_until:
        lines.append(f"- {g}")
    lines.extend(
        [
            "",
            "## Decision logic (scientific)",
            "",
        ]
    )
    for rule in report.decision_logic:
        lines.append(f"- {rule}")
    lines.extend(["", "## Required evidence matrix", ""])
    lines.append("| ID | Status | Role | Blocking | Acceptance criterion |")
    lines.append("| -- | ------ | ---- | -------- | -------------------- |")
    for e in report.required_evidence:
        acc = e.acceptance_criterion.replace("|", "\\|")
        lines.append(f"| `{e.evidence_id}` | {e.status} | {e.scientific_role} | {e.blocking_for_execution} | {acc} |")
    lines.extend(["", "### Evidence details", ""])
    for e in report.required_evidence:
        ptr = f" pointers={list(e.evidence_pointers)}" if e.evidence_pointers else ""
        lines.append(f"- `{e.evidence_id}` [{e.status}]: {e.description}{ptr}")
    lines.extend(["", "## Non-claims", ""])
    for n in report.non_claims:
        lines.append(f"- {n}")
    lines.extend(
        [
            "",
            "## Results",
            "",
            "_None. This scaffold intentionally contains no training results._",
            "",
            "## Explicit non-authorization",
            "",
            "Completing rows in this matrix as documentation does **not** authorize R6 "
            "training execution. Execution remains blocked until R2 and R4 promotion gates "
            "pass and the acceptance criteria above are met with retained negatives.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    path = write_r6_decision_scaffold()
    print(f"wrote {path} status=BLOCKED version={R6_DECISION_DOC_VERSION}")


if __name__ == "__main__":
    main()
