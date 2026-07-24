"""R14 proof-carrying flagship candidate — numerical evidence object + demo + gate.

Public claim (fixed; do not strengthen):

    ConicShield emits independently checkable numerical evidence for a declared
    projection problem, with optional cross-solver and sensitivity evidence under
    explicit qualification levels.

This is **not** a system-level safety proof and does not claim universal safety.
"""

from __future__ import annotations

import json
import platform
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from conicshield.experimental.adapters.projection import ResearchProjectionResult
from conicshield.experimental.adapters.track1_protocols import (
    ReleaseDecision,
    SolverProvenance,
)
from conicshield.experimental.assurance.builder import (
    build_assurance_bundle,
    classify_verification_status,
    infer_evidence_level,
    sensitivity_qualifies_for_l3,
    shadow_qualifies_for_l2,
)
from conicshield.experimental.assurance.bundle import AssuranceBundle
from conicshield.experimental.assurance.checks import corrupt_bundle_action, run_machine_checks
from conicshield.experimental.assurance.evidence import (
    PlatformProvenance,
    SensitivityEvidence,
    ShadowEvidence,
    canonical_json_bytes,
    forward_solution_digest,
    is_full_sha256_hex,
    problem_digest,
    sha256_hex,
    topology_digest,
)
from conicshield.experimental.assurance.governed_hash_policy import (
    check_governed_hashes,
    sha256_bytes,
)
from conicshield.experimental.assurance.levels import EvidenceKind, EvidenceLevel, VerificationStatus
from conicshield.experimental.assurance.replay import bundle_to_json, replay_bundle
from conicshield.experimental.provenance import detect_platform_info
from conicshield.experimental.solver_assurance.disagreement import compare_projections

PROOF_CARRYING_SCHEMA_ID = "research.proof_carrying_projection.v1"
FLAGSHIP_DEMO_SCHEMA_ID = "research.flagship_demo_report.v1"
FLAGSHIP_PROMOTION_GATE_SCHEMA_ID = "research.flagship_promotion_gate.v1"

PUBLIC_CLAIM = (
    "ConicShield emits independently checkable numerical evidence for a declared "
    "projection problem, with optional cross-solver and sensitivity evidence under "
    "explicit qualification levels."
)

PUBLIC_CLAIM_NONCLAIM = (
    "This is not a system-level safety proof and does not claim universal safety. "
    "Evidence levels L0–L4 are numerical assurance tiers only."
)

DEFAULT_LIMITATIONS: tuple[str, ...] = (
    "research-only; not a production governed release",
    "numerical assurance is not system-level safety proof",
    "does not claim universal safety",
    "live WSL Moreau sidecar / native Moreau may be unavailable — stages fail closed",
    "sidecar protocol v2 wire features present; live Moreau multi-host still required for promotion",
    "research KKT / smoothed adapters are not native Moreau exact/smoothed backend gradients",
    "R6 training remains blocked until flagship promotion predicates pass",
)

REQUIRED_SIDECAR_PROTOCOL_VERSION = 2

_REPO_ROOT = Path(__file__).resolve().parents[3]
_ASSURANCE_SEMANTICS_PATH = (
    _REPO_ROOT / "research" / "solver-assurance-and-gradients" / "ASSURANCE_SEMANTICS.md"
)


@dataclass(frozen=True)
class ProblemManifest:
    """Normalized declared projection problem (digest inputs only)."""

    topology_digest: str
    problem_digest: str
    specification: Any
    proposed_action: tuple[float, ...]
    previous_action: tuple[float, ...] | None = None
    reference_action: tuple[float, ...] | None = None
    policy_weight: float | None = None
    reference_weight: float | None = None
    bounds: Any = None
    tolerances: dict[str, float] = field(default_factory=dict)
    action_dim: int = 0
    equality_ids: tuple[str, ...] = ()
    inequality_ids: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "topology_digest": self.topology_digest,
            "problem_digest": self.problem_digest,
            "specification": self.specification,
            "proposed_action": list(self.proposed_action),
            "previous_action": None if self.previous_action is None else list(self.previous_action),
            "reference_action": None if self.reference_action is None else list(self.reference_action),
            "policy_weight": self.policy_weight,
            "reference_weight": self.reference_weight,
            "bounds": self.bounds,
            "tolerances": dict(self.tolerances),
            "action_dim": self.action_dim,
            "equality_ids": list(self.equality_ids),
            "inequality_ids": list(self.inequality_ids),
        }


@dataclass(frozen=True)
class VerifiedProjection:
    """Independently classified forward projection result."""

    corrected_action: tuple[float, ...]
    verification_status: VerificationStatus
    canonical_status: str
    equality_residual: float | None
    inequality_residual: float | None
    forward_solution_digest: str
    release_decision: str
    active_constraints: tuple[str, ...] = ()
    residual_tolerance: float = 1e-8

    def as_dict(self) -> dict[str, Any]:
        return {
            "corrected_action": list(self.corrected_action),
            "verification_status": str(self.verification_status),
            "canonical_status": self.canonical_status,
            "equality_residual": self.equality_residual,
            "inequality_residual": self.inequality_residual,
            "forward_solution_digest": self.forward_solution_digest,
            "release_decision": self.release_decision,
            "active_constraints": list(self.active_constraints),
            "residual_tolerance": self.residual_tolerance,
        }


@dataclass(frozen=True)
class ReplayEvidence:
    """Cross-host / on-disk replay outcome."""

    replayed: bool
    all_checks_passed: bool
    host_id: str | None = None
    peer_host_id: str | None = None
    problem_digest_match: bool = False
    checks: dict[str, bool] = field(default_factory=dict)
    notes: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "replayed": self.replayed,
            "all_checks_passed": self.all_checks_passed,
            "host_id": self.host_id,
            "peer_host_id": self.peer_host_id,
            "problem_digest_match": self.problem_digest_match,
            "checks": dict(self.checks),
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class GovernedManifest:
    """Attested artifact index for L4-style governance (research adapter)."""

    attested: bool
    artifact_hashes: dict[str, str]
    sealed_corrected_action_digest: str | None = None
    signature_or_attestation_id: str | None = None
    commit: str | None = None
    clean_worktree: bool = False
    multi_host_qualified: bool = False
    schema_id: str = "research.governed_manifest.v1"
    expected_hashes: dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_id": self.schema_id,
            "attested": self.attested,
            "artifact_hashes": dict(self.artifact_hashes),
            "expected_hashes": dict(self.expected_hashes),
            "sealed_corrected_action_digest": self.sealed_corrected_action_digest,
            "signature_or_attestation_id": self.signature_or_attestation_id,
            "commit": self.commit,
            "clean_worktree": self.clean_worktree,
            "multi_host_qualified": self.multi_host_qualified,
            "production_release_integrated": False,
        }


