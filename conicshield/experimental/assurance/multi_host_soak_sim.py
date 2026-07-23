"""Local multi-host soak simulation with synthetic second-host fixtures (R4).

Simulates aggregation of independent soak reports with controlled digest
match/mismatch cases. Does **not** replace real multi-host evidence for
production promotion.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from conicshield.experimental.assurance.governed_hash_policy import (
    check_governed_hashes,
    default_governed_hash_policy,
)
from conicshield.experimental.assurance.platform_soak import (
    AGGREGATE_SCHEMA_ID,
    aggregate_platform_soaks,
    run_platform_soak,
)
from conicshield.experimental.corpus.paths import CORPUS_VERSION

MULTI_HOST_SIM_SCHEMA_ID = "research.multi_host_soak_simulation.v0"
DigestMode = Literal["match", "mismatch"]


@dataclass(slots=True)
class MultiHostSoakSimulation:
    schema_id: str = MULTI_HOST_SIM_SCHEMA_ID
    corpus_version: str = CORPUS_VERSION
    primary_host_id: str = ""
    synthetic_host_id: str = ""
    digest_mode: DigestMode = "match"
    aggregate: dict[str, Any] = field(default_factory=dict)
    governed_hash_check: dict[str, Any] = field(default_factory=dict)
    r4_blockers_remaining: list[str] = field(default_factory=list)
    is_synthetic: bool = True
    promotion_claim: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_id": self.schema_id,
            "corpus_version": self.corpus_version,
            "primary_host_id": self.primary_host_id,
            "synthetic_host_id": self.synthetic_host_id,
            "digest_mode": self.digest_mode,
            "aggregate": dict(self.aggregate),
            "governed_hash_check": dict(self.governed_hash_check),
            "r4_blockers_remaining": list(self.r4_blockers_remaining),
            "is_synthetic": self.is_synthetic,
            "promotion_claim": self.promotion_claim,
            "note": (
                "Synthetic second-host fixture for local aggregation QA only. "
                "Does not satisfy the real multi-environment R4 soak gate."
            ),
        }


def synthesize_second_host_report(
    primary: dict[str, Any],
    *,
    host_id: str = "synthetic-host-b|ci-fixture",
    digest_mode: DigestMode = "match",
) -> dict[str, Any]:
    """Clone a soak report as a second host with controlled digest agreement."""

    syn = copy.deepcopy(primary)
    plat = dict(syn.get("platform") or {})
    sealed = plat.get("sealed_corrected_action_digest") or "missing"
    bundle = plat.get("bundle_sha256") or "missing"
    if digest_mode == "mismatch":
        sealed = f"mismatched-{sealed}"
        bundle = f"mismatched-{bundle}"
    plat.update(
        {
            "host_id": host_id,
            "operating_system": "synthetic-os",
            "python_version": "3.12.synthetic",
            "cpu_info": "synthetic-cpu",
            "gpu_info": None,
            "sealed_corrected_action_digest": sealed,
            "bundle_sha256": bundle,
            "host_kind": "synthetic",
            "extras": {
                **dict(plat.get("extras") or {}),
                "synthetic_fixture": True,
                "digest_mode": digest_mode,
                "host_kind": "synthetic",
                "counts_toward_r4_multi_host_gate": False,
            },
        }
    )
    syn["platform"] = plat
    syn["r4_blockers"] = list(syn.get("r4_blockers") or []) + [
        "This report is a synthetic second-host fixture (not an independent machine)."
    ]
    syn["note"] = "SYNTHETIC_FIXTURE: not independent multi-host evidence"
    return syn


def remaining_r4_blockers(*, n_real_hosts: int, digest_mismatches: list[str]) -> list[str]:
    blockers = [
        "Governed hash policy not integrated with production release tooling.",
        "Assurance levels L0–L4 must not be overclaimed as universal safety guarantees.",
        "Synthetic multi-host simulation does not replace independent OS/Python/GPU soaks.",
    ]
    if n_real_hosts < 2:
        blockers.insert(
            0,
            "Need independent soak evidence from >=2 distinct real hosts "
            "(synthetic fixtures do not count toward the R4 multi-host gate).",
        )
    if digest_mismatches:
        blockers.append("Investigate unexplained sealed-digest mismatches before governed promotion.")
    return blockers


def run_multi_host_soak_simulation(
    *,
    output_dir: Path,
    digest_mode: DigestMode = "match",
    host_id: str | None = None,
    exact_command: str = "python -m conicshield.experimental.assurance.multi_host_soak_sim",
) -> MultiHostSoakSimulation:
    """Run primary soak, synthesize second host, aggregate, apply research hash checks."""

    output_dir.mkdir(parents=True, exist_ok=True)
    primary_dir = output_dir / "primary"
    report = run_platform_soak(
        output_dir=primary_dir,
        host_id=host_id or "sim-host-a|local",
        exact_command=exact_command,
    )
    primary = report.as_dict()
    syn_host = "synthetic-host-b|ci-fixture"
    secondary = synthesize_second_host_report(primary, host_id=syn_host, digest_mode=digest_mode)
    (output_dir / "synthetic_second_host.json").write_text(
        json.dumps(secondary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    agg = aggregate_platform_soaks([primary, secondary])
    # Mark aggregation as synthetic-augmented
    agg = {
        **agg,
        "schema_id": AGGREGATE_SCHEMA_ID,
        "synthetic_second_host": True,
        "digest_mode": digest_mode,
        "n_real_hosts": 1,
        "n_synthetic_hosts": 1,
    }

    plat = primary.get("platform") or {}
    hash_check = check_governed_hashes(
        artifact_hashes=dict(plat.get("artifact_hashes") or {}),
        sealed_corrected_action_digest=plat.get("sealed_corrected_action_digest"),
        dirty_worktree=bool(plat.get("dirty_worktree")),
        peer_sealed_digests=[str((secondary.get("platform") or {}).get("sealed_corrected_action_digest") or "")],
        policy=default_governed_hash_policy(),
    )

    blockers = remaining_r4_blockers(
        n_real_hosts=1,
        digest_mismatches=list(agg.get("digest_mismatches") or []),
    )
    sim = MultiHostSoakSimulation(
        corpus_version=str(primary.get("corpus_version") or CORPUS_VERSION),
        primary_host_id=str(plat.get("host_id") or ""),
        synthetic_host_id=syn_host,
        digest_mode=digest_mode,
        aggregate=agg,
        governed_hash_check=hash_check.as_dict(),
        r4_blockers_remaining=blockers,
    )
    out = output_dir / "multi_host_soak_simulation.json"
    out.write_text(json.dumps(sim.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "platform_soak_aggregate.json").write_text(
        json.dumps(agg, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return sim


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="R4 multi-host soak simulation")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output/research/multi_host_soak_sim"),
    )
    parser.add_argument(
        "--digest-mode",
        choices=["match", "mismatch"],
        default="match",
    )
    parser.add_argument("--host-id", type=str, default=None)
    args = parser.parse_args()
    sim = run_multi_host_soak_simulation(
        output_dir=args.output_dir,
        digest_mode=args.digest_mode,  # type: ignore[arg-type]
        host_id=args.host_id,
    )
    print(
        f"multi-host sim mode={sim.digest_mode} "
        f"mismatches={len(sim.aggregate.get('digest_mismatches') or [])} "
        f"blockers={len(sim.r4_blockers_remaining)}"
    )


if __name__ == "__main__":
    main()
