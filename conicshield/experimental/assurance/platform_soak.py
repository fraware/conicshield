"""Multi-environment AssuranceBundle soak harness (R4 evidence).

Records OS / Python / CPU / GPU / solver versions / commit / dirty state /
artifact hashes per soak run, and supports multi-host aggregation that flags
digest mismatches. Does **not** claim R4 production promotion.
"""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from conicshield.experimental.assurance.builder import build_assurance_bundle
from conicshield.experimental.assurance.checks import run_machine_checks
from conicshield.experimental.assurance.migration import normalize_bundle_dict
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

PLATFORM_SOAK_SCHEMA_ID = "research.platform_soak_report.v0"
AGGREGATE_SCHEMA_ID = "research.platform_soak_aggregate.v0"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _solver_versions() -> dict[str, str | None]:
    versions: dict[str, str | None] = {}
    for name in ("cvxpy", "clarabel", "scs", "numpy"):
        try:
            mod = __import__(name)
            versions[name] = getattr(mod, "__version__", None)
        except Exception:  # noqa: BLE001
            versions[name] = None
    return versions


@dataclass(slots=True)
class PlatformMatrixRecord:
    """One soak run's platform + digests."""

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
            "promotion_claim": False,
            "note": (
                "Single-host soak evidence only unless aggregated with multi-host reports. "
                "R4 public/production flagship promotion remains blocked."
            ),
        }