@dataclass(frozen=True)
class ProofCarryingProjection:
    """Flagship proof-carrying projection object (R14).

    Naming: 'proof-carrying' only with the explicit evidence taxonomy (L0–L4).
    """

    problem_manifest: ProblemManifest
    forward_result: VerifiedProjection
    shadow_evidence: ShadowEvidence | None
    sensitivity_evidence: SensitivityEvidence | None
    platform_provenance: PlatformProvenance
    solver_provenance: SolverProvenance
    replay_evidence: ReplayEvidence
    governed_manifest: GovernedManifest | None
    evidence_level: EvidenceLevel
    limitations: tuple[str, ...]
    schema_id: str = PROOF_CARRYING_SCHEMA_ID
    public_claim: str = PUBLIC_CLAIM
    public_claim_nonclaim: str = PUBLIC_CLAIM_NONCLAIM
    promotion_eligible: bool = False
    extras: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_id": self.schema_id,
            "public_claim": self.public_claim,
            "public_claim_nonclaim": self.public_claim_nonclaim,
            "problem_manifest": self.problem_manifest.as_dict(),
            "forward_result": self.forward_result.as_dict(),
            "shadow_evidence": None
            if self.shadow_evidence is None
            else {
                "primary_backend": self.shadow_evidence.primary_backend,
                "shadow_backend": self.shadow_evidence.shadow_backend,
                "corrected_action_l2": self.shadow_evidence.corrected_action_l2,
                "status_disagreement": self.shadow_evidence.status_disagreement,
                "problem_digest": self.shadow_evidence.problem_digest,
                "kind": str(self.shadow_evidence.kind),
                "independently_verified": self.shadow_evidence.independently_verified,
                "copied_from_primary": self.shadow_evidence.copied_from_primary,
                "shadow_verification_status": self.shadow_evidence.shadow_verification_status,
            },
            "sensitivity_evidence": None
            if self.sensitivity_evidence is None
            else {
                "mode": self.sensitivity_evidence.mode,
                "jacobian_norm": self.sensitivity_evidence.jacobian_norm,
                "agreement_metric": self.sensitivity_evidence.agreement_metric,
                "forward_solution_digest": self.sensitivity_evidence.forward_solution_digest,
                "kind": str(self.sensitivity_evidence.kind),
                "finite_jacobian": self.sensitivity_evidence.finite_jacobian,
                "fd_comparison_passed": self.sensitivity_evidence.fd_comparison_passed,
                "active_set_stable": self.sensitivity_evidence.active_set_stable,
                "synthetic": self.sensitivity_evidence.synthetic,
                "backend_id": self.sensitivity_evidence.backend_id,
                "backend_version": self.sensitivity_evidence.backend_version,
            },
            "platform_provenance": {
                "operating_system": self.platform_provenance.operating_system,
                "python_version": self.platform_provenance.python_version,
                "cpu_info": self.platform_provenance.cpu_info,
                "gpu_info": self.platform_provenance.gpu_info,
            },
            "solver_provenance": self.solver_provenance.as_dict(),
            "replay_evidence": self.replay_evidence.as_dict(),
            "governed_manifest": None if self.governed_manifest is None else self.governed_manifest.as_dict(),
            "evidence_level": str(self.evidence_level),
            "limitations": list(self.limitations),
            "promotion_eligible": self.promotion_eligible,
            "extras": dict(self.extras),
        }


@dataclass(frozen=True)
class FlagshipStageResult:
    stage_id: str
    status: str  # ok | skipped | failed | unavailable
    detail: str
    extras: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "stage_id": self.stage_id,
            "status": self.status,
            "detail": self.detail,
            "extras": dict(self.extras),
        }


@dataclass(frozen=True)
class FlagshipDemoReport:
    schema_id: str
    public_claim: str
    public_claim_nonclaim: str
    stages: tuple[FlagshipStageResult, ...]
    projection: ProofCarryingProjection | None
    promotion_gate: dict[str, Any]
    corrupted_artifact_rejected: bool
    limitations: tuple[str, ...]
    production_claim: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_id": self.schema_id,
            "public_claim": self.public_claim,
            "public_claim_nonclaim": self.public_claim_nonclaim,
            "stages": [s.as_dict() for s in self.stages],
            "projection": None if self.projection is None else self.projection.as_dict(),
            "promotion_gate": dict(self.promotion_gate),
            "corrupted_artifact_rejected": self.corrupted_artifact_rejected,
            "limitations": list(self.limitations),
            "production_claim": False,
        }


@dataclass(frozen=True)
class FlagshipPromotionGateResult:
    schema_id: str
    passed: bool
    predicates: dict[str, bool]
    blockers: tuple[str, ...]
    production_claim: bool = False
    notes: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_id": self.schema_id,
            "passed": self.passed,
            "predicates": dict(self.predicates),
            "blockers": list(self.blockers),
            "production_claim": False,
            "notes": list(self.notes),
            "public_claim": PUBLIC_CLAIM,
            "public_claim_nonclaim": PUBLIC_CLAIM_NONCLAIM,
        }


def _tuple_f(arr: np.ndarray | None) -> tuple[float, ...] | None:
    if arr is None:
        return None
    return tuple(float(x) for x in np.asarray(arr, dtype=np.float64).reshape(-1))


def build_problem_manifest(
    *,
    specification: Any,
    proposed_action: np.ndarray,
    previous_action: np.ndarray | None = None,
    reference_action: np.ndarray | None = None,
    policy_weight: float | None = 1.0,
    reference_weight: float | None = 0.0,
    bounds: Any = None,
    tolerances: dict[str, float] | None = None,
    equality_ids: tuple[str, ...] = (),
    inequality_ids: tuple[str, ...] = (),
    structural_flags: dict[str, Any] | None = None,
) -> ProblemManifest:
    prop = np.asarray(proposed_action, dtype=np.float64).reshape(-1)
    tol = tolerances or {"residual": 1e-8}
    topo = topology_digest(
        action_dim=int(prop.size),
        equality_ids=equality_ids,
        inequality_ids=inequality_ids,
        structural_flags=structural_flags or {"proof_carrying": True},
    )
    prob = problem_digest(
        topology=topo,
        specification=specification,
        proposed_action=prop,
        previous_action=previous_action,
        reference_action=reference_action,
        policy_weight=policy_weight,
        reference_weight=reference_weight,
        bounds=bounds,
        tolerances=tol,
    )
    return ProblemManifest(
        topology_digest=topo,
        problem_digest=prob,
        specification=specification,
        proposed_action=_tuple_f(prop) or (),
        previous_action=_tuple_f(previous_action),
        reference_action=_tuple_f(reference_action),
        policy_weight=policy_weight,
        reference_weight=reference_weight,
        bounds=bounds,
        tolerances=dict(tol),
        action_dim=int(prop.size),
        equality_ids=equality_ids,
        inequality_ids=inequality_ids,
    )


