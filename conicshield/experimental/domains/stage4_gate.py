"""Machine-checkable CBF stage-4 gate evaluator (R5).

Evaluates stage-4 checklist criteria against stage 1–3 experimental evidence.
When all required criteria pass, reports checklist green and (when the
experimental short-horizon RH module is present) ``experimental_rh_available``.
Does **not** claim full RH-MPC, multi-robot, or production qualification.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

import numpy as np

from conicshield.experimental.domains.cbf_2d import (
    STAGE4_VALIDATION_CHECKLIST,
    AgentState2D,
    CBFStage,
    CircularObstacle,
    apply_cbf_filter,
    compute_cbf_metrics,
    demo_stage1_scenario,
    demo_stage2_batch,
    demo_stage3_soc_robust,
    stage3_disagreement_under_perturbation,
)
from conicshield.experimental.domains.cbf_corpus import (
    CBF_CORPUS_VERSION,
    CBF_MANIFEST_PATH,
    MIN_HELD_OUT_NOMINAL,
    evaluate_held_out_nominal,
    held_out_nominal_cases,
    probe_cbf_filter_bank,
)
from conicshield.experimental.domains.cbf_rh import (
    RH_IMPLEMENTED,
    describe_rh_capability,
)
from conicshield.experimental.domains.infeasibility_taxonomy import (
    audit_infeasibility,
    write_infeasibility_audit,
)

STAGE4_GATE_SCHEMA_ID = "research.cbf_stage4_gate_evaluation.v0"
INFEASIBILITY_RATE_THRESHOLD = 0.05
UNEXPLAINED_INFEASIBILITY_THRESHOLD = 0.05


class CriterionStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    PENDING = "pending"


@dataclass(slots=True)
class CriterionResult:
    criterion_id: str
    status: CriterionStatus
    required: bool = True
    evidence_pointers: list[str] = field(default_factory=list)
    detail: str = ""
    numeric: dict[str, float] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "criterion_id": self.criterion_id,
            "status": str(self.status),
            "required": self.required,
            "evidence_pointers": list(self.evidence_pointers),
            "detail": self.detail,
            "numeric": dict(self.numeric),
        }


@dataclass(slots=True)
class Stage4GateEvaluation:
    schema_id: str = STAGE4_GATE_SCHEMA_ID
    stage: str = CBFStage.STAGE4_RECEDING.value
    criteria: list[CriterionResult] = field(default_factory=list)
    stage4_status: str = "blocked"
    unblock_allowed: bool = False
    rh_mpc_implemented: bool = False
    experimental_rh_implemented: bool = False
    experimental_rh: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        required = [c for c in self.criteria if c.required]
        all_pass = bool(required) and all(c.status == CriterionStatus.PASS for c in required)
        return {
            "schema_id": self.schema_id,
            "stage": self.stage,
            "criteria": [c.as_dict() for c in self.criteria],
            "required_count": len(required),
            "passed_count": sum(1 for c in required if c.status == CriterionStatus.PASS),
            "failed_count": sum(1 for c in required if c.status == CriterionStatus.FAIL),
            "pending_count": sum(1 for c in required if c.status == CriterionStatus.PENDING),
            "all_required_passed": all_pass,
            "stage4_status": self.stage4_status,
            "unblock_allowed": self.unblock_allowed,
            "rh_mpc_implemented": self.rh_mpc_implemented,
            "experimental_rh_implemented": self.experimental_rh_implemented,
            "experimental_rh": dict(self.experimental_rh),
            "checklist_ids": list(STAGE4_VALIDATION_CHECKLIST),
            "notes": list(self.notes),
        }


def evaluate_stage4_gate(
    *,
    evidence_dir: Path | None = None,
    force_pending: set[str] | None = None,
) -> Stage4GateEvaluation:
    """Evaluate checklist against live experimental evidence; keep stage 4 blocked if incomplete."""

    pending_force = force_pending or set()
    criteria: list[CriterionResult] = []
    notes: list[str] = []

    # --- stage1 ---
    cid = "stage1_nominal_cbf_qp_feasible_on_demo_corpus"
    if cid in pending_force:
        criteria.append(CriterionResult(cid, CriterionStatus.PENDING, detail="forced pending", evidence_pointers=[]))
    else:
        s1 = demo_stage1_scenario()
        ok = np.all(np.isfinite(s1.u_safe)) and s1.solver_status in {"optimal", "optimal_inaccurate"}
        criteria.append(
            CriterionResult(
                cid,
                CriterionStatus.PASS if ok else CriterionStatus.FAIL,
                evidence_pointers=["conicshield.experimental.domains.cbf_2d.demo_stage1_scenario"],
                detail=f"solver_status={s1.solver_status} margin={s1.safety_margin}",
                numeric={"safety_margin": float(s1.safety_margin), "intervention_norm": float(s1.intervention_norm)},
            )
        )

    # --- stage2 ---
    cid = "stage2_batched_agents_metrics_recorded"
    if cid in pending_force:
        criteria.append(CriterionResult(cid, CriterionStatus.PENDING, detail="forced pending"))
    else:
        batch = demo_stage2_batch()
        metrics = compute_cbf_metrics(batch)
        ok = len(batch) >= 2 and metrics.intervention_frequency >= 0.0
        criteria.append(
            CriterionResult(
                cid,
                CriterionStatus.PASS if ok else CriterionStatus.FAIL,
                evidence_pointers=[
                    "conicshield.experimental.domains.cbf_2d.demo_stage2_batch",
                    "conicshield.experimental.domains.cbf_2d.compute_cbf_metrics",
                ],
                detail=f"n_agents={len(batch)} intervention_frequency={metrics.intervention_frequency}",
                numeric={
                    "n_agents": float(len(batch)),
                    "intervention_frequency": float(metrics.intervention_frequency),
                },
            )
        )

    # --- stage3 feasible ---
    cid = "stage3_soc_robust_margin_feasible_under_declared_noise_model"
    if cid in pending_force:
        criteria.append(CriterionResult(cid, CriterionStatus.PENDING, detail="forced pending"))
    else:
        s3 = demo_stage3_soc_robust()
        ok = np.all(np.isfinite(s3.u_safe)) and "uncertainty_model_id" in s3.metadata
        criteria.append(
            CriterionResult(
                cid,
                CriterionStatus.PASS if ok else CriterionStatus.FAIL,
                evidence_pointers=[
                    "conicshield.experimental.domains.cbf_2d.demo_stage3_soc_robust",
                    "research/solver-assurance-and-gradients/notes/CBF_STAGE3_UNCERTAINTY_MODEL.md",
                ],
                detail=f"status={s3.solver_status} model={s3.metadata.get('uncertainty_model_id')}",
                numeric={"safety_margin": float(s3.safety_margin)},
            )
        )

    # --- stage3 disagreement quantified ---
    cid = "stage3_robust_margin_disagreement_under_perturbation_quantified"
    if cid in pending_force:
        criteria.append(CriterionResult(cid, CriterionStatus.PENDING, detail="forced pending"))
    else:
        agent = AgentState2D(np.array([0.0, 0.0]), np.array([1.0, 0.0]), "a0")
        obs = CircularObstacle(np.array([1.0, 0.0]), 0.5, "o0")
        disagree = stage3_disagreement_under_perturbation(agent, obs, epsilon=0.05)
        l2 = float(disagree.get("nominal_vs_robust_u_l2") or float("nan"))
        ok = np.isfinite(l2)
        criteria.append(
            CriterionResult(
                cid,
                CriterionStatus.PASS if ok else CriterionStatus.FAIL,
                evidence_pointers=["conicshield.experimental.domains.cbf_2d.stage3_disagreement_under_perturbation"],
                detail=f"nominal_vs_robust_u_l2={l2}",
                numeric={"nominal_vs_robust_u_l2": l2},
            )
        )

    # --- held-out nonnegative margins ---
    cid = "single_step_safety_margin_nonnegative_on_held_out_nominal_cases"
    if cid in pending_force:
        criteria.append(CriterionResult(cid, CriterionStatus.PENDING, detail="forced pending"))
    else:
        corpus_present = CBF_MANIFEST_PATH.is_file()
        if not corpus_present:
            status = CriterionStatus.PENDING
            detail = (
                f"CBF held-out corpus missing at {CBF_MANIFEST_PATH}; "
                f"run python -m conicshield.experimental.domains.cbf_corpus"
            )
            notes.append("held-out criterion pending: committed cbf corpus not found")
            criteria.append(
                CriterionResult(
                    cid,
                    status,
                    evidence_pointers=[
                        "conicshield.experimental.domains.cbf_corpus",
                        str(CBF_MANIFEST_PATH),
                    ],
                    detail=detail,
                    numeric={"held_out_n": 0.0},
                )
            )
        else:
            held_eval = evaluate_held_out_nominal()
            n_held = int(held_eval["n_held_out"])
            min_m = float(held_eval["min_safety_margin"])
            infeas = int(held_eval["infeasible_count"])
            if n_held < MIN_HELD_OUT_NOMINAL:
                status = CriterionStatus.PENDING
                detail = f"held_out_n={n_held} < {MIN_HELD_OUT_NOMINAL}; corpus={CBF_CORPUS_VERSION} incomplete"
                notes.append("held-out criterion pending: corpus below minimum nominal count")
            elif min_m >= -1e-4 and infeas == 0:
                status = CriterionStatus.PASS
                detail = f"held_out_n={n_held} min_margin={min_m} corpus={CBF_CORPUS_VERSION}"
            else:
                status = CriterionStatus.FAIL
                detail = f"held_out_n={n_held} min_margin={min_m} infeas={infeas} corpus={CBF_CORPUS_VERSION}"
            criteria.append(
                CriterionResult(
                    cid,
                    status,
                    evidence_pointers=[
                        "conicshield.experimental.domains.cbf_corpus.evaluate_held_out_nominal",
                        f"research/solver-assurance-and-gradients/corpus/cbf/{CBF_CORPUS_VERSION}",
                        "conicshield.experimental.domains.cbf_2d.apply_cbf_filter",
                    ],
                    detail=detail,
                    numeric={
                        "min_safety_margin": min_m,
                        "held_out_n": float(n_held),
                        "infeasible": float(infeas),
                    },
                )
            )

    # --- unexplained infeasibility ---
    cid = "no_unexplained_infeasibility_rate_above_threshold"
    if cid in pending_force:
        criteria.append(CriterionResult(cid, CriterionStatus.PENDING, detail="forced pending"))
    else:
        if not CBF_MANIFEST_PATH.is_file():
            status = CriterionStatus.PENDING
            detail = "CBF corpus missing; cannot run taxonomy-backed infeasibility audit"
            notes.append("unexplained-infeasibility pending: need committed cbf corpus")
            criteria.append(
                CriterionResult(
                    cid,
                    status,
                    evidence_pointers=[
                        "conicshield.experimental.domains.infeasibility_taxonomy",
                    ],
                    detail=detail,
                    numeric={"unexplained_rate": float("nan")},
                )
            )
        else:
            probes = probe_cbf_filter_bank()
            audit = audit_infeasibility(probes)
            if evidence_dir is not None:
                write_infeasibility_audit(evidence_dir / "cbf_infeasibility_audit.json", audit)
            held_cases = held_out_nominal_cases()
            held_bad = 0
            for case in held_cases:
                agent, obs = case.to_agent_obstacle()
                r = apply_cbf_filter(agent, obs, alpha=case.alpha, u_max=case.u_max)
                if r.solver_status not in {"optimal", "optimal_inaccurate"} or not np.all(np.isfinite(r.u_safe)):
                    held_bad += 1
            held_rate = float(held_bad / max(len(held_cases), 1))
            unexplained = float(audit.unexplained_rate)
            if held_rate > INFEASIBILITY_RATE_THRESHOLD:
                status = CriterionStatus.FAIL
                detail = (
                    f"held_out_infeasibility_rate={held_rate} > {INFEASIBILITY_RATE_THRESHOLD}; "
                    f"unexplained_rate={unexplained}"
                )
            elif unexplained > UNEXPLAINED_INFEASIBILITY_THRESHOLD:
                status = CriterionStatus.FAIL
                detail = (
                    f"unexplained_rate={unexplained} > {UNEXPLAINED_INFEASIBILITY_THRESHOLD}; "
                    f"class_counts={audit.class_counts}"
                )
            else:
                status = CriterionStatus.PASS
                detail = (
                    f"unexplained_rate={unexplained} held_out_infeas_rate={held_rate} "
                    f"n_probes={audit.n_probes} taxonomy_committed=true"
                )
            criteria.append(
                CriterionResult(
                    cid,
                    status,
                    evidence_pointers=[
                        "conicshield.experimental.domains.infeasibility_taxonomy.audit_infeasibility",
                        "conicshield.experimental.domains.cbf_corpus.probe_cbf_filter_bank",
                        f"research/solver-assurance-and-gradients/corpus/cbf/{CBF_CORPUS_VERSION}",
                    ],
                    detail=detail,
                    numeric={
                        "unexplained_rate": unexplained,
                        "held_out_infeasibility_rate": held_rate,
                        "failure_rate": float(audit.failure_rate),
                        "threshold_unexplained": UNEXPLAINED_INFEASIBILITY_THRESHOLD,
                        "threshold_held_out": INFEASIBILITY_RATE_THRESHOLD,
                        "n_probes": float(audit.n_probes),
                    },
                )
            )

    # Ensure checklist coverage
    seen = {c.criterion_id for c in criteria}
    for req in STAGE4_VALIDATION_CHECKLIST:
        if req not in seen:
            criteria.append(
                CriterionResult(
                    req,
                    CriterionStatus.PENDING,
                    detail="no evaluator wired for this checklist id",
                    evidence_pointers=[],
                )
            )

    required = [c for c in criteria if c.required]
    all_pass = bool(required) and all(c.status == CriterionStatus.PASS for c in required)
    rh_cap = describe_rh_capability()
    experimental_rh = bool(RH_IMPLEMENTED)
    rh_mpc_full = False
    unblock = False
    stage_status = "blocked"
    if all_pass and experimental_rh:
        stage_status = "experimental_rh_available"
        unblock = True
        notes.append(
            "All required criteria passed; experimental short-horizon RH filter is available "
            f"({rh_cap.get('experiment_version')}). Full RH-MPC / multi-robot remain out of scope."
        )
    elif all_pass:
        stage_status = "checklist_green_rh_not_implemented"
        unblock = True
        notes.append(
            "All required criteria passed with evidence pointers; experimental RH module "
            "not detected — RH runtime remains unavailable."
        )

    if evidence_dir is not None:
        evidence_dir.mkdir(parents=True, exist_ok=True)
        (evidence_dir / "stage4_gate_evaluation.json").write_text(
            json.dumps(
                Stage4GateEvaluation(
                    criteria=criteria,
                    stage4_status=stage_status,
                    unblock_allowed=unblock,
                    rh_mpc_implemented=rh_mpc_full,
                    experimental_rh_implemented=experimental_rh,
                    experimental_rh=rh_cap,
                    notes=notes,
                ).as_dict(),
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    return Stage4GateEvaluation(
        criteria=criteria,
        stage4_status=stage_status,
        unblock_allowed=unblock and all_pass,
        rh_mpc_implemented=rh_mpc_full,
        experimental_rh_implemented=experimental_rh,
        experimental_rh=rh_cap,
        notes=notes
        + [
            "rh_mpc_implemented=False: full receding-horizon MPC is not claimed.",
            "experimental_rh_implemented reflects the minimal short-horizon filter only.",
            "Do not claim CBF domain production qualification.",
        ],
    )


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="CBF stage-4 gate evaluator")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output/research/stage4_gate"),
    )
    args = parser.parse_args()
    ev = evaluate_stage4_gate(evidence_dir=args.output_dir)
    d = ev.as_dict()
    print(
        f"stage4 status={d['stage4_status']} "
        f"passed={d['passed_count']}/{d['required_count']} "
        f"pending={d['pending_count']} failed={d['failed_count']} "
        f"experimental_rh={d['experimental_rh_implemented']} "
        f"rh_mpc={d['rh_mpc_implemented']}"
    )


if __name__ == "__main__":
    main()