def run_platform_soak(
    *,
    output_dir: Path,
    host_id: str | None = None,
    exact_command: str = "python -m conicshield.experimental.assurance.platform_soak",
    host_kind: str = "real",
) -> PlatformSoakReport:
    """Execute clean-env soak with full platform matrix recording.

    ``host_kind`` must be ``real`` for independent machines / CI runners, or
    ``synthetic`` for simulated second-host fixtures. Synthetic hosts never
    count toward the R4 ≥2-real-host gate.
    """

    if host_kind not in {"real", "synthetic"}:
        raise ValueError(f"host_kind must be 'real' or 'synthetic', got {host_kind!r}")

    from conicshield.experimental.adapters.projection import ResearchProjectionResult
    from conicshield.experimental.adapters.track1_protocols import CanonicalSolverStatus, SolverProvenance

    output_dir.mkdir(parents=True, exist_ok=True)
    plat = detect_platform_info()
    resolved_host = host_id or f"{platform.node()}|{plat['operating_system']}|{plat['python_version']}"

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
        raise RuntimeError(
            f"corpus version mismatch: manifest={manifest.get('corpus_version')} code={CORPUS_VERSION}"
        )

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
    bundle = build_assurance_bundle(
        primary=primary,
        specification=scenario["spec"],
        shadow=shadow,
        disagreement=disagreement,
        shadow_backend=str(case["shadow_backend"]),
        sensitivity_mode="central_finite_difference",
        jacobian_norm=1.0,
        agreement_metric=0.0,
        extras={"corpus_version": CORPUS_VERSION, "platform_soak": True, "host_id": resolved_host},
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
        **{
            k: v
            for k, v in bundle.as_dict().items()
            if k not in {"corrected_action", "evidence_level", "schema_id"}
        },
    }
    migrated = normalize_bundle_dict(legacy)
    migrated_bundle = bundle_from_dict(migrated)
    migrated_checks = run_machine_checks(migrated_bundle)

    finalize_experiment_provenance(prov, artifact_paths=[bundle_path])
    audit = audit_provenance_completeness(prov)
    prov.to_json(output_dir / "provenance.json")

    bundle_hash = _sha256(bundle_path)
    platform_rec = PlatformMatrixRecord(
        host_id=resolved_host,
        operating_system=str(plat["operating_system"]),
        python_version=str(plat["python_version"]),
        cpu_info=plat.get("cpu_info"),
        gpu_info=plat.get("gpu_info"),
        repository_commit=prov.repository_commit,
        dirty_worktree=bool(prov.dirty_worktree),
        corpus_version=CORPUS_VERSION,
        solver_versions=_solver_versions(),
        artifact_hashes={
            "assurance_bundle.json": bundle_hash,
            "provenance.json": _sha256(output_dir / "provenance.json"),
        },
        sealed_corrected_action_digest=sealed,
        bundle_sha256=bundle_hash,
        all_passed=bool(replay.get("all_passed")) and all(checks.values()) and audit["complete"],
        host_kind=host_kind,
        extras={
            "sys_platform": sys.platform,
            "machine": platform.machine(),
            "host_kind": host_kind,
            "counts_toward_r4_multi_host_gate": host_kind == "real",
        },
    )

    blockers = [
        "Multi-host independent soak evidence not yet aggregated (single host in this report).",
        "Governed hash policy integration with production release tooling not wired.",
        "Assurance levels L0–L4 must not be overclaimed as universal safety guarantees.",
        "Synthetic multi-host simulation ≠ real multi-host (see MULTI_HOST_SOAK_RUNBOOK.md).",
    ]

    report = PlatformSoakReport(
        corpus_version=CORPUS_VERSION,
        platform=platform_rec,
        replay=dict(replay),
        checks=dict(checks),
        migration_fixture={
            "from": "research.assurance_bundle.v0_legacy",
            "to": migrated.get("schema_id"),
            "checks": migrated_checks,
            "all_passed": all(migrated_checks.values()),
        },
        provenance_audit=audit,
        r4_blockers=blockers,
        provenance=prov.as_dict(),
        all_passed=bool(platform_rec.all_passed),
    )

    out_path = output_dir / "platform_soak.json"
    out_path.write_text(json.dumps(report.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    # Also emit a host-keyed shard for aggregation
    shard = output_dir / f"platform_soak__{platform_rec.host_id.replace('|', '_').replace(' ', '_')}.json"
    shard.write_text(json.dumps(report.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    finalize_experiment_provenance(prov, artifact_paths=[out_path, shard, bundle_path])
    report.provenance = prov.as_dict()
    out_path.write_text(json.dumps(report.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def aggregate_platform_soaks(
    reports: Sequence[dict[str, Any] | PlatformSoakReport],
) -> dict[str, Any]:
    """Merge multi-host soak reports; flag digest mismatches across hosts.

    Distinguishes ``host_kind=real`` from ``host_kind=synthetic``. Only real
    hosts count toward the R4 ≥2-host gate. Never sets ``promotion_claim``.
    """

    rows: list[dict[str, Any]] = []
    for r in reports:
        rows.append(r.as_dict() if isinstance(r, PlatformSoakReport) else dict(r))

    digests: dict[str, set[str]] = {}
    bundle_hashes: dict[str, set[str]] = {}
    hosts: list[str] = []
    real_hosts: list[str] = []
    synthetic_hosts: list[str] = []
    for row in rows:
        plat = row.get("platform") or {}
        hid = str(plat.get("host_id") or "unknown")
        hosts.append(hid)
        kind = str(plat.get("host_kind") or (plat.get("extras") or {}).get("host_kind") or "real")
        if kind == "synthetic" or bool((plat.get("extras") or {}).get("synthetic_fixture")):
            synthetic_hosts.append(hid)
            kind = "synthetic"
        else:
            real_hosts.append(hid)
            kind = "real"
        # Normalize for downstream consumers
        plat = dict(plat)
        plat["host_kind"] = kind
        row["platform"] = plat
        sealed = plat.get("sealed_corrected_action_digest")
        bhash = plat.get("bundle_sha256")
        if sealed:
            digests.setdefault("sealed_corrected_action_digest", set()).add(str(sealed))
        if bhash:
            bundle_hashes.setdefault("bundle_sha256", set()).add(str(bhash))

    mismatches: list[str] = []
    sealed_mismatches: list[str] = []
    for key, vals in digests.items():
        if len(vals) > 1:
            msg = f"{key} mismatch across hosts: {sorted(vals)}"
            mismatches.append(msg)
            sealed_mismatches.append(msg)
    bundle_hash_notes: list[str] = []
    for key, vals in bundle_hashes.items():
        if len(vals) > 1:
            # Bundle SHA includes host-local provenance paths; divergence is expected
            # across OS/hosts when sealed corrected-action digests still agree.
            note = (
                f"{key} differs across hosts (informational; does not alone block "
                f"r4_multi_host_gate_ready when sealed digests agree): {sorted(vals)}"
            )
            mismatches.append(note)
            bundle_hash_notes.append(note)

    n_hosts = len(set(hosts))
    n_real = len(set(real_hosts))
    n_synth = len(set(synthetic_hosts))
    blockers = [
        "Governed hash policy integration with production release tooling not wired.",
        "Assurance levels L0–L4 must not be overclaimed as universal safety guarantees.",
    ]
    if n_real < 2:
        blockers.insert(
            0,
            "Need independent soak evidence from >=2 distinct **real** hosts/OS/Python "
            "environments before R4 multi-environment gate can be considered "
            f"(n_real_hosts={n_real}, n_synthetic_hosts={n_synth}).",
        )
    if n_synth > 0:
        blockers.append(
            "Aggregate includes synthetic host(s); synthetic ≠ real multi-host evidence."
        )
    if sealed_mismatches:
        blockers.append(
            "Sealed corrected-action digest mismatch across real hosts must be "
            "investigated before treating multi-host evidence as ready."
        )

    # Evidence-readiness: ≥2 real hosts, no synthetic hosts, sealed digests agree.
    # Bundle SHA divergence alone does not block (host-local provenance differs).
    gate_ready = n_real >= 2 and n_synth == 0 and not sealed_mismatches

    return {
        "schema_id": AGGREGATE_SCHEMA_ID,
        "corpus_version": CORPUS_VERSION,
        "n_reports": len(rows),
        "n_distinct_hosts": n_hosts,
        "n_real_hosts": n_real,
        "n_synthetic_hosts": n_synth,
        "hosts": hosts,
        "real_hosts": real_hosts,
        "synthetic_hosts": synthetic_hosts,
        "digest_mismatches": mismatches,
        "sealed_digest_mismatches": sealed_mismatches,
        "bundle_hash_notes": bundle_hash_notes,
        "all_hosts_passed": all(bool(r.get("all_passed")) for r in rows) if rows else False,
        "r4_blockers": blockers,
        "r4_multi_host_gate_ready": gate_ready,
        "promotion_claim": False,
        "reports": rows,
        "note": (
            "Aggregation distinguishes real vs synthetic hosts. "
            "r4_multi_host_gate_ready is evidence-readiness only — never a production claim. "
            "Sealed corrected-action digests must agree across real hosts; bundle SHA may "
            "differ due to host-local provenance. Unexplained sealed mismatches must be "
            "investigated before governed promotion. Not a production R4 pass "
            "(governed-hash release wiring still required)."
        ),
    }


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

    parser = argparse.ArgumentParser(description="R4 platform matrix soak")
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
        "--aggregate",
        nargs="*",
        type=Path,
        default=None,
        help="Optional list of platform_soak JSON paths to aggregate",
    )
    args = parser.parse_args()
    if args.aggregate is not None and len(args.aggregate) > 0:
        reports = load_soak_reports(list(args.aggregate))
        agg = aggregate_platform_soaks(reports)
        out = args.output_dir
        out.mkdir(parents=True, exist_ok=True)
        path = out / "platform_soak_aggregate.json"
        path.write_text(json.dumps(agg, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(
            f"aggregate hosts={agg['n_distinct_hosts']} "
            f"real={agg['n_real_hosts']} synthetic={agg['n_synthetic_hosts']} "
            f"mismatches={len(agg['digest_mismatches'])} "
            f"r4_ready={agg['r4_multi_host_gate_ready']} promotion_claim={agg['promotion_claim']}"
        )
        print(f"wrote {path}")
        return
    report = run_platform_soak(
        output_dir=args.output_dir,
        host_id=args.host_id,
        host_kind=args.host_kind,
    )
    print(
        f"platform soak all_passed={report.all_passed} "
        f"host={report.platform.host_id if report.platform else None} "
        f"host_kind={report.platform.host_kind if report.platform else None}"
    )

if __name__ == "__main__":
    main()