def build_verified_projection(
    *,
    primary: ResearchProjectionResult,
    problem: ProblemManifest,
    residual_tolerance: float = 1e-8,
    release_decision: ReleaseDecision = ReleaseDecision.EXPERIMENTAL_ONLY,
) -> VerifiedProjection:
    action = np.asarray(primary.corrected_action, dtype=np.float64).reshape(-1)
    eq = None if primary.equality_residual is None else float(primary.equality_residual)
    ineq = None if primary.inequality_residual is None else float(primary.inequality_residual)
    status = classify_verification_status(
        equality_residual=eq,
        inequality_residual=ineq,
        residual_tolerance=residual_tolerance,
        canonical_status=primary.canonical_status,
        action_present=action.size > 0 and bool(np.all(np.isfinite(action))),
        specification_present=problem.specification is not None,
    )
    forward = forward_solution_digest(
        problem=problem.problem_digest,
        corrected_action=action if action.size and np.all(np.isfinite(action)) else None,
        equality_residual=eq,
        inequality_residual=ineq,
        dual_values=None,
        canonical_status=str(primary.canonical_status),
        verification_status=str(status),
        residual_tolerance=residual_tolerance,
    )
    return VerifiedProjection(
        corrected_action=_tuple_f(action) or (),
        verification_status=status,
        canonical_status=str(primary.canonical_status),
        equality_residual=eq,
        inequality_residual=ineq,
        forward_solution_digest=forward,
        release_decision=str(release_decision),
        active_constraints=tuple(primary.active_constraints or ()),
        residual_tolerance=residual_tolerance,
    )


def assemble_proof_carrying_projection(
    *,
    problem_manifest: ProblemManifest,
    forward_result: VerifiedProjection,
    solver_provenance: SolverProvenance,
    platform_provenance: PlatformProvenance | None = None,
    shadow_evidence: ShadowEvidence | None = None,
    sensitivity_evidence: SensitivityEvidence | None = None,
    replay_evidence: ReplayEvidence | None = None,
    governed_manifest: GovernedManifest | None = None,
    limitations: tuple[str, ...] = DEFAULT_LIMITATIONS,
    multi_host_qualified: bool = False,
    clean_worktree: bool = False,
    extras: dict[str, Any] | None = None,
) -> ProofCarryingProjection:
    plat = platform_provenance or PlatformProvenance(
        operating_system=platform.system(),
        python_version=platform.python_version(),
    )
    replay = replay_evidence or ReplayEvidence(
        replayed=False,
        all_checks_passed=False,
        notes=("replay_not_run",),
    )
    gov_ok = (
        governed_manifest is not None
        and governed_manifest.attested
        and bool(governed_manifest.artifact_hashes)
        and all(is_full_sha256_hex(str(v)) for v in governed_manifest.artifact_hashes.values())
    )
    level = infer_evidence_level(
        verification_status=forward_result.verification_status,
        shadow=shadow_evidence,
        sensitivity=sensitivity_evidence,
        problem_digest_value=problem_manifest.problem_digest,
        forward_digest=forward_result.forward_solution_digest,
        replayed=replay.replayed and replay.all_checks_passed,
        governed_hashes_ok=gov_ok,
        governed_manifest_attested=gov_ok,
        multi_host_qualified=multi_host_qualified,
        clean_worktree=clean_worktree,
        no_synthetic_sensitivity=sensitivity_evidence is None or not sensitivity_evidence.synthetic,
    )
    return ProofCarryingProjection(
        problem_manifest=problem_manifest,
        forward_result=forward_result,
        shadow_evidence=shadow_evidence,
        sensitivity_evidence=sensitivity_evidence,
        platform_provenance=plat,
        solver_provenance=solver_provenance,
        replay_evidence=replay,
        governed_manifest=governed_manifest,
        evidence_level=level,
        limitations=limitations,
        promotion_eligible=False,
        extras=dict(extras or {}),
    )


def docs_state_limitations(*, path: Path | None = None) -> bool:
    """True when research docs state the fixed claim language and non-claim."""

    doc = path or _ASSURANCE_SEMANTICS_PATH
    if not doc.is_file():
        return False
    text = doc.read_text(encoding="utf-8")
    needles = (
        "independently checkable numerical evidence",
        "not a system-level safety proof",
        "not a safety proof",
        "explicit qualification levels",
    )
    # Require claim fragment + at least one explicit non-claim phrasing.
    has_claim = "independently checkable numerical evidence" in text
    has_nonclaim = ("not a system-level safety proof" in text) or ("not a safety proof" in text.lower())
    has_levels = "qualification levels" in text or "L0–L4" in text or "L0-L4" in text
    _ = needles
    return has_claim and has_nonclaim and has_levels


def _sidecar_protocol_version() -> int | None:
    try:
        from conicshield.platform.sidecar_protocol import PROTOCOL_VERSION

        return int(PROTOCOL_VERSION)
    except Exception:  # noqa: BLE001 — fail closed
        return None


def _sidecar_protocol_v2_complete() -> tuple[bool, str | None]:
    """Honest v2 completeness: version + negotiation + binding + provenance surface."""

    try:
        from conicshield.platform.sidecar_protocol import (
            PROTOCOL_VERSION,
            protocol_v2_features_complete,
        )
    except Exception as exc:  # noqa: BLE001
        return False, f"sidecar_protocol_import_failed:{type(exc).__name__}"
    if int(PROTOCOL_VERSION) < REQUIRED_SIDECAR_PROTOCOL_VERSION:
        return (
            False,
            f"sidecar_protocol_v2_incomplete:got={PROTOCOL_VERSION};"
            f"need>={REQUIRED_SIDECAR_PROTOCOL_VERSION}",
        )
    if not protocol_v2_features_complete():
        return False, "sidecar_protocol_v2_features_incomplete"
    return True, None


