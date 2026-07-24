"""Multi-environment AssuranceBundle soak harness (R4 / R12).

Records OS / Python / CPU / GPU / solver versions / commit / dirty state /
artifact hashes per soak run, and supports multi-host aggregation that flags
digest mismatches. Does **not** claim R4 production promotion.

Phase-0 invalidation of historical artifacts is preserved via
``annotate_deprecated_soak_artifact``. R12 aggregate gate evaluates genuine
multi-host predicates under assurance_bundle v1 (problem digests, matrix roles,
clean worktree, no synthetic sensitivity/hosts, governed-hash verify).
"""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import numpy as np

from conicshield.experimental.assurance.builder import build_assurance_bundle
from conicshield.experimental.assurance.checks import run_machine_checks
from conicshield.experimental.assurance.governed_hash_policy import (
    check_governed_hashes,
    default_governed_hash_policy,
)
from conicshield.experimental.assurance.migration import (
    CURRENT_SCHEMA_ID,
    INVALIDATION_PRE_V1,
    INVALIDATION_SYNTHETIC_SENSITIVITY,
    normalize_bundle_dict,
)
from conicshield.experimental.assurance.replay import bundle_from_dict, bundle_to_json, replay_bundle
from conicshield.experimental.corpus.generate import load_all_scenarios, load_manifest
from conicshield.experimental.corpus.paths import CORPUS_VERSION
from conicshield.experimental.provenance import (
    audit_provenance_completeness,
    begin_experiment_provenance,
    detect_platform_info,
    finalize_experiment_provenance,
)
from conicshield.experimental.solver_assurance.disagreement import compare_projections
from conicshield.experimental.solver_assurance.shadow_harness import run_shadow_harness

PLATFORM_SOAK_SCHEMA_ID = "research.platform_soak_report.v1"
PLATFORM_SOAK_SCHEMA_ID_V0 = "research.platform_soak_report.v0"
AGGREGATE_SCHEMA_ID = "research.platform_soak_aggregate.v1"
AGGREGATE_SCHEMA_ID_V0 = "research.platform_soak_aggregate.v0"

AGGREGATE_INVALIDATION_REASON = (
    f"{INVALIDATION_SYNTHETIC_SENSITIVITY};{INVALIDATION_PRE_V1};awaiting_r12_multihost_rebuild"
)

MatrixRole = Literal[
    "linux_public",
    "windows_public",
    "linux_wsl_moreau_cpu",
    "linux_moreau_cuda",
    "windows_wsl_sidecar",
    "unspecified",
]

REQUIRED_MATRIX_ROLES: tuple[str, ...] = (
    "linux_public",
    "windows_public",
    "linux_wsl_moreau_cpu",
    "linux_moreau_cuda",
    "windows_wsl_sidecar",
)

NATIVE_MOREAU_ROLES: frozenset[str] = frozenset(
    {
        "linux_wsl_moreau_cpu",
        "linux_moreau_cuda",
    }
)

PUBLIC_ROLES: frozenset[str] = frozenset({"linux_public", "windows_public"})

# Digests (problem / topology / sealed) use byte identity.
# Numerical residuals / action vectors may differ within tolerance across solvers.
DIGEST_COMPARISON_POLICY = "byte_identity"
NUMERICAL_COMPARISON_POLICY = "tolerance"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _solver_versions() -> dict[str, str | None]:
    versions: dict[str, str | None] = {}
    for name in ("cvxpy", "clarabel", "scs", "numpy", "moreau"):
        try:
            mod = __import__(name)
            versions[name] = getattr(mod, "__version__", None)
        except Exception:  # noqa: BLE001
            versions[name] = None
    return versions


def _package_provenance() -> dict[str, Any]:
    """Complete-enough package provenance for soak gate (distribution + version)."""

    out: dict[str, Any] = {}
    for name in ("cvxpy", "clarabel", "scs", "numpy", "moreau", "conicshield"):
        try:
            from importlib.metadata import distribution

            dist = distribution(name)
            out[name] = {
                "distribution": name,
                "version": dist.version,
                "source": None,
                "hash": None,
            }
        except Exception:  # noqa: BLE001
            out[name] = {
                "distribution": name,
                "version": None,
                "source": None,
                "hash": None,
                "available": False,
            }
    return out


def _probe_moreau_native() -> dict[str, Any]:
    """Honest availability probe — never fake native Moreau presence."""

    try:
        import moreau  # noqa: F401

        cpu = True
        cpu_reason = None
    except ImportError as exc:
        cpu = False
        cpu_reason = f"moreau_import_failed:{type(exc).__name__}"
    cuda = False
    cuda_reason = "cuda_not_probed"
    if cpu:
        try:
            import torch

            cuda = bool(torch.cuda.is_available())
            cuda_reason = None if cuda else "torch_cuda_unavailable"
        except Exception as exc:  # noqa: BLE001
            cuda = False
            cuda_reason = f"cuda_probe_failed:{type(exc).__name__}"
    return {
        "native_moreau_cpu": cpu,
        "native_moreau_cuda": cuda,
        "cpu_reason": cpu_reason,
        "cuda_reason": cuda_reason,
    }


