from __future__ import annotations

import json
from pathlib import Path


def next_family_version(family_id: str) -> str:
    if "-v" not in family_id:
        raise ValueError(f"Family id has no version suffix: {family_id}")
    stem, suffix = family_id.rsplit("-v", 1)
    version = int(suffix)
    return f"{stem}-v{version + 1}"


def initialize_new_family(
    *,
    current_family_id: str,
    new_family_id: str,
    task_contract_version: str,
    fixture_version: str,
) -> None:
    registry_path = Path("benchmarks") / "registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry.setdefault("benchmark_families", []).append(
        {
            "family_id": new_family_id,
            "status": "active",
            "task_contract_version": task_contract_version,
            "current_fixture_version": fixture_version,
            "current_run_id": None,
            "published_at_utc": None,
            "history": [],
            "forked_from": current_family_id,
        }
    )
    registry_path.write_text(json.dumps(registry, indent=2), encoding="utf-8")

    release_dir = Path("benchmarks") / "releases" / new_family_id
    release_dir.mkdir(parents=True, exist_ok=True)

    (release_dir / "CURRENT.json").write_text(
        json.dumps(
            {
                "family_id": new_family_id,
                "task_contract_version": task_contract_version,
                "fixture_version": fixture_version,
                "current_run_id": None,
                "state": "uninitialized",
                "publishable_arms": [],
                "artifact_gate": "unknown",
                "parity_gate": "unknown",
                "promotion_gate": "unknown",
                "published_at_utc": None,
                "notes": f"Forked from {current_family_id}",
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    (release_dir / "HISTORY.json").write_text(
        json.dumps({"family_id": new_family_id, "entries": []}, indent=2),
        encoding="utf-8",
    )

    current_schema_path = Path("benchmarks") / "releases" / current_family_id / "FAMILY_MANIFEST.schema.json"
    if current_schema_path.exists():
        (release_dir / "FAMILY_MANIFEST.schema.json").write_text(
            current_schema_path.read_text(encoding="utf-8"), encoding="utf-8"
        )

    (release_dir / "FAMILY_MANIFEST.json").write_text(
        json.dumps(
            {
                "family_id": new_family_id,
                "family_version": new_family_id.rsplit("-v", 1)[-1],
                "benchmark_name": "ConicShield Transition-Bank Benchmark",
                "task_contract_version": task_contract_version,
                "fixture_lineage": {
                    "current_fixture_version": fixture_version,
                    "reference_arm_label": "shielded-rules-plus-geometry",
                    "reference_backend": "cvxpy_moreau",
                },
                "required_arms": [
                    "baseline-unshielded",
                    "shielded-rules-only",
                    "shielded-rules-plus-geometry",
                ],
                "reference_arm": "shielded-rules-plus-geometry",
                "native_parity_required": True,
                "same_family_replacement_rules": {
                    "action_space_must_match": True,
                    "state_contract_must_match": True,
                    "rule_choices_must_match": True,
                    "transition_bank_semantics_must_match": True,
                    "reference_arm_definition_must_match": True,
                },
                "fork_info": {
                    "forked_from_family_id": current_family_id,
                    "reason": "Family fork initiated through governed release orchestration",
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