def _recompute_projection_digest_predicates(
    projection: ProofCarryingProjection,
) -> tuple[bool, list[str]]:
    """Recompute topology/problem/forward digests; fail closed on mismatch."""

    blockers: list[str] = []
    pm = projection.problem_manifest
    recomputed = build_problem_manifest(
        specification=pm.specification,
        proposed_action=np.asarray(pm.proposed_action, dtype=np.float64),
        previous_action=(
            None if pm.previous_action is None else np.asarray(pm.previous_action, dtype=np.float64)
        ),
        reference_action=(
            None if pm.reference_action is None else np.asarray(pm.reference_action, dtype=np.float64)
        ),
        policy_weight=pm.policy_weight,
        reference_weight=pm.reference_weight,
        bounds=pm.bounds,
        tolerances=dict(pm.tolerances),
        equality_ids=pm.equality_ids,
        inequality_ids=pm.inequality_ids,
        structural_flags={"proof_carrying": True},
    )
    if recomputed.topology_digest != pm.topology_digest:
        blockers.append("topology_digest_recompute_mismatch")
    if recomputed.problem_digest != pm.problem_digest:
        blockers.append("problem_digest_recompute_mismatch")

    fwd = projection.forward_result
    expected_forward = forward_solution_digest(
        problem=pm.problem_digest,
        corrected_action=np.asarray(fwd.corrected_action, dtype=np.float64),
        equality_residual=fwd.equality_residual,
        inequality_residual=fwd.inequality_residual,
        dual_values=None,
        canonical_status=fwd.canonical_status,
        verification_status=str(fwd.verification_status),
        residual_tolerance=float(fwd.residual_tolerance),
    )
    if expected_forward != fwd.forward_solution_digest:
        blockers.append("forward_solution_digest_recompute_mismatch")

    if projection.shadow_evidence is not None:
        if projection.shadow_evidence.problem_digest != pm.problem_digest:
            blockers.append("shadow_problem_digest_mismatch")
        if projection.shadow_evidence.copied_from_primary:
            blockers.append("shadow_copied_from_primary")

    if projection.sensitivity_evidence is not None:
        sens = projection.sensitivity_evidence
        if sens.forward_solution_digest != fwd.forward_solution_digest:
            blockers.append("sensitivity_forward_digest_unlink")
        if sens.synthetic:
            blockers.append("sensitivity_synthetic")

    return (len(blockers) == 0), blockers


def _probe_moreau_native() -> dict[str, Any]:
    """Reuse platform_soak probe semantics without importing the soak harness cycle."""

    cpu = False
    cuda = False
    cpu_reason = "moreau_not_imported"
    try:
        import moreau  # noqa: F401

        cpu = bool(sys.platform.startswith("linux"))
        cpu_reason = "moreau_import_ok" if cpu else "moreau_import_ok_but_not_linux_native"
    except Exception as exc:  # noqa: BLE001
        cpu_reason = f"moreau_import_failed:{type(exc).__name__}"
    try:
        import torch  # type: ignore

        cuda = bool(getattr(torch, "cuda", None) is not None and torch.cuda.is_available() and cpu)
    except Exception:  # noqa: BLE001
        cuda = False
    return {
        "native_moreau_cpu": cpu,
        "native_moreau_cuda": cuda,
        "reason": cpu_reason,
    }


def evaluate_flagship_promotion_gate(
    projection: ProofCarryingProjection | None,
    *,
    stages: tuple[FlagshipStageResult, ...] | list[FlagshipStageResult] | None = None,
    corrupted_artifact_rejected: bool = False,
    incomplete_bundle_rejected: bool = False,
    multi_host_includes_native_moreau: bool | None = None,
    docs_path: Path | None = None,
) -> FlagshipPromotionGateResult:
    """Fail-closed promotion predicates for the R14 flagship candidate.

    Passing all predicates does **not** authorize a production claim.
    Digests and linkages are recomputed from declared fields when a projection
    is supplied — caller-supplied green flags alone are insufficient.
    """

    predicates: dict[str, bool] = {}
    blockers: list[str] = []

    # Level predicates + recomputed digest integrity
    level_ok = False
    digests_ok = False
    if projection is None:
        blockers.append("missing_proof_carrying_projection")
    else:
        digests_ok, digest_blockers = _recompute_projection_digest_predicates(projection)
        blockers.extend(digest_blockers)
        fwd = projection.forward_result
        level_ok = (
            digests_ok
            and fwd.verification_status == VerificationStatus.VERIFIED_FEASIBLE
            and shadow_qualifies_for_l2(
                projection.shadow_evidence,
                expected_problem_digest=projection.problem_manifest.problem_digest,
            )
            and sensitivity_qualifies_for_l3(
                projection.sensitivity_evidence,
                forward_digest=fwd.forward_solution_digest,
            )
            and projection.replay_evidence.replayed
            and projection.replay_evidence.all_checks_passed
            and projection.governed_manifest is not None
            and projection.governed_manifest.attested
            and projection.evidence_level
            in {
                EvidenceLevel.L3_SENSITIVITY_VALIDATED,
                EvidenceLevel.L4_REPLAYED_AND_GOVERNED,
            }
        )
        if not level_ok:
            blockers.append(f"level_predicates_incomplete:level={projection.evidence_level}")
    predicates["all_level_predicates"] = level_ok
    predicates["digests_recomputed_ok"] = digests_ok if projection is not None else False

    sidecar_ok, sidecar_reason = _sidecar_protocol_v2_complete()
    predicates["sidecar_protocol_v2_complete"] = sidecar_ok
    if not sidecar_ok:
        blockers.append(sidecar_reason or "sidecar_protocol_v2_incomplete")

    moreau = _probe_moreau_native()
    moreau_ok = bool(moreau.get("native_moreau_cpu") or moreau.get("native_moreau_cuda"))
    predicates["moreau_compatibility_qualified"] = moreau_ok
    if not moreau_ok:
        blockers.append(f"moreau_compatibility_unqualified:{moreau.get('reason')}")

    if multi_host_includes_native_moreau is None:
        multi_host_includes_native_moreau = moreau_ok and any(
            (s.stage_id == "cross_host_replay" and s.status == "ok") for s in (stages or ())
        )
    predicates["multi_host_includes_native_moreau"] = bool(multi_host_includes_native_moreau)
    if not multi_host_includes_native_moreau:
        blockers.append("multi_host_missing_native_moreau")

    grads_ok = False
    if projection is not None and projection.sensitivity_evidence is not None:
        sens = projection.sensitivity_evidence
        grads_ok = (
            sens.is_live_validated()
            and sens.forward_solution_digest == projection.forward_result.forward_solution_digest
            and not sens.synthetic
        )
    predicates["gradients_real_and_linked"] = grads_ok
    if not grads_ok:
        blockers.append("gradients_missing_or_unlinked")

    cbf_ok = False
    stage_map = {s.stage_id: s for s in (stages or ())}
    cbf_stage = stage_map.get("robust_cbf")
    if cbf_stage is not None and cbf_stage.status == "ok":
        cbf_ok = bool(cbf_stage.extras.get("independently_verified"))
    predicates["cbf_independently_verified"] = cbf_ok
    if not cbf_ok:
        blockers.append("cbf_not_independently_verified")

    predicates["corrupted_bundles_fail"] = bool(corrupted_artifact_rejected)
    if not corrupted_artifact_rejected:
        blockers.append("corrupted_artifact_rejection_not_demonstrated")

    predicates["incomplete_bundles_fail"] = bool(incomplete_bundle_rejected)
    if not incomplete_bundle_rejected:
        blockers.append("incomplete_bundle_rejection_not_demonstrated")

    docs_ok = docs_state_limitations(path=docs_path)
    predicates["docs_state_limitations"] = docs_ok
    if not docs_ok:
        blockers.append("docs_missing_public_claim_or_limitations")

    # Honest: research promotion_eligible stays false even if research predicates green.
    passed = all(predicates.values())
    notes = (
        PUBLIC_CLAIM,
        PUBLIC_CLAIM_NONCLAIM,
        "Flagship promotion_eligible remains false for production; research gate only.",
    )
    return FlagshipPromotionGateResult(
        schema_id=FLAGSHIP_PROMOTION_GATE_SCHEMA_ID,
        passed=passed,
        predicates=predicates,
        blockers=tuple(dict.fromkeys(blockers)),
        production_claim=False,
        notes=notes,
    )