def _probe_sidecar_hint() -> dict[str, Any]:
    """Non-authoritative sidecar / WSL hint for matrix role labeling."""

    hint: dict[str, Any] = {
        "windows_host": sys.platform == "win32",
        "wsl_available": False,
        "sidecar_attested": False,
    }
    if sys.platform != "win32":
        return hint
    try:
        from conicshield.platform.paths import wsl_available

        hint["wsl_available"] = bool(wsl_available())
    except Exception as exc:  # noqa: BLE001
        hint["wsl_error"] = f"{type(exc).__name__}: {exc}"
    return hint


def environment_signature(
    *,
    operating_system: str,
    python_version: str,
    cpu_info: str | None,
    gpu_info: str | None,
    repository_commit: str | None,
    solver_versions: dict[str, str | None],
    matrix_role: str,
) -> str:
    """Stable SHA-256 of host environment axes (not a problem digest)."""

    payload = {
        "operating_system": operating_system,
        "python_version": python_version,
        "cpu_info": cpu_info,
        "gpu_info": gpu_info,
        "repository_commit": repository_commit,
        "solver_versions": solver_versions,
        "matrix_role": matrix_role,
    }
    return _sha256_text(json.dumps(payload, sort_keys=True, separators=(",", ":")))


def resolve_matrix_role(
    *,
    matrix_role: str | None,
    host_kind: str,
) -> str:
    """Resolve / validate matrix role. Synthetic hosts cannot claim Moreau roles."""

    role = matrix_role or "unspecified"
    if role not in REQUIRED_MATRIX_ROLES and role != "unspecified":
        raise ValueError(
            f"matrix_role must be one of {REQUIRED_MATRIX_ROLES + ('unspecified',)}, got {role!r}"
        )
    if host_kind == "synthetic" and role in NATIVE_MOREAU_ROLES | {"windows_wsl_sidecar"}:
        raise ValueError(f"synthetic hosts cannot claim matrix_role={role!r}")
    return role


@dataclass(slots=True)
class PlatformMatrixRecord:
    """One soak run's platform + digests (R12 per-host artifacts)."""

    host_id: str
    operating_system: str
    python_version: str
    cpu_info: str | None
    gpu_info: str | None
    repository_commit: str | None
    dirty_worktree: bool
    corpus_version: str
    solver_versions: dict[str, str | None] = field(default_factory=dict)
    artifact_hashes: dict[str, str] = field(default_factory=dict)
    sealed_corrected_action_digest: str | None = None
    bundle_sha256: str | None = None
    all_passed: bool = False
    host_kind: str = "real"
    matrix_role: str = "unspecified"
    problem_digest: str | None = None
    forward_solution_digest: str | None = None
    package_provenance: dict[str, Any] = field(default_factory=dict)
    artifact_index: dict[str, str] = field(default_factory=dict)
    environment_signature: str | None = None
    claimed_evidence_level: str | None = None
    has_live_sensitivity: bool = False
    has_shadow: bool = False
    moreau_native: bool = False
    extras: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "host_id": self.host_id,
            "operating_system": self.operating_system,
            "python_version": self.python_version,
            "cpu_info": self.cpu_info,
            "gpu_info": self.gpu_info,
            "repository_commit": self.repository_commit,
            "dirty_worktree": self.dirty_worktree,
            "corpus_version": self.corpus_version,
            "solver_versions": dict(self.solver_versions),
            "artifact_hashes": dict(self.artifact_hashes),
            "sealed_corrected_action_digest": self.sealed_corrected_action_digest,
            "bundle_sha256": self.bundle_sha256,
            "all_passed": self.all_passed,
            "host_kind": self.host_kind,
            "matrix_role": self.matrix_role,
            "problem_digest": self.problem_digest,
            "forward_solution_digest": self.forward_solution_digest,
            "package_provenance": dict(self.package_provenance),
            "artifact_index": dict(self.artifact_index),
            "environment_signature": self.environment_signature,
            "claimed_evidence_level": self.claimed_evidence_level,
            "has_live_sensitivity": self.has_live_sensitivity,
            "has_shadow": self.has_shadow,
            "moreau_native": self.moreau_native,
            "extras": dict(self.extras),
        }


@dataclass(slots=True)
class PlatformSoakReport:
    schema_id: str = PLATFORM_SOAK_SCHEMA_ID
    corpus_version: str = CORPUS_VERSION
    platform: PlatformMatrixRecord | None = None
    replay: dict[str, Any] = field(default_factory=dict)
    checks: dict[str, bool] = field(default_factory=dict)
    migration_fixture: dict[str, Any] = field(default_factory=dict)
    provenance_audit: dict[str, Any] = field(default_factory=dict)
    r4_blockers: list[str] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)
    all_passed: bool = False
    sensitivity_fields_synthetic: bool = False
    promotion_eligible: bool = False
    invalidation_reason: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_id": self.schema_id,
            "corpus_version": self.corpus_version,
            "platform": None if self.platform is None else self.platform.as_dict(),
            "replay": dict(self.replay),
            "checks": dict(self.checks),
            "migration_fixture": dict(self.migration_fixture),
            "provenance_audit": dict(self.provenance_audit),
            "r4_blockers": list(self.r4_blockers),
            "provenance": dict(self.provenance),
            "all_passed": self.all_passed,
            "sensitivity_fields_synthetic": self.sensitivity_fields_synthetic,
            "promotion_eligible": self.promotion_eligible,
            "invalidation_reason": self.invalidation_reason,
            "promotion_claim": False,
            "note": (
                "Single-host soak evidence only unless aggregated with multi-host reports. "
                "R4 public/production flagship promotion remains blocked. "
                "Synthetic sensitivity fields are never injected; L3 requires live gradients (R11). "
                "R12 matrix roles: "
                + ", ".join(REQUIRED_MATRIX_ROLES)
            ),
        }


