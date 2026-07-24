"""R6 decision-report scaffold: whether intervention-aware training is scientifically justified.

States BLOCKED and lists required evidence. Does **not** contain training results
or claim that safer policies were learned. This is a scientific decision document
(evidence matrix), not an experiment results report.

R15: authorization is wired through ``evaluate_flagship_promotion_gate`` (lazy via
the comparison harness). Fail-closed while the flagship gate fails. Numerical
assurance evidence is not system-level safety proof.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from conicshield.experimental.corpus.paths import CORPUS_VERSION, RESEARCH_ROOT
from conicshield.experimental.training.comparison_harness import (
    COMPARISON_ARMS,
    CRITICAL_PROMOTION_RULE,
    HELD_OUT_EVAL_FIELDS,
    PUBLIC_CLAIM_BINDING,
    build_controlled_comparison_harness,
)
from conicshield.experimental.training.intervention_aware_stub import InterventionAwareTrainingPlan

R6_DECISION_SCHEMA_ID = "research.r6_decision_report_scaffold.v1"
R6_DECISION_DOC_VERSION = "r6-decision-v0.3.0"


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
    blocked_until: tuple[str, ...] = (
        "flagship_promotion_gate",
        "R2_promotion_gate",
        "R4_promotion_gate",
    )
    required_evidence: list[RequiredEvidenceItem] = field(default_factory=list)
    non_claims: list[str] = field(default_factory=list)
    decision_logic: list[str] = field(default_factory=list)
    training_plan: dict[str, Any] = field(default_factory=dict)
    comparison_harness: dict[str, Any] = field(default_factory=dict)
    flagship_gate: dict[str, Any] = field(default_factory=dict)
    results: None = None  # explicit: no results in scaffold

    def as_dict(self) -> dict[str, Any]:
        missing_blocking = [
            e.evidence_id
            for e in self.required_evidence
            if e.blocking_for_execution and e.status in {"missing", "blocked_dependency", "partial"}
        ]
        authorized = bool(self.flagship_gate.get("r6_execution_authorized"))
        return {
            "schema_id": self.schema_id,
            "document_version": self.document_version,
            "decision_status": self.decision_status if not authorized else "STRUCTURE_READY_NO_RESULTS",
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
            "comparison_harness": dict(self.comparison_harness),
            "flagship_gate": dict(self.flagship_gate),
            "execution_authorized": authorized,
            "results": self.results,
            "critical_rule": CRITICAL_PROMOTION_RULE,
            "public_claim_binding": PUBLIC_CLAIM_BINDING,
            "note": (
                "Scientific decision document / evidence matrix only. No training loops "
                "executed. No claim that safer policies were learned. Fill results only "
                "after the R14 flagship promotion gate passes and independent safety "
                "metrics improve under held-out conditions. Checklist completeness here "
                "does not unblock R6. Numerical evidence ≠ system safety proof."
            ),
        }


def build_r6_decision_report_scaffold() -> R6DecisionReportScaffold:
    plan = InterventionAwareTrainingPlan()
    harness = build_controlled_comparison_harness()
    gate = dict(harness.flagship_gate)
    gate_passed = bool(gate.get("r6_execution_authorized"))
    flagship_status = "present" if gate_passed else "blocked_dependency"

    evidence = [
        RequiredEvidenceItem(
            "flagship_promotion_gate",
            "R14 flagship promotion gate (`evaluate_flagship_promotion_gate`) must pass "
            "before any R6 training execution. Includes level predicates, sidecar protocol "
            "≥ v2, native Moreau multi-host participation, real linked gradients, verified "
            "CBF, corrupted/incomplete rejection, and docs limitations. Passing is numerical "
            "assurance readiness — not system-level safety proof.",
            status=flagship_status,
            scientific_role="required",
            depends_on_gates=("R14", "flagship_promotion_gate"),
            evidence_pointers=(
                "conicshield.experimental.assurance.proof_carrying.evaluate_flagship_promotion_gate",
                "research/solver-assurance-and-gradients/PROMOTION_GATES.md#r4",
                "research/solver-assurance-and-gradients/ASSURANCE_SEMANTICS.md",
            ),
            acceptance_criterion=(
                "evaluate_flagship_promotion_gate(...).passed is True with retained blockers "
                "empty; production_claim remains False. Numerical evidence is not a system "
                "safety proof."
            ),
        ),
        RequiredEvidenceItem(
            "r2_native_or_validated_gradients",
            "R2 gate: corpus-validated gradients with active-set coverage and exact-vs-FD "
            "agreement for the claimed differentiation path (native backends implemented; "
            "live Moreau required for AVAILABLE). "
            "Research KKT/smoothed adapters are distinct evidence kinds and do not satisfy "
            "the native exact-vs-FD promotion gate.",
            status="partial",
            scientific_role="required",
            depends_on_gates=("R2", "R14"),
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
            "(research adapter exists; production wiring absent). Supporting prerequisite "
            "for flagship multi-host predicates.",
            status="partial",
            scientific_role="required",
            depends_on_gates=("R4", "R14"),
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
            "(not intervention-rate alone). Must include failure cases. Required fields: "
            + ", ".join(HELD_OUT_EVAL_FIELDS)
            + ".",
            status="missing",
            scientific_role="required",
            depends_on_gates=("flagship_promotion_gate", "R6"),
            evidence_pointers=(
                "research/solver-assurance-and-gradients/CHARTER.md",
                "conicshield.experimental.training.comparison_harness",
                "conicshield.experimental.domains.cbf_corpus",
            ),
            acceptance_criterion=(
                "Pre-registered held-out safety metrics improve under shift vs baselines; "
                "intervention-frequency reduction alone is insufficient for promotion."
            ),
        ),
        RequiredEvidenceItem(
            "robustness_to_solver_and_smoothing",
            "Results stable across solver backends and smoothing choices; failure cases included.",
            status="missing",
            scientific_role="required",
            depends_on_gates=("R6",),
            evidence_pointers=("conicshield.experimental.training.comparison_harness",),
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
            "Documented controlled comparisons for arms: "
            + ", ".join(COMPARISON_ARMS)
            + " with pre-registered held-out metrics. Harness structure exists; execution "
            "blocked until flagship gate passes.",
            status="partial",
            scientific_role="required",
            depends_on_gates=("flagship_promotion_gate", "R6"),
            evidence_pointers=(
                "conicshield.experimental.training.comparison_harness",
                "conicshield.experimental.training.intervention_aware_stub",
            ),
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
        decision_status="BLOCKED" if not gate_passed else "STRUCTURE_READY_NO_RESULTS",
        training_plan=plan.as_dict(),
        comparison_harness=harness.as_dict(),
        flagship_gate=gate,
        required_evidence=evidence,
        decision_logic=[
            "IF evaluate_flagship_promotion_gate does not pass THEN decision_status remains "
            "BLOCKED and no training execution is authorized (fail-closed).",
            "IF R2 and R4 promotion gates are not passed THEN treat as supporting blockers "
            "under the flagship gate; do not authorize R6 execution.",
            "IF independent held-out safety metrics do not improve under shift THEN do not "
            "claim scientifically justified intervention-aware training.",
            "IF only intervention frequency decreases without safety-metric gains THEN treat "
            "as negative / inconclusive result — never as promotion evidence.",
            "IF native exact/smoothed gradients are unavailable on the training host "
            "THEN do not claim native differentiable training success "
            "(research adapters are distinct evidence).",
            "Flagship / L0–L4 numerical assurance is not system-level safety proof and does "
            "not alone justify a safer-policy claim.",
            "Stage-4 CBF experimental RH availability does not satisfy flagship / R2 / R4 "
            "and does not unblock R6.",
        ],
        non_claims=[
            "No claim of learning safer policies.",
            "No training results are present in this scaffold.",
            "Research KKT / smoothed adapters are not native Moreau gradients.",
            "Intervention-frequency reduction alone is insufficient evidence of safety.",
            "Checklist completeness here does not unblock R6 training execution.",
            "Numerical evidence (ProofCarryingProjection / L0–L4) is not system-level safety proof.",
            "Stage-4 CBF checklist green / experimental RH does not imply flagship or R2/R4 gates passed.",
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
    gate = report.flagship_gate
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
        "## Flagship gate dependency (R14 → R15)",
        "",
        f"- `r6_execution_authorized`: `{bool(gate.get('r6_execution_authorized'))}`",
        f"- `flagship_gate.passed`: `{bool(gate.get('passed'))}`",
        f"- blockers: `{list(gate.get('blockers') or [])}`",
        "",
        CRITICAL_PROMOTION_RULE,
        "",
        PUBLIC_CLAIM_BINDING,
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
    lines.extend(
        [
            "",
            "## Controlled comparison arms",
            "",
        ]
    )
    for arm in COMPARISON_ARMS:
        lines.append(f"- `{arm}`")
    lines.extend(
        [
            "",
            "## Held-out evaluation matrix fields",
            "",
        ]
    )
    for fid in HELD_OUT_EVAL_FIELDS:
        lines.append(f"- `{fid}`")
    lines.extend(["", "## Required evidence matrix", ""])
    lines.append("| ID | Status | Role | Blocking | Acceptance criterion |")
    lines.append("| -- | ------ | ---- | -------- | -------------------- |")
    for e in report.required_evidence:
        acc = e.acceptance_criterion.replace("|", "\\|")
        lines.append(
            f"| `{e.evidence_id}` | {e.status} | {e.scientific_role} | {e.blocking_for_execution} | {acc} |"
        )
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
            "training execution. Execution remains blocked until "
            "`evaluate_flagship_promotion_gate` passes and the acceptance criteria above "
            "are met with retained negatives. Intervention-frequency reduction alone is "
            "not promotion evidence. Numerical assurance ≠ system safety proof.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    path = write_r6_decision_scaffold()
    report = build_r6_decision_report_scaffold()
    print(
        f"wrote {path} status={report.decision_status} version={R6_DECISION_DOC_VERSION} "
        f"flagship_passed={bool(report.flagship_gate.get('passed'))}"
    )


if __name__ == "__main__":
    main()