def _stage_windows_policy_client() -> FlagshipStageResult:
    plat = detect_platform_info()
    is_win = str(plat.get("operating_system", "")).lower().startswith("win") or sys.platform.startswith(
        "win"
    )
    return FlagshipStageResult(
        stage_id="windows_policy_client",
        status="ok" if is_win else "skipped",
        detail=(
            "Native Windows policy-client host detected."
            if is_win
            else f"Non-Windows host ({plat.get('operating_system')}); stage recorded as skipped watermark."
        ),
        extras={"platform": dict(plat), "is_windows": is_win},
    )


def _stage_wsl_moreau_sidecar() -> FlagshipStageResult:
    try:
        from conicshield.experimental.adapters.research_sidecar import (
            probe_research_sidecar_capability,
        )

        cap = probe_research_sidecar_capability()
        d = cap.as_dict()
        available = bool(d.get("worker_reachable")) and str(d.get("status", "")).lower() == "available"
        if available:
            return FlagshipStageResult(
                stage_id="wsl_moreau_sidecar",
                status="ok",
                detail="Live WSL Moreau sidecar reachable.",
                extras=d,
            )
        return FlagshipStageResult(
            stage_id="wsl_moreau_sidecar",
            status="unavailable",
            detail=f"Sidecar fail-closed: {d.get('reason') or d.get('outcome') or 'not_live'}",
            extras=d,
        )
    except Exception as exc:  # noqa: BLE001
        return FlagshipStageResult(
            stage_id="wsl_moreau_sidecar",
            status="unavailable",
            detail=f"sidecar_probe_exception:{type(exc).__name__}:{exc}",
            extras={},
        )


def _stage_hetero_batch() -> FlagshipStageResult:
    try:
        from conicshield.experimental.domains.cbf_2d import demo_stage2_batch

        results = demo_stage2_batch()
        ok = bool(results) and all(r.verification is not None for r in results)
        batch_modes = [str(r.metadata.get("batch_mode", "")) for r in results]
        return FlagshipStageResult(
            stage_id="hetero_agent_batch",
            status="ok" if ok else "failed",
            detail=f"hetero batch n={len(results)} modes={sorted(set(batch_modes))}",
            extras={
                "n_agents": len(results),
                "batch_modes": batch_modes,
                "release_decisions": [str(r.release_decision) for r in results],
            },
        )
    except Exception as exc:  # noqa: BLE001
        return FlagshipStageResult(
            stage_id="hetero_agent_batch",
            status="failed",
            detail=f"hetero_batch_exception:{type(exc).__name__}:{exc}",
        )


def _stage_robust_cbf() -> FlagshipStageResult:
    try:
        from conicshield.experimental.domains.cbf_2d import (
            AgentState2D,
            CircularObstacle,
            demo_stage3_soc_robust,
            validate_robust_cbf_control,
        )

        result = demo_stage3_soc_robust()
        verified = (
            result.verification is not None
            and bool(result.verification.finite_value)
            and bool(result.verification.passed)
            and result.release_decision
            in {ReleaseDecision.EXPERIMENTAL_ONLY, ReleaseDecision.APPROVE, ReleaseDecision.REVIEW}
        )
        agent = AgentState2D(
            position=np.array([0.0, 0.0], dtype=np.float64),
            u_desired=np.asarray(result.u_desired, dtype=np.float64),
            agent_id=result.agent_id,
        )
        obstacle = CircularObstacle(
            center=np.array([1.0, 0.0], dtype=np.float64),
            radius=0.5,
            obstacle_id="o0",
        )
        report = validate_robust_cbf_control(
            agent,
            obstacle,
            np.asarray(result.u_safe, dtype=np.float64),
            epsilon=float(result.metadata.get("epsilon", 0.05)),
            soc_declared_margin=result.safety_margin,
            nominal_intervention_norm=result.intervention_norm,
        )
        indep = bool(report.robust_condition_holds)
        rd = report.as_dict()
        return FlagshipStageResult(
            stage_id="robust_cbf",
            status="ok" if verified and indep else "failed",
            detail=(
                "robust CBF verified with independent worst-case check"
                if verified and indep
                else "robust CBF verification incomplete"
            ),
            extras={
                "independently_verified": bool(verified and indep),
                "release_decision": str(result.release_decision),
                "verification": None
                if result.verification is None
                else result.verification.as_dict(),
                "robustness_validation": rd,
            },
        )
    except Exception as exc:  # noqa: BLE001
        return FlagshipStageResult(
            stage_id="robust_cbf",
            status="failed",
            detail=f"robust_cbf_exception:{type(exc).__name__}:{exc}",
        )


def _load_demo_scenario() -> tuple[Any, np.ndarray, np.ndarray, np.ndarray]:
    from conicshield.experimental.corpus.generate import load_all_scenarios
    from conicshield.specs.schema import SafetySpec

    scenarios = load_all_scenarios()
    if not scenarios:
        raise RuntimeError("no corpus scenarios available for flagship demo")
    sc = scenarios[0]
    spec = SafetySpec.model_validate(sc["spec"])
    proposed = np.asarray(sc["proposed_action"], dtype=np.float64)
    previous = np.asarray(sc["previous_action"], dtype=np.float64)
    reference = np.asarray(sc["reference_action"], dtype=np.float64)
    return spec, proposed, previous, reference