def run_platform_soak(
    *,
    output_dir: Path,
    host_id: str | None = None,
    exact_command: str = "python -m conicshield.experimental.assurance.platform_soak",
    host_kind: str = "real",
    matrix_role: str | None = None,
    governed_attestation: dict[str, Any] | None = None,
) -> PlatformSoakReport:
    """Execute clean-env soak with full platform matrix recording.

    ``host_kind`` must be ``real`` for independent machines / CI runners, or
    ``synthetic`` for simulated second-host fixtures. Synthetic hosts never
    count toward the R4 ≥2-real-host gate.

    Does **not** inject placeholder ``sensitivity_mode`` / ``jacobian_norm``.
    """

    if host_kind not in {"real", "synthetic"}:
        raise ValueError(f"host_kind must be 'real' or 'synthetic', got {host_kind!r}")
    role = resolve_matrix_role(matrix_role=matrix_role, host_kind=host_kind)

    from conicshield.experimental.adapters.projection import ResearchProjectionResult
    from conicshield.experimental.adapters.track1_protocols import CanonicalSolverStatus, SolverProvenance

    output_dir.mkdir(parents=True, exist_ok=True)
    plat = detect_platform_info()
    resolved_host = host_id or f"{platform.node()}|{plat['operating_system']}|{plat['python_version']}|{role}"

    prov = begin_experiment_provenance(
        scenario_corpus_version=CORPUS_VERSION,
        backend="cvxpy_clarabel",
        exact_command=exact_command,
        random_seeds={"platform_soak": 0},
        solver_distribution="cvxpy",
        tolerances={"residual": 1e-8},
        warm_start_policy="cold",
        fallback_policy="record_only",
        batch_size=1,
    )

    manifest = load_manifest()
    if manifest.get("corpus_version") != CORPUS_VERSION:
        raise RuntimeError(f"corpus version mismatch: manifest={manifest.get('corpus_version')} code={CORPUS_VERSION}")

    summary = run_shadow_harness(
        budget_fraction=1.0,
        exact_command=exact_command,
    )
    case = next(c for c in summary["cases"] if c["shadowed"])

    def _to_result(d: dict[str, Any]) -> ResearchProjectionResult:
        return ResearchProjectionResult(
            proposed_action=np.asarray(d["proposed_action"], dtype=np.float64),
            corrected_action=np.asarray(d["corrected_action"], dtype=np.float64),
            intervened=bool(d["intervened"]),
            intervention_norm=float(d["intervention_norm"]),
            solver_status=str(d["solver_status"]),
            canonical_status=CanonicalSolverStatus(str(d["canonical_status"])),
            objective_value=d.get("objective_value"),
            active_constraints=list(d.get("active_constraints") or []),
            equality_residual=d.get("equality_residual"),
            inequality_residual=d.get("inequality_residual"),
            provenance=SolverProvenance(
                backend_id=str((d.get("provenance") or {}).get("backend_id", "unknown")),
                solver_name=str((d.get("provenance") or {}).get("solver_name", "unknown")),
                solver_version=(d.get("provenance") or {}).get("solver_version"),
                package_distribution=(d.get("provenance") or {}).get("package_distribution"),
                package_version=(d.get("provenance") or {}).get("package_version"),
            )
            if d.get("provenance")
            else None,
        )

    primary = _to_result(case["primary"])
    shadow = _to_result(case["shadow"])
    disagreement = compare_projections(primary, shadow)
    scenario = next(s for s in load_all_scenarios() if s["scenario_id"] == case["scenario_id"])
    # No synthetic sensitivity injection — soak bundles cannot imply L3.
    moreau_probe = _probe_moreau_native()
    sidecar_hint = _probe_sidecar_hint()
    moreau_native = bool(
        role in NATIVE_MOREAU_ROLES and moreau_probe.get("native_moreau_cpu")
    )
    if role == "linux_moreau_cuda":
        moreau_native = bool(moreau_probe.get("native_moreau_cuda"))

    bundle = build_assurance_bundle(
        primary=primary,
        specification=scenario["spec"],
        shadow=shadow,
        disagreement=disagreement,
        shadow_backend=str(case["shadow_backend"]),
        extras={
            "corpus_version": CORPUS_VERSION,
            "platform_soak": True,
            "host_id": resolved_host,
            "matrix_role": role,
            "moreau_probe": moreau_probe,
            "sidecar_hint": sidecar_hint,
        },
    )
    bundle_path = output_dir / "assurance_bundle.json"
    bundle_to_json(bundle, bundle_path)
    sealed = bundle.corrected_action_digest()
    replay = replay_bundle(bundle_path, expected_spec_digest=bundle.specification_digest)
    checks = run_machine_checks(bundle, sealed_corrected_action_digest=sealed)

    legacy = {
        "schema_id": "research.assurance_bundle.v0_legacy",
        "action": bundle.as_dict()["corrected_action"],
        "level": str(bundle.evidence_level),
        **{k: v for k, v in bundle.as_dict().items() if k not in {"corrected_action", "evidence_level", "schema_id"}},
    }
    migrated = normalize_bundle_dict(legacy)
    migrated_bundle = bundle_from_dict(migrated)
    migrated_checks = run_machine_checks(migrated_bundle)

    finalize_experiment_provenance(prov, artifact_paths=[bundle_path])
    audit = audit_provenance_completeness(prov)
    prov.to_json(output_dir / "provenance.json")

    package_prov = _package_provenance()
    solver_vers = _solver_versions()
    env_sig = environment_signature(
        operating_system=str(plat["operating_system"]),
        python_version=str(plat["python_version"]),
        cpu_info=plat.get("cpu_info"),
        gpu_info=plat.get("gpu_info"),
        repository_commit=prov.repository_commit,
        solver_versions=solver_vers,
        matrix_role=role,
    )

    has_live_sens = (
        bundle.sensitivity_evidence is not None
        and bundle.sensitivity_evidence.is_live_validated()
        and not bundle.sensitivity_evidence.synthetic
    )
    claimed_level = str(bundle.evidence_level)

    attestation = dict(governed_attestation or {})
    if attestation and "attested" not in attestation:
        attestation["attested"] = False

    artifact_hashes = {
        "assurance_bundle.json": _sha256(bundle_path),
        "provenance.json": _sha256(output_dir / "provenance.json"),
    }
    artifact_index = {
        "assurance_bundle.json": artifact_hashes["assurance_bundle.json"],
        "provenance.json": artifact_hashes["provenance.json"],
        "sealed_corrected_action_digest": sealed,
        "problem_digest": bundle.problem_digest,
        "forward_solution_digest": bundle.forward_solution_digest,
        "environment_signature": env_sig,
    }

    hash_check = check_governed_hashes(
        artifact_hashes=artifact_hashes,
        sealed_corrected_action_digest=sealed,
        dirty_worktree=bool(prov.dirty_worktree),
        artifact_paths={
            "assurance_bundle.json": bundle_path,
            "provenance.json": output_dir / "provenance.json",
        },
        attestation=attestation or None,
        attested=bool(attestation.get("attested")) if attestation else False,
        policy=default_governed_hash_policy(),
    )
    # Research soak without attestation is expected — record but do not fail host soak.
    hash_check_relaxed = check_governed_hashes(
        artifact_hashes=artifact_hashes,
        sealed_corrected_action_digest=sealed,
        dirty_worktree=bool(prov.dirty_worktree),
        artifact_paths={
            "assurance_bundle.json": bundle_path,
            "provenance.json": output_dir / "provenance.json",
        },
        attestation={"attested": True},
        attested=True,
        policy=default_governed_hash_policy(),
    )

    bundle_hash = artifact_hashes["assurance_bundle.json"]
    platform_rec = PlatformMatrixRecord(
        host_id=resolved_host,
        operating_system=str(plat["operating_system"]),
        python_version=str(plat["python_version"]),
        cpu_info=plat.get("cpu_info"),
        gpu_info=plat.get("gpu_info"),
        repository_commit=prov.repository_commit,
        dirty_worktree=bool(prov.dirty_worktree),
        corpus_version=CORPUS_VERSION,
        solver_versions=solver_vers,
        artifact_hashes=artifact_hashes,
        sealed_corrected_action_digest=sealed,
        bundle_sha256=bundle_hash,
        all_passed=bool(replay.get("all_passed")) and all(checks.values()) and audit["complete"],
        host_kind=host_kind,
        matrix_role=role,
        problem_digest=bundle.problem_digest,
        forward_solution_digest=bundle.forward_solution_digest,
        package_provenance=package_prov,
        artifact_index=artifact_index,
        environment_signature=env_sig,
        claimed_evidence_level=claimed_level,
        has_live_sensitivity=has_live_sens,
        has_shadow=bundle.shadow_evidence is not None,
        moreau_native=moreau_native,
        extras={
            "sys_platform": sys.platform,
            "machine": platform.machine(),
            "host_kind": host_kind,
            "matrix_role": role,
            "counts_toward_r4_multi_host_gate": host_kind == "real",
            "sensitivity_fields_synthetic": False,
            "assurance_schema_id": bundle.schema_id,
            "moreau_probe": moreau_probe,
            "sidecar_hint": sidecar_hint,
            "digest_comparison_policy": DIGEST_COMPARISON_POLICY,
            "numerical_comparison_policy": NUMERICAL_COMPARISON_POLICY,
            "governed_hash_check": hash_check.as_dict(),
            "governed_hash_on_disk_ok": hash_check_relaxed.passed and not hash_check_relaxed.on_disk_mismatches,
            "replay_all_passed": bool(replay.get("all_passed")),
        },
    )

    blockers = [
        "Multi-host independent soak evidence not yet aggregated (single host in this report).",
        "Governed hash policy integration with production release tooling not wired.",
        "Assurance levels L0–L4 must not be overclaimed as universal safety guarantees.",
        "Synthetic multi-host simulation ≠ real multi-host (see MULTI_HOST_SOAK_RUNBOOK.md).",
        "R12: L4 candidates require ≥2 independent environments with matching problem digests.",
    ]
    if role in NATIVE_MOREAU_ROLES and not moreau_native:
        blockers.append(
            f"matrix_role={role} claimed but native Moreau unavailable "
            f"(probe={moreau_probe})."
        )
    if role == "windows_wsl_sidecar" and not sidecar_hint.get("wsl_available"):
        blockers.append("windows_wsl_sidecar role without WSL availability hint.")

    report = PlatformSoakReport(
        corpus_version=CORPUS_VERSION,
        platform=platform_rec,
        replay=dict(replay),
        checks=dict(checks),
        migration_fixture={
            "from": "research.assurance_bundle.v0_legacy",
            "to": migrated.get("schema_id") or CURRENT_SCHEMA_ID,
            "checks": migrated_checks,
            "all_passed": all(migrated_checks.values()),
        },
        provenance_audit=audit,
        r4_blockers=blockers,
        provenance=prov.as_dict(),
        all_passed=bool(platform_rec.all_passed),
        sensitivity_fields_synthetic=False,
        promotion_eligible=False,
        invalidation_reason=None,
    )

    out_path = output_dir / "platform_soak.json"
    out_path.write_text(json.dumps(report.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    shard = output_dir / f"platform_soak__{platform_rec.host_id.replace('|', '_').replace(' ', '_')}.json"
    shard.write_text(json.dumps(report.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    # Refresh artifact index with soak report hashes
    platform_rec.artifact_hashes["platform_soak.json"] = _sha256(out_path)
    platform_rec.artifact_index["platform_soak.json"] = platform_rec.artifact_hashes["platform_soak.json"]
    finalize_experiment_provenance(prov, artifact_paths=[out_path, shard, bundle_path])
    report.provenance = prov.as_dict()
    report.platform = platform_rec
    out_path.write_text(json.dumps(report.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    shard.write_text(json.dumps(report.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def _host_kind_of(plat: dict[str, Any]) -> str:
    kind = str(plat.get("host_kind") or (plat.get("extras") or {}).get("host_kind") or "real")
    if kind == "synthetic" or bool((plat.get("extras") or {}).get("synthetic_fixture")):
        return "synthetic"
    return "real"


def _claims_l3_or_higher(plat: dict[str, Any], row: dict[str, Any]) -> bool:
    level = str(plat.get("claimed_evidence_level") or "")
    if "L3" in level or "L4" in level:
        return True
    if bool(plat.get("has_live_sensitivity")):
        return True
    if bool(row.get("sensitivity_fields_synthetic")):
        return True
    extras = plat.get("extras") or {}
    return bool(extras.get("claims_l3") or extras.get("l3_claimed"))


def _claims_moreau(plat: dict[str, Any]) -> bool:
    role = str(plat.get("matrix_role") or "unspecified")
    if role in NATIVE_MOREAU_ROLES or role == "windows_wsl_sidecar":
        return True
    extras = plat.get("extras") or {}
    return bool(extras.get("moreau_research_claim") or extras.get("claims_moreau"))


def _claims_l4_candidate(plat: dict[str, Any], row: dict[str, Any]) -> bool:
    level = str(plat.get("claimed_evidence_level") or "")
    if "L4" in level:
        return True
    extras = plat.get("extras") or {}
    return bool(extras.get("l4_candidate") or row.get("l4_candidate"))


def aggregate_platform_soaks(
    reports: Sequence[dict[str, Any] | PlatformSoakReport],
    *,
    expected_commit: str | None = None,
    require_public_matrix: bool = False,
    require_moreau_matrix: bool = False,
) -> dict[str, Any]:
    """Merge multi-host soak reports under R12 gate predicates.

    Distinguishes ``host_kind=real`` from ``host_kind=synthetic``. Only real
    hosts count toward multi-host readiness. Digests use byte identity;
    numerical residuals use tolerance policy (recorded, not equated to digests).

    Rejects: synthetic hosts for readiness, missing gradients for L3 claims,
    stale commits, provenance mismatch, synthetic sensitivity.
    Never sets ``promotion_claim`` / ``promotion_eligible``.
    """

    rows: list[dict[str, Any]] = []
    for r in reports:
        rows.append(r.as_dict() if isinstance(r, PlatformSoakReport) else dict(r))

    digests: dict[str, set[str]] = {}
    problem_digests: set[str] = set()
    forward_digests: set[str] = set()
    bundle_hashes: dict[str, set[str]] = {}
    commits: set[str] = set()
    corpus_versions: set[str] = set()
    hosts: list[str] = []
    real_hosts: list[str] = []
    synthetic_hosts: list[str] = []
    matrix_roles: list[str] = []
    env_signatures: set[str] = set()
    dirty_hosts: list[str] = []
    missing_problem_digest_hosts: list[str] = []
    l3_missing_gradient: list[str] = []
    moreau_claim_hosts: list[str] = []
    native_moreau_hosts: list[str] = []
    l4_candidate_hosts: list[str] = []
    synthetic_sensitivity_hosts: list[str] = []
    provenance_notes: list[str] = []

    for row in rows:
        plat = dict(row.get("platform") or {})
        hid = str(plat.get("host_id") or "unknown")
        hosts.append(hid)
        kind = _host_kind_of(plat)
        plat["host_kind"] = kind
        if kind == "synthetic":
            synthetic_hosts.append(hid)
        else:
            real_hosts.append(hid)

        role = str(plat.get("matrix_role") or (plat.get("extras") or {}).get("matrix_role") or "unspecified")
        plat["matrix_role"] = role
        matrix_roles.append(role)
        row["platform"] = plat

        if bool(row.get("sensitivity_fields_synthetic")) or bool(
            (plat.get("extras") or {}).get("sensitivity_fields_synthetic")
        ):
            synthetic_sensitivity_hosts.append(hid)

        if bool(plat.get("dirty_worktree")):
            dirty_hosts.append(hid)

        sealed = plat.get("sealed_corrected_action_digest")
        bhash = plat.get("bundle_sha256")
        if sealed:
            digests.setdefault("sealed_corrected_action_digest", set()).add(str(sealed))
        if bhash:
            bundle_hashes.setdefault("bundle_sha256", set()).add(str(bhash))

        pd = plat.get("problem_digest")
        if pd:
            problem_digests.add(str(pd))
        else:
            missing_problem_digest_hosts.append(hid)
        fd = plat.get("forward_solution_digest")
        if fd:
            forward_digests.add(str(fd))

        commit = plat.get("repository_commit")
        if commit:
            commits.add(str(commit))
        cv = plat.get("corpus_version") or row.get("corpus_version")
        if cv:
            corpus_versions.add(str(cv))

        es = plat.get("environment_signature")
        if es:
            env_signatures.add(str(es))

        if _claims_l3_or_higher(plat, row) and not bool(plat.get("has_live_sensitivity")):
            l3_missing_gradient.append(hid)
        if _claims_moreau(plat):
            moreau_claim_hosts.append(hid)
        if bool(plat.get("moreau_native")):
            native_moreau_hosts.append(hid)
        if _claims_l4_candidate(plat, row):
            l4_candidate_hosts.append(hid)

    mismatches: list[str] = []
    sealed_mismatches: list[str] = []
    problem_digest_mismatches: list[str] = []
    for key, vals in digests.items():
        if len(vals) > 1:
            msg = f"{key} mismatch across hosts (byte_identity): {sorted(vals)}"
            mismatches.append(msg)
            sealed_mismatches.append(msg)
    if len(problem_digests) > 1:
        msg = f"problem_digest mismatch across hosts (byte_identity): {sorted(problem_digests)}"
        mismatches.append(msg)
        problem_digest_mismatches.append(msg)
    if missing_problem_digest_hosts:
        problem_digest_mismatches.append(
            f"missing problem_digest on hosts: {missing_problem_digest_hosts}"
        )

    forward_digest_notes: list[str] = []
    if len(forward_digests) > 1:
        forward_digest_notes.append(
            "forward_solution_digest differs across hosts "
            f"(may be numerical/solver variance; policy={NUMERICAL_COMPARISON_POLICY}; "
            f"digests use {DIGEST_COMPARISON_POLICY} when compared): {sorted(forward_digests)}"
        )

    bundle_hash_notes: list[str] = []
    for key, vals in bundle_hashes.items():
        if len(vals) > 1:
            note = (
                f"{key} differs across hosts (informational; host-local provenance may differ; "
                f"does not alone fail gate when problem digests agree): {sorted(vals)}"
            )
            mismatches.append(note)
            bundle_hash_notes.append(note)

    stale_commit_notes: list[str] = []
    if len(commits) > 1:
        stale_commit_notes.append(f"repository_commit disagree across hosts: {sorted(commits)}")
    if expected_commit is not None:
        bad = [c for c in commits if c != expected_commit]
        if bad or not commits:
            stale_commit_notes.append(
                f"stale/missing commit vs expected_commit={expected_commit}: seen={sorted(commits)}"
            )
    if len(corpus_versions) > 1:
        provenance_notes.append(f"corpus_version mismatch: {sorted(corpus_versions)}")

    n_hosts = len(set(hosts))
    n_real = len(set(real_hosts))
    n_synth = len(set(synthetic_hosts))
    roles_present = sorted(set(matrix_roles))
    public_roles_present = sorted(set(matrix_roles) & PUBLIC_ROLES)
    moreau_roles_present = sorted(set(matrix_roles) & NATIVE_MOREAU_ROLES)
    n_independent_envs = len(env_signatures) if env_signatures else n_real

    blockers: list[str] = [
        "Governed hash policy integration with production release tooling not wired.",
        "Assurance levels L0–L4 must not be overclaimed as universal safety guarantees.",
    ]
    rejection_reasons: list[str] = []

    if n_real < 2:
        msg = (
            "Need independent soak evidence from >=2 distinct **real** hosts/OS/Python "
            f"environments (n_real_hosts={n_real}, n_synthetic_hosts={n_synth})."
        )
        blockers.insert(0, msg)
        rejection_reasons.append("insufficient_real_hosts")
    if n_synth > 0:
        blockers.append("Aggregate includes synthetic host(s); synthetic ≠ real multi-host evidence.")
        rejection_reasons.append("synthetic_hosts")
    if sealed_mismatches:
        blockers.append(
            "Sealed corrected-action digest mismatch across hosts must be "
            "investigated before treating multi-host evidence as ready."
        )
        rejection_reasons.append("sealed_digest_mismatch")
    if problem_digest_mismatches:
        blockers.append(
            "Problem digests must be byte-identical across hosts for multi-host agreement."
        )
        rejection_reasons.append("problem_digest_mismatch_or_missing")
    if dirty_hosts:
        blockers.append(f"Dirty worktree not allowed for R12 gate: {dirty_hosts}")
        rejection_reasons.append("dirty_worktree")
    if stale_commit_notes:
        blockers.extend(stale_commit_notes)
        rejection_reasons.append("stale_or_mismatched_commit")
    if provenance_notes:
        blockers.extend(provenance_notes)
        rejection_reasons.append("provenance_mismatch")
    if synthetic_sensitivity_hosts:
        blockers.append(
            f"Synthetic sensitivity fields present on hosts: {synthetic_sensitivity_hosts}"
        )
        rejection_reasons.append("synthetic_sensitivity")
    if l3_missing_gradient:
        blockers.append(
            f"L3 claimed (or sensitivity claimed) without live gradient on hosts: {l3_missing_gradient}"
        )
        rejection_reasons.append("missing_gradient_for_l3")
    if moreau_claim_hosts and not native_moreau_hosts:
        blockers.append(
            "Moreau research claim present but no native Moreau host in aggregate "
            f"(claim_hosts={moreau_claim_hosts})."
        )
        rejection_reasons.append("moreau_claim_without_native_host")
    if l4_candidate_hosts and n_independent_envs < 2:
        blockers.append(
            "L4 candidates require ≥2 independent environments "
            f"(n_independent_envs={n_independent_envs}, l4_hosts={l4_candidate_hosts})."
        )
        rejection_reasons.append("l4_insufficient_independent_envs")
    if require_public_matrix and not (
        "linux_public" in roles_present and "windows_public" in roles_present
    ):
        blockers.append(
            "require_public_matrix: need both linux_public and windows_public roles "
            f"(present={roles_present})."
        )
        rejection_reasons.append("incomplete_public_matrix")
    if require_moreau_matrix and not moreau_roles_present:
        blockers.append(
            "require_moreau_matrix: need ≥1 native Moreau matrix role "
            f"(linux_wsl_moreau_cpu / linux_moreau_cuda); present={roles_present}."
        )
        rejection_reasons.append("incomplete_moreau_matrix")

    # Historical structural criterion (pre-R12): ≥2 real, no synth, sealed match.
    historical_structural_gate_ready = n_real >= 2 and n_synth == 0 and not sealed_mismatches

    # R12 genuine multi-host evidence readiness (still not a production promotion claim).
    gate_ready = (
        n_real >= 2
        and n_synth == 0
        and not sealed_mismatches
        and not problem_digest_mismatches
        and not dirty_hosts
        and not stale_commit_notes
        and not provenance_notes
        and not synthetic_sensitivity_hosts
        and not l3_missing_gradient
        and not (moreau_claim_hosts and not native_moreau_hosts)
        and not (l4_candidate_hosts and n_independent_envs < 2)
        and not (require_public_matrix and not (
            "linux_public" in roles_present and "windows_public" in roles_present
        ))
        and not (require_moreau_matrix and not moreau_roles_present)
        and all(bool(r.get("all_passed")) for r in rows)
    )

    invalidation_reason: str | None
    if gate_ready:
        invalidation_reason = None
    else:
        # Preserve Phase-0 watermark language when reports lack R12 fields entirely.
        if missing_problem_digest_hosts and not problem_digests:
            invalidation_reason = AGGREGATE_INVALIDATION_REASON
        else:
            invalidation_reason = (
                "r12_gate_rejected:" + ",".join(rejection_reasons)
                if rejection_reasons
                else AGGREGATE_INVALIDATION_REASON
            )

    return {
        "schema_id": AGGREGATE_SCHEMA_ID,
        "corpus_version": next(iter(corpus_versions), CORPUS_VERSION),
        "n_reports": len(rows),
        "n_distinct_hosts": n_hosts,
        "n_real_hosts": n_real,
        "n_synthetic_hosts": n_synth,
        "n_independent_envs": n_independent_envs,
        "hosts": hosts,
        "real_hosts": real_hosts,
        "synthetic_hosts": synthetic_hosts,
        "matrix_roles": matrix_roles,
        "matrix_roles_present": roles_present,
        "public_roles_present": public_roles_present,
        "moreau_roles_present": moreau_roles_present,
        "native_moreau_hosts": sorted(set(native_moreau_hosts)),
        "moreau_claim_hosts": sorted(set(moreau_claim_hosts)),
        "l4_candidate_hosts": sorted(set(l4_candidate_hosts)),
        "digest_mismatches": mismatches,
        "sealed_digest_mismatches": sealed_mismatches,
        "problem_digest_mismatches": problem_digest_mismatches,
        "forward_digest_notes": forward_digest_notes,
        "bundle_hash_notes": bundle_hash_notes,
        "stale_commit_notes": stale_commit_notes,
        "provenance_notes": provenance_notes,
        "rejection_reasons": rejection_reasons,
        "digest_comparison_policy": DIGEST_COMPARISON_POLICY,
        "numerical_comparison_policy": NUMERICAL_COMPARISON_POLICY,
        "solver_platform_diversity": {
            "n_real_hosts": n_real,
            "n_environment_signatures": len(env_signatures),
            "matrix_roles": roles_present,
            "commits": sorted(commits),
        },
        "all_hosts_passed": all(bool(r.get("all_passed")) for r in rows) if rows else False,
        "r4_blockers": blockers,
        "r4_multi_host_gate_ready": gate_ready,
        "historical_structural_gate_ready": historical_structural_gate_ready,
        "promotion_claim": False,
        "promotion_eligible": False,
        "invalidation_reason": invalidation_reason,
        "reports": rows,
        "note": (
            "R12 aggregation: rejects synthetic hosts, synthetic sensitivity, "
            "missing L3 gradients, stale commits, provenance mismatch; "
            "problem digests use byte_identity; numerical fields use tolerance policy. "
            "r4_multi_host_gate_ready is evidence readiness only — never a production claim. "
            "Historical Phase-0 artifacts remain invalidated via annotate_deprecated_soak_artifact."
        ),
    }


def annotate_deprecated_soak_artifact(data: dict[str, Any]) -> dict[str, Any]:
    """Preserve historical soak JSON under deprecated schema with invalidation metadata."""

    out = dict(data)
    schema = str(out.get("schema_id") or "")
    historical_ready = out.get("r4_multi_host_gate_ready")
    if "aggregate" in schema or schema.endswith("aggregate.v0") or "reports" in out and "n_real_hosts" in out:
        out["deprecated_source_schema"] = schema or AGGREGATE_SCHEMA_ID_V0
        out["schema_id"] = AGGREGATE_SCHEMA_ID_V0
        out["historical_r4_multi_host_gate_ready"] = historical_ready
        out["r4_multi_host_gate_ready"] = False
        out["promotion_eligible"] = False
        out["promotion_claim"] = False
        out["invalidation_reason"] = AGGREGATE_INVALIDATION_REASON
    else:
        out["deprecated_source_schema"] = schema or PLATFORM_SOAK_SCHEMA_ID_V0
        out["schema_id"] = PLATFORM_SOAK_SCHEMA_ID_V0
        out["sensitivity_fields_synthetic"] = True
        out["promotion_eligible"] = False
        out["promotion_claim"] = False
        out["invalidation_reason"] = (
            f"{INVALIDATION_SYNTHETIC_SENSITIVITY};{INVALIDATION_PRE_V1}"
        )
        extras = dict(out.get("extras") or {})
        extras["sensitivity_fields_synthetic"] = True
        extras["experimental_invalidated"] = True
        out["extras"] = extras
    return out


def invalidate_on_disk_soak_artifacts(root: Path) -> list[Path]:
    """Annotate existing soak JSON under ``root`` in place (do not delete)."""

    touched: list[Path] = []
    if not root.exists():
        return touched
    for path in sorted(root.rglob("platform_soak*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(raw, dict):
            continue
        annotated = annotate_deprecated_soak_artifact(raw)
        path.write_text(json.dumps(annotated, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        touched.append(path)
    return touched


def load_soak_reports(paths: list[Path]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for p in paths:
        raw = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise TypeError(f"soak report must be an object: {p}")
        out.append(raw)
    return out


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="R12 platform matrix soak")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output/research/platform_soak"),
    )
    parser.add_argument("--host-id", type=str, default=None)
    parser.add_argument(
        "--host-kind",
        choices=["real", "synthetic"],
        default="real",
        help="real=independent machine/CI runner; synthetic=fixture (does not count for R4)",
    )
    parser.add_argument(
        "--matrix-role",
        choices=[*REQUIRED_MATRIX_ROLES, "unspecified"],
        default="unspecified",
        help="R12 matrix role label for this host",
    )
    parser.add_argument(
        "--aggregate",
        nargs="*",
        type=Path,
        default=None,
        help="Optional list of platform_soak JSON paths to aggregate",
    )
    parser.add_argument(
        "--expected-commit",
        type=str,
        default=None,
        help="Optional expected git commit; reject aggregates with stale/mismatched commits",
    )
    parser.add_argument(
        "--require-public-matrix",
        action="store_true",
        help="Require both linux_public and windows_public roles for gate readiness",
    )
    parser.add_argument(
        "--require-moreau-matrix",
        action="store_true",
        help="Require ≥1 native Moreau matrix role for gate readiness",
    )
    parser.add_argument(
        "--invalidate-artifacts",
        type=Path,
        default=None,
        help="Annotate historical soak JSON under this root with invalidation metadata",
    )
    args = parser.parse_args()
    if args.invalidate_artifacts is not None:
        touched = invalidate_on_disk_soak_artifacts(args.invalidate_artifacts)
        print(f"annotated {len(touched)} soak artifacts under {args.invalidate_artifacts}")
        return
    if args.aggregate is not None and len(args.aggregate) > 0:
        reports = load_soak_reports(list(args.aggregate))
        agg = aggregate_platform_soaks(
            reports,
            expected_commit=args.expected_commit,
            require_public_matrix=bool(args.require_public_matrix),
            require_moreau_matrix=bool(args.require_moreau_matrix),
        )
        out = args.output_dir
        out.mkdir(parents=True, exist_ok=True)
        path = out / "platform_soak_aggregate.json"
        path.write_text(json.dumps(agg, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(
            f"aggregate hosts={agg['n_distinct_hosts']} "
            f"real={agg['n_real_hosts']} synthetic={agg['n_synthetic_hosts']} "
            f"roles={agg['matrix_roles_present']} "
            f"mismatches={len(agg['digest_mismatches'])} "
            f"r4_ready={agg['r4_multi_host_gate_ready']} "
            f"historical_structural={agg['historical_structural_gate_ready']} "
            f"promotion_eligible={agg['promotion_eligible']} "
            f"rejection={agg.get('rejection_reasons')}"
        )
        print(f"wrote {path}")
        return
    report = run_platform_soak(
        output_dir=args.output_dir,
        host_id=args.host_id,
        host_kind=args.host_kind,
        matrix_role=args.matrix_role,
    )
    print(
        f"platform soak all_passed={report.all_passed} "
        f"host={report.platform.host_id if report.platform else None} "
        f"host_kind={report.platform.host_kind if report.platform else None} "
        f"matrix_role={report.platform.matrix_role if report.platform else None} "
        f"level_cap=no_synthetic_sensitivity"
    )


if __name__ == "__main__":
    main()
