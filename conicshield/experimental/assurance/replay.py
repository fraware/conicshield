"""AssuranceBundle replay tools (R4)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import numpy as np

from conicshield.experimental.adapters.track1_protocols import (
    CanonicalSolverStatus,
    ReleaseDecision,
    ResearchVerificationReport,
    SolverProvenance,
)
from conicshield.experimental.assurance.bundle import AssuranceBundle
from conicshield.experimental.assurance.checks import run_machine_checks
from conicshield.experimental.assurance.evidence import (
    ActiveSetEvidence,
    DeclaredAssumption,
    DualEvidence,
    FallbackAttempt,
    PlatformProvenance,
    PrimalEvidence,
    SensitivityEvidence,
    ShadowEvidence,
)
from conicshield.experimental.assurance.levels import EvidenceKind, EvidenceLevel


def bundle_to_json(bundle: AssuranceBundle, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(bundle.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def bundle_from_dict(data: dict[str, Any]) -> AssuranceBundle:
    """Reconstruct AssuranceBundle from serialized dict (replay)."""

    ver = data["verification"]
    prim = data["primal_evidence"]
    dual_raw = data.get("dual_evidence")
    sens_raw = data.get("sensitivity_evidence")
    shadow_raw = data.get("shadow_evidence")
    solv = data["solver_provenance"]
    plat = data["platform_provenance"]

    dual: DualEvidence | None = None
    if dual_raw is not None:
        dual = DualEvidence(
            dual_values=tuple(float(x) for x in dual_raw["dual_values"]),
            constraint_ids=tuple(dual_raw["constraint_ids"]),
            kind=EvidenceKind(dual_raw.get("kind", EvidenceKind.SOLVER_CLAIMS)),
        )
    sens: SensitivityEvidence | None = None
    if sens_raw is not None:
        sens = SensitivityEvidence(
            mode=str(sens_raw["mode"]),
            jacobian_norm=float(sens_raw["jacobian_norm"]),
            agreement_metric=sens_raw.get("agreement_metric"),
            forward_solution_digest=str(sens_raw["forward_solution_digest"]),
            kind=EvidenceKind(sens_raw.get("kind", EvidenceKind.EMPIRICAL_GRADIENT_VALIDATION)),
        )
    shadow: ShadowEvidence | None = None
    if shadow_raw is not None:
        shadow = ShadowEvidence(
            primary_backend=str(shadow_raw["primary_backend"]),
            shadow_backend=str(shadow_raw["shadow_backend"]),
            corrected_action_l2=float(shadow_raw["corrected_action_l2"]),
            status_disagreement=bool(shadow_raw["status_disagreement"]),
            problem_digest=str(shadow_raw["problem_digest"]),
            kind=EvidenceKind(shadow_raw.get("kind", EvidenceKind.CROSS_SOLVER_AGREEMENT)),
        )

    return AssuranceBundle(
        corrected_action=np.asarray(data["corrected_action"], dtype=np.float64),
        specification_digest=str(data["specification_digest"]),
        structural_fingerprint=str(data["structural_fingerprint"]),
        verification=ResearchVerificationReport(
            equality_residual=float(ver["equality_residual"]),
            inequality_residual=float(ver["inequality_residual"]),
            primal_feasible=bool(ver["primal_feasible"]),
            dual_available=bool(ver["dual_available"]),
            residual_tolerance=float(ver["residual_tolerance"]),
            checks=dict(ver.get("checks") or {}),
            notes=tuple(ver.get("notes") or ()),
        ),
        canonical_status=CanonicalSolverStatus(str(data["canonical_status"])),
        release_decision=ReleaseDecision(str(data["release_decision"])),
        primal_evidence=PrimalEvidence(
            equality_residual=float(prim["equality_residual"]),
            inequality_residual=float(prim["inequality_residual"]),
            feasible=bool(prim["feasible"]),
            kind=EvidenceKind(prim.get("kind", EvidenceKind.NUMERICAL_RESIDUALS)),
        ),
        dual_evidence=dual,
        active_set_evidence=ActiveSetEvidence(
            active_constraints=tuple(data["active_set_evidence"]["active_constraints"]),
            kind=EvidenceKind(data["active_set_evidence"].get("kind", EvidenceKind.SOLVER_CLAIMS)),
        ),
        sensitivity_evidence=sens,
        shadow_evidence=shadow,
        solver_provenance=SolverProvenance(
            backend_id=str(solv["backend_id"]),
            solver_name=str(solv["solver_name"]),
            solver_version=solv.get("solver_version"),
            package_distribution=solv.get("package_distribution"),
            package_version=solv.get("package_version"),
        ),
        platform_provenance=PlatformProvenance(
            operating_system=str(plat["operating_system"]),
            python_version=str(plat["python_version"]),
            cpu_info=plat.get("cpu_info"),
            gpu_info=plat.get("gpu_info"),
        ),
        fallback_history=tuple(
            FallbackAttempt(backend_id=str(f["backend_id"]), status=str(f["status"]), reason=str(f["reason"]))
            for f in data.get("fallback_history") or []
        ),
        assumptions=tuple(
            DeclaredAssumption(
                assumption_id=str(a["assumption_id"]),
                statement=str(a["statement"]),
                verified=bool(a.get("verified", False)),
                kind=EvidenceKind(a.get("kind", EvidenceKind.UNVERIFIED_ASSUMPTIONS)),
            )
            for a in data.get("assumptions") or []
        ),
        limitations=tuple(data.get("limitations") or ()),
        evidence_level=EvidenceLevel(str(data.get("evidence_level", EvidenceLevel.L0_RECORDED))),
        schema_id=str(data.get("schema_id", "research.assurance_bundle.v0")),
        naming_note=str(
            data.get(
                "naming_note",
                "Use 'proof-carrying' only with an explicit evidence taxonomy.",
            )
        ),
        extras=dict(data.get("extras") or {}),
    )


def load_bundle(path: Path) -> AssuranceBundle:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise TypeError(f"assurance bundle must be an object: {path}")
    return bundle_from_dict(cast(dict[str, Any], raw))


def replay_bundle(
    path: Path,
    *,
    expected_spec_digest: str | None = None,
) -> dict[str, Any]:
    """Load a bundle and re-run machine checks (replay)."""

    bundle = load_bundle(path)
    checks = run_machine_checks(bundle, expected_spec_digest=expected_spec_digest)
    return {
        "path": str(path),
        "schema_id": bundle.schema_id,
        "evidence_level": str(bundle.evidence_level),
        "checks": checks,
        "all_passed": all(checks.values()),
        "naming_note": bundle.naming_note,
    }