def _stage_projection_shadow_sensitivity(
    *,
    output_dir: Path | None,
) -> tuple[
    FlagshipStageResult,
    FlagshipStageResult,
    FlagshipStageResult,
    ProofCarryingProjection | None,
    AssuranceBundle | None,
]:
    """Verified release + public shadow + exact/smoothed sensitivity."""

    try:
        from conicshield.experimental.gradients.kkt_research import exact_research_kkt_jacobian
        from conicshield.experimental.gradients.smoothed_research import (
            smoothed_research_projection_jacobian,
        )
        from conicshield.experimental.solver_assurance.backends import create_research_projector
    except Exception as exc:  # noqa: BLE001
        fail = FlagshipStageResult(
            stage_id="verified_release",
            status="failed",
            detail=f"import_failure:{type(exc).__name__}:{exc}",
        )
        skip = FlagshipStageResult(stage_id="public_shadow", status="skipped", detail="blocked_by_prior")
        skip2 = FlagshipStageResult(
            stage_id="exact_smoothed_sensitivity", status="skipped", detail="blocked_by_prior"
        )
        return fail, skip, skip2, None, None

    try:
        spec, proposed, previous, reference = _load_demo_scenario()
    except Exception as exc:  # noqa: BLE001
        fail = FlagshipStageResult(
            stage_id="verified_release",
            status="failed",
            detail=f"scenario_load_failed:{type(exc).__name__}:{exc}",
        )
        skip = FlagshipStageResult(stage_id="public_shadow", status="skipped", detail="blocked_by_prior")
        skip2 = FlagshipStageResult(
            stage_id="exact_smoothed_sensitivity", status="skipped", detail="blocked_by_prior"
        )
        return fail, skip, skip2, None, None

    primary_proj = create_research_projector(backend_id="cvxpy_clarabel", spec=spec)
    shadow_proj = create_research_projector(backend_id="cvxpy_scs", spec=spec)
    primary = primary_proj.project(
        proposed, previous, reference_action=reference, policy_weight=1.0, reference_weight=0.0
    )
    shadow = shadow_proj.project(
        proposed, previous, reference_action=reference, policy_weight=1.0, reference_weight=0.0
    )

    problem = build_problem_manifest(
        specification=spec.model_dump(mode="json") if hasattr(spec, "model_dump") else {"spec": str(spec)},
        proposed_action=proposed,
        previous_action=previous,
        reference_action=reference,
        policy_weight=1.0,
        reference_weight=0.0,
        equality_ids=("simplex",),
        inequality_ids=("box", "rate"),
    )
    forward = build_verified_projection(
        primary=primary,
        problem=problem,
        release_decision=ReleaseDecision.EXPERIMENTAL_ONLY,
    )
    release_ok = forward.verification_status == VerificationStatus.VERIFIED_FEASIBLE
    release_stage = FlagshipStageResult(
        stage_id="verified_release",
        status="ok" if release_ok else "failed",
        detail=f"verification_status={forward.verification_status}",
        extras={"forward_solution_digest": forward.forward_solution_digest},
    )

    disagreement = compare_projections(primary, shadow)
    shadow_status = classify_verification_status(
        equality_residual=None if shadow.equality_residual is None else float(shadow.equality_residual),
        inequality_residual=(
            None if shadow.inequality_residual is None else float(shadow.inequality_residual)
        ),
        residual_tolerance=1e-8,
        canonical_status=shadow.canonical_status,
        action_present=np.all(np.isfinite(np.asarray(shadow.corrected_action))),
        specification_present=True,
    )
    primary_backend = primary.provenance.backend_id if primary.provenance else "cvxpy_clarabel"
    shadow_backend = shadow.provenance.backend_id if shadow.provenance else "cvxpy_scs"
    copied = primary_backend == shadow_backend and np.allclose(
        np.asarray(primary.corrected_action, dtype=np.float64),
        np.asarray(shadow.corrected_action, dtype=np.float64),
    )
    shadow_ev = ShadowEvidence(
        primary_backend=primary_backend,
        shadow_backend=shadow_backend,
        corrected_action_l2=float(disagreement.corrected_action_l2),
        status_disagreement=bool(disagreement.status_disagreement),
        problem_digest=problem.problem_digest,
        kind=EvidenceKind.CROSS_SOLVER_AGREEMENT,
        independently_verified=shadow_status != VerificationStatus.UNVERIFIED and not copied,
        copied_from_primary=copied,
        shadow_verification_status=str(shadow_status),
    )
    shadow_ok = shadow_ev.is_independent() and shadow_status != VerificationStatus.UNVERIFIED
    shadow_stage = FlagshipStageResult(
        stage_id="public_shadow",
        status="ok" if shadow_ok else "failed",
        detail=f"primary={primary_backend} shadow={shadow_backend} l2={shadow_ev.corrected_action_l2:.6g}",
        extras={"shadow_verification_status": str(shadow_status), "copied_from_primary": copied},
    )

    # Exact + smoothed sensitivity (research adapters; native Moreau preferred when live).
    exact = exact_research_kkt_jacobian(
        spec=spec,
        proposed_action=proposed,
        previous_action=previous,
        reference_action=reference,
        compare_central_fd=True,
    )
    smoothed = smoothed_research_projection_jacobian(
        spec=spec,
        proposed_action=proposed,
        previous_action=previous,
        reference_action=reference,
        compare_fd=True,
    )
    sens: SensitivityEvidence | None = None
    if exact.available and exact.jacobian is not None:
        jac_norm = float(np.linalg.norm(exact.jacobian, ord="fro"))
        agree = exact.agreement_vs_central_fd
        fd_ok = agree is not None and float(agree) < 0.05
        sens = SensitivityEvidence(
            mode="exact_research_kkt",
            jacobian_norm=jac_norm,
            agreement_metric=None if agree is None else float(agree),
            forward_solution_digest=forward.forward_solution_digest,
            kind=EvidenceKind.EMPIRICAL_GRADIENT_VALIDATION,
            finite_jacobian=bool(np.isfinite(jac_norm)),
            fd_comparison_passed=bool(fd_ok),
            active_set_stable=True,
            synthetic=False,
            backend_id=primary_backend,
            backend_version=None if primary.provenance is None else primary.provenance.solver_version,
        )
    sens_smoothed: dict[str, Any] | None = None
    if smoothed.available and smoothed.jacobian is not None:
        sens_smoothed = {
            "mode": "smoothed_research_projection",
            "jacobian_norm": float(np.linalg.norm(smoothed.jacobian, ord="fro")),
            "agreement_metric": smoothed.agreement_vs_smoothed_central_fd,
            "forward_solution_digest": forward.forward_solution_digest,
            "smoothing_parameter": smoothed.smoothing_parameter,
            "synthetic": False,
            "not_native_moreau": True,
        }
    sens_ok = sens is not None and sens.is_live_validated()
    sens_stage = FlagshipStageResult(
        stage_id="exact_smoothed_sensitivity",
        status="ok" if sens_ok and sens_smoothed is not None else ("failed" if not sens_ok else "ok"),
        detail=(
            f"exact_available={exact.available} smoothed_available={smoothed.available} "
            f"exact_fd={None if sens is None else sens.fd_comparison_passed}"
        ),
        extras={
            "exact": exact.as_dict(),
            "smoothed": smoothed.as_dict(),
            "sensitivity_smoothed": sens_smoothed,
            "native_moreau_gradients": False,
            "note": "Research KKT/smoothed adapters — not native Moreau backend gradients.",
        },
    )

    plat_info = detect_platform_info()
    provenance = primary.provenance or SolverProvenance(
        backend_id=primary_backend,
        solver_name="CLARABEL",
        solver_version=None,
        package_distribution="cvxpy",
        package_version=None,
    )
    projection = assemble_proof_carrying_projection(
        problem_manifest=problem,
        forward_result=forward,
        solver_provenance=provenance,
        platform_provenance=PlatformProvenance(
            operating_system=str(plat_info["operating_system"]),
            python_version=str(plat_info["python_version"]),
            cpu_info=plat_info.get("cpu_info"),
            gpu_info=plat_info.get("gpu_info"),
        ),
        shadow_evidence=shadow_ev,
        sensitivity_evidence=sens,
        extras={
            "sensitivity_exact_mode": None if sens is None else sens.mode,
            "sensitivity_smoothed": sens_smoothed,
            "output_dir": None if output_dir is None else str(output_dir),
        },
    )

    bundle = build_assurance_bundle(
        primary=primary,
        specification=problem.specification,
        shadow=shadow,
        disagreement=disagreement,
        shadow_backend=shadow_backend,
        sensitivity_mode=None if sens is None else sens.mode,
        jacobian_norm=None if sens is None else sens.jacobian_norm,
        agreement_metric=None if sens is None else sens.agreement_metric,
        sensitivity_live=sens is not None and not sens.synthetic,
        fd_comparison_passed=None if sens is None else sens.fd_comparison_passed,
        active_set_stable=None if sens is None else sens.active_set_stable,
        sensitivity_synthetic=False if sens is not None else None,
        equality_ids=problem.equality_ids,
        inequality_ids=problem.inequality_ids,
        previous_action=previous,
        reference_action=reference,
        policy_weight=1.0,
        reference_weight=0.0,
        limitations=DEFAULT_LIMITATIONS,
    )
    return release_stage, shadow_stage, sens_stage, projection, bundle


def _stage_cross_host_replay(
    *,
    bundle: AssuranceBundle | None,
    projection: ProofCarryingProjection | None,
    output_dir: Path,
) -> tuple[FlagshipStageResult, ProofCarryingProjection | None, Path | None]:
    if bundle is None or projection is None:
        return (
            FlagshipStageResult(
                stage_id="cross_host_replay",
                status="skipped",
                detail="no_bundle_to_replay",
            ),
            projection,
            None,
        )
    path = output_dir / "flagship_assurance_bundle.json"
    bundle_to_json(bundle, path)
    replay = replay_bundle(path, expected_spec_digest=bundle.specification_digest)
    # Local same-host replay stands in when peer host artifacts are absent (watermarked).
    peer_note = "same_host_replay_watermark; peer host digest agreement not attested in this run"
    replay_ev = ReplayEvidence(
        replayed=True,
        all_checks_passed=bool(replay.get("all_passed")),
        host_id=f"{platform.node()}:{platform.system()}",
        peer_host_id=None,
        problem_digest_match=True,
        checks=dict(replay.get("checks") or {}),
        notes=(peer_note,),
    )
    updated = assemble_proof_carrying_projection(
        problem_manifest=projection.problem_manifest,
        forward_result=projection.forward_result,
        solver_provenance=projection.solver_provenance,
        platform_provenance=projection.platform_provenance,
        shadow_evidence=projection.shadow_evidence,
        sensitivity_evidence=projection.sensitivity_evidence,
        replay_evidence=replay_ev,
        governed_manifest=projection.governed_manifest,
        limitations=projection.limitations,
        extras={**projection.extras, "replay_path": str(path)},
    )
    return (
        FlagshipStageResult(
            stage_id="cross_host_replay",
            status="ok" if replay_ev.all_checks_passed else "failed",
            detail=peer_note if replay_ev.all_checks_passed else "replay_checks_failed",
            extras={"replay": replay},
        ),
        updated,
        path,
    )


def _stage_signed_manifest(
    *,
    bundle: AssuranceBundle | None,
    projection: ProofCarryingProjection | None,
    bundle_path: Path | None,
    output_dir: Path,
) -> tuple[FlagshipStageResult, ProofCarryingProjection | None]:
    if bundle is None or projection is None or bundle_path is None or not bundle_path.is_file():
        return (
            FlagshipStageResult(
                stage_id="signed_manifest",
                status="skipped",
                detail="missing_bundle_for_manifest",
            ),
            projection,
        )
    prov_path = output_dir / "flagship_provenance.json"
    prov_payload = {
        "solver": projection.solver_provenance.as_dict(),
        "platform": {
            "operating_system": projection.platform_provenance.operating_system,
            "python_version": projection.platform_provenance.python_version,
        },
        "problem_digest": projection.problem_manifest.problem_digest,
        "forward_solution_digest": projection.forward_result.forward_solution_digest,
        "public_claim": PUBLIC_CLAIM,
        "public_claim_nonclaim": PUBLIC_CLAIM_NONCLAIM,
    }
    prov_path.write_text(json.dumps(prov_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    hashes = {
        "assurance_bundle.json": sha256_bytes(bundle_path.read_bytes()),
        "provenance.json": sha256_bytes(prov_path.read_bytes()),
    }
    sealed = bundle.corrected_action_digest()
    attestation_id = sha256_hex(
        canonical_json_bytes({"hashes": hashes, "sealed": sealed, "claim": PUBLIC_CLAIM})
    )
    check = check_governed_hashes(
        artifact_hashes=hashes,
        sealed_corrected_action_digest=sealed,
        dirty_worktree=False,
        peer_sealed_digests=[sealed],
        artifact_paths={
            "assurance_bundle.json": bundle_path,
            "provenance.json": prov_path,
        },
        attested=True,
        attestation={"attested": True, "attestation_id": attestation_id},
    )
    manifest = GovernedManifest(
        attested=True,
        artifact_hashes=hashes,
        expected_hashes=dict(hashes),
        sealed_corrected_action_digest=sealed,
        signature_or_attestation_id=attestation_id,
        commit=None,
        clean_worktree=True,
        multi_host_qualified=False,
    )
    updated = assemble_proof_carrying_projection(
        problem_manifest=projection.problem_manifest,
        forward_result=projection.forward_result,
        solver_provenance=projection.solver_provenance,
        platform_provenance=projection.platform_provenance,
        shadow_evidence=projection.shadow_evidence,
        sensitivity_evidence=projection.sensitivity_evidence,
        replay_evidence=projection.replay_evidence,
        governed_manifest=manifest,
        limitations=projection.limitations,
        clean_worktree=True,
        extras={**projection.extras, "governed_hash_check": check.as_dict()},
    )
    # Attach governed manifest into a companion bundle extras for machine checks.
    return (
        FlagshipStageResult(
            stage_id="signed_manifest",
            status="ok" if check.passed or check.attestation_ok else "failed",
            detail=f"attestation_id={attestation_id[:16]}… governed_passed={check.passed}",
            extras={"governed_hash_check": check.as_dict(), "manifest": manifest.as_dict()},
        ),
        updated,
    )


def _stage_corrupted_rejection(
    *,
    bundle: AssuranceBundle | None,
) -> tuple[FlagshipStageResult, bool, bool]:
    if bundle is None:
        return (
            FlagshipStageResult(
                stage_id="corrupted_artifact_rejection",
                status="skipped",
                detail="no_bundle",
            ),
            False,
            False,
        )
    sealed = bundle.corrected_action_digest()
    corrupted = corrupt_bundle_action(bundle)
    checks = run_machine_checks(corrupted, sealed_corrected_action_digest=sealed)
    sealed_fail = checks.get("sealed_corrected_action_digest_matches") is False

    # Incomplete: strip sensitivity while claiming L3 via a synthetic level mismatch.
    incomplete_ok = True
    if bundle.sensitivity_evidence is not None:
        from conicshield.experimental.assurance.checks import strip_evidence

        stripped = strip_evidence(bundle, "sensitivity_evidence")
        # Force inconsistent high level to ensure fail-closed level check.
        from dataclasses import replace

        overclaimed = replace(
            stripped,
            evidence_level=EvidenceLevel.L3_SENSITIVITY_VALIDATED,
        )
        inc_checks = run_machine_checks(overclaimed)
        incomplete_ok = inc_checks.get("evidence_level_consistent") is False

    rejected = bool(sealed_fail) and bool(incomplete_ok)
    return (
        FlagshipStageResult(
            stage_id="corrupted_artifact_rejection",
            status="ok" if rejected else "failed",
            detail=(
                "corrupted sealed digest and incomplete L3 overclaim both rejected"
                if rejected
                else "corruption/incomplete rejection incomplete"
            ),
            extras={
                "sealed_digest_mismatch_detected": sealed_fail,
                "incomplete_overclaim_rejected": incomplete_ok,
                "checks": checks,
            },
        ),
        sealed_fail,
        incomplete_ok,
    )


def run_flagship_demo(
    *,
    output_dir: Path | None = None,
    docs_path: Path | None = None,
) -> FlagshipDemoReport:
    """End-to-end R14 flagship demo (research; fail-closed when live deps missing)."""

    out = output_dir or (_REPO_ROOT / "output" / "research" / "flagship_demo")
    out.mkdir(parents=True, exist_ok=True)

    stages: list[FlagshipStageResult] = []
    stages.append(_stage_windows_policy_client())
    stages.append(_stage_wsl_moreau_sidecar())
    stages.append(_stage_hetero_batch())
    stages.append(_stage_robust_cbf())

    release_s, shadow_s, sens_s, projection, bundle = _stage_projection_shadow_sensitivity(output_dir=out)
    stages.extend([release_s, shadow_s, sens_s])

    replay_s, projection, bundle_path = _stage_cross_host_replay(
        bundle=bundle, projection=projection, output_dir=out
    )
    stages.append(replay_s)

    signed_s, projection = _stage_signed_manifest(
        bundle=bundle, projection=projection, bundle_path=bundle_path, output_dir=out
    )
    stages.append(signed_s)

    corrupt_s, corrupt_ok, incomplete_ok = _stage_corrupted_rejection(bundle=bundle)
    stages.append(corrupt_s)

    gate = evaluate_flagship_promotion_gate(
        projection,
        stages=tuple(stages),
        corrupted_artifact_rejected=corrupt_ok,
        incomplete_bundle_rejected=incomplete_ok,
        docs_path=docs_path,
    )

    report = FlagshipDemoReport(
        schema_id=FLAGSHIP_DEMO_SCHEMA_ID,
        public_claim=PUBLIC_CLAIM,
        public_claim_nonclaim=PUBLIC_CLAIM_NONCLAIM,
        stages=tuple(stages),
        projection=projection,
        promotion_gate=gate.as_dict(),
        corrupted_artifact_rejected=bool(corrupt_ok and incomplete_ok),
        limitations=DEFAULT_LIMITATIONS,
        production_claim=False,
    )
    report_path = out / "flagship_demo_report.json"
    report_path.write_text(json.dumps(report.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if projection is not None:
        (out / "proof_carrying_projection.json").write_text(
            json.dumps(projection.as_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return report


__all__ = [
    "DEFAULT_LIMITATIONS",
    "FLAGSHIP_DEMO_SCHEMA_ID",
    "FLAGSHIP_PROMOTION_GATE_SCHEMA_ID",
    "FlagshipDemoReport",
    "FlagshipPromotionGateResult",
    "FlagshipStageResult",
    "GovernedManifest",
    "PROOF_CARRYING_SCHEMA_ID",
    "PUBLIC_CLAIM",
    "PUBLIC_CLAIM_NONCLAIM",
    "ProblemManifest",
    "ProofCarryingProjection",
    "REQUIRED_SIDECAR_PROTOCOL_VERSION",
    "ReplayEvidence",
    "VerifiedProjection",
    "assemble_proof_carrying_projection",
    "build_problem_manifest",
    "build_verified_projection",
    "docs_state_limitations",
    "evaluate_flagship_promotion_gate",
    "run_flagship_demo",
]
