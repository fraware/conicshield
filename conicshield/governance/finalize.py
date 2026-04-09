from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from conicshield.artifacts.validator import validate_run_bundle
from conicshield.governance.family_policy import decide_family_compatibility
from conicshield.governance.policy import GovernanceError, assert_same_family_replacement

# Keys copied from governance_status into CURRENT.json when syncing metadata for an already-published run.
_CURRENT_SYNC_KEYS = ("artifact_gate", "parity_gate", "promotion_gate", "publishable_arms")
from conicshield.parity.fixture_policy import validate_fixture_policy


@dataclass(slots=True)
class GateResult:
    status: str
    detail: str

    def as_dict(self) -> dict[str, str]:
        return {"status": self.status, "detail": self.detail}


@dataclass(slots=True)
class FinalizationInputs:
    run_dir: Path
    family_id: str
    task_contract_version: str
    fixture_version: str
    reference_fixture_dir: Path | None
    parity_summary_path: Path | None
    current_release_path: Path | None


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _summary_index(summary_payload: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {row["label"]: row for row in summary_payload}


def _has_native_arm(summary_by_label: dict[str, dict[str, Any]]) -> bool:
    return "shielded-native-moreau" in summary_by_label


def _compute_publishable_arms(
    *,
    summary_by_label: dict[str, dict[str, Any]],
    artifact_gate: GateResult,
    parity_gate: GateResult,
    promotion_gate: GateResult,
) -> list[str]:
    if artifact_gate.status != "green":
        return []

    publishable = [
        "baseline-unshielded",
        "shielded-rules-only",
        "shielded-rules-plus-geometry",
    ]

    if (
        "shielded-native-moreau" in summary_by_label
        and parity_gate.status == "green"
        and promotion_gate.status == "green"
    ):
        publishable.append("shielded-native-moreau")

    return publishable


def _artifact_gate(run_dir: Path) -> GateResult:
    try:
        validate_run_bundle(run_dir)
        return GateResult("green", "Run bundle validated successfully.")
    except Exception as exc:
        return GateResult("red", f"Artifact validation failed: {exc}")


def _fixture_gate(reference_fixture_dir: Path | None) -> GateResult:
    if reference_fixture_dir is None:
        return GateResult("unknown", "No reference fixture provided.")
    try:
        validate_fixture_policy(reference_fixture_dir)
        return GateResult("green", "Fixture policy validated successfully.")
    except Exception as exc:
        return GateResult("red", f"Fixture policy validation failed: {exc}")


def _parity_thresholds_from_summary_payload(payload: dict[str, Any]) -> GateResult:
    try:
        action_match_rate = float(payload["action_match_rate"])
        active_constraints_match_rate = float(payload["active_constraints_match_rate"])
        max_corrected_linf = float(payload["max_corrected_linf"])
        p95_corrected_linf = float(payload["p95_corrected_linf"])
        max_corrected_l2 = float(payload["max_corrected_l2"])
    except Exception as exc:
        return GateResult("red", f"Malformed parity summary: {exc}")

    failures: list[str] = []
    if action_match_rate < 1.0:
        failures.append(f"action_match_rate={action_match_rate:.8f} < 1.0")
    if active_constraints_match_rate < 0.999:
        failures.append(f"active_constraints_match_rate={active_constraints_match_rate:.8f} < 0.999")
    if max_corrected_linf > 1e-5:
        failures.append(f"max_corrected_linf={max_corrected_linf:.3e} > 1e-5")
    if p95_corrected_linf > 1e-6:
        failures.append(f"p95_corrected_linf={p95_corrected_linf:.3e} > 1e-6")
    if max_corrected_l2 > 1e-5:
        failures.append(f"max_corrected_l2={max_corrected_l2:.3e} > 1e-5")

    if failures:
        return GateResult("red", "Parity gate failed: " + "; ".join(failures))
    return GateResult("green", "Parity thresholds satisfied (parity_summary.json).")


def _parity_gate(*, has_native_arm: bool, parity_summary_path: Path | None) -> GateResult:
    """Evaluate native-vs-reference parity from ``parity_summary.json`` when provided.

    Offline ``conicshield.parity.cli`` replay against the frozen fixture can prove parity even when
    the benchmark ``summary.json`` does not include a ``shielded-native-moreau`` row (reference-only run).
    """
    if parity_summary_path is not None:
        if not parity_summary_path.exists():
            return GateResult("red", f"parity_summary_path not found: {parity_summary_path}")
        try:
            payload = _load_json(parity_summary_path)
        except Exception as exc:
            return GateResult("red", f"Could not read parity summary: {exc}")
        return _parity_thresholds_from_summary_payload(payload)

    if has_native_arm:
        return GateResult(
            "red",
            "shielded-native-moreau is present in summary.json but parity_summary_path was not provided.",
        )
    return GateResult(
        "unknown",
        "No parity_summary_path; pass --parity-summary-path from conicshield.parity.cli output.",
    )


def sync_current_release_from_status(*, current_release_path: Path, status: dict[str, Any]) -> None:
    """Refresh gate fields on CURRENT.json for the same ``current_run_id`` as ``status['run_id']``.

    Does not append HISTORY or change ``benchmarks/registry.json`` (unlike full publish). Use after
    ``finalize_run`` when the release is already published but gates were recomputed (e.g. parity evidence added).
    """
    if not current_release_path.exists():
        raise GovernanceError(f"Missing current release file: {current_release_path}")
    current = _load_json(current_release_path)
    run_id = str(status["run_id"])
    if str(current.get("current_run_id")) != run_id:
        raise GovernanceError(
            f"CURRENT.json current_run_id {current.get('current_run_id')!r} does not match finalized run {run_id!r}"
        )
    for key in _CURRENT_SYNC_KEYS:
        current[key] = status[key]
    _write_json(current_release_path, current)


def _promotion_gate(summary_by_label: dict[str, dict[str, Any]]) -> GateResult:
    required = ["baseline-unshielded", "shielded-rules-only", "shielded-rules-plus-geometry"]
    missing = [label for label in required if label not in summary_by_label]
    if missing:
        return GateResult("red", f"Missing required benchmark arms: {missing}")

    baseline = summary_by_label["baseline-unshielded"]
    rules = summary_by_label["shielded-rules-only"]
    geometry = summary_by_label["shielded-rules-plus-geometry"]
    failures: list[str] = []

    if float(rules["rule_violation_rate"]) > float(baseline["rule_violation_rate"]):
        failures.append("rules-only regresses rule_violation_rate vs baseline")

    rules_retention = rules.get("reward_retention_vs_baseline")
    if rules_retention is not None and float(rules_retention) < 0.90:
        failures.append("rules-only reward retention < 0.90")

    if float(geometry["matched_action_rate"]) < float(rules["matched_action_rate"]):
        failures.append("geometry shield regresses matched_action_rate vs rules-only")

    if float(geometry["solve_failure_rate"]) > 0.0:
        failures.append("geometry shield has nonzero solve_failure_rate")

    native = summary_by_label.get("shielded-native-moreau")
    if native is not None:
        native_retention = native.get("reward_retention_vs_baseline")
        ref_retention = geometry.get("reward_retention_vs_baseline")
        if native_retention is not None and ref_retention is not None and float(ref_retention) != 0.0:
            rel = float(native_retention) / float(ref_retention)
            if rel < 0.995:
                failures.append("native reward retention < 0.995 of reference shield")
        if float(native["rule_violation_rate"]) > float(geometry["rule_violation_rate"]):
            failures.append("native regresses rule_violation_rate vs geometry reference")
        if float(native["matched_action_rate"]) < float(geometry["matched_action_rate"]):
            failures.append("native regresses matched_action_rate vs geometry reference")
        if float(native["solve_failure_rate"]) > 0.0:
            failures.append("native solve_failure_rate > 0")
        ref_p95 = float(geometry["solve_time_p95_ms"])
        native_p95 = float(native["solve_time_p95_ms"])
        if ref_p95 > 0 and native_p95 > ref_p95:
            failures.append("native p95 solve latency worse than geometry reference")

    if failures:
        return GateResult("red", "Promotion gate failed: " + "; ".join(failures))
    return GateResult("green", "Promotion thresholds satisfied.")


def _review_lock_gate(
    *,
    current_release_path: Path | None,
    candidate_config_path: Path,
    family_id: str,
    task_contract_version: str,
) -> GateResult:
    if current_release_path is None or not current_release_path.exists():
        return GateResult("green", "No current published release found. Run is review-lock compatible by default.")
    try:
        current = _load_json(current_release_path)
        current_family_id = str(current["family_id"])
        current_task_contract_version = str(current["task_contract_version"])
        assert_same_family_replacement(
            current_family_id=current_family_id,
            candidate_family_id=family_id,
            current_task_contract_version=current_task_contract_version,
            candidate_task_contract_version=task_contract_version,
        )
        current_run_id = current.get("current_run_id")
        if current_run_id is None:
            return GateResult("green", "No current run published yet; family compatibility vacuously holds.")
        current_config_path = Path("benchmarks") / "runs" / str(current_run_id) / "config.json"
        candidate_config = _load_json(candidate_config_path)
        current_config = _load_json(current_config_path)
        decision = decide_family_compatibility(
            family_id=family_id,
            current_config=current_config,
            candidate_config=candidate_config,
        )
        if not decision.same_family_allowed:
            return GateResult("red", f"Family compatibility failed: {decision.reason}")
        return GateResult("green", decision.reason)
    except GovernanceError as exc:
        return GateResult("red", f"Family/version incompatibility: {exc}")
    except Exception as exc:
        return GateResult("red", f"Could not evaluate review-lock gate: {exc}")


def finalize_run(inputs: FinalizationInputs) -> dict[str, Any]:
    summary = _load_json(inputs.run_dir / "summary.json")
    summary_by_label = _summary_index(summary)

    artifact_gate = _artifact_gate(inputs.run_dir)
    fixture_gate = _fixture_gate(inputs.reference_fixture_dir)
    parity_gate = _parity_gate(
        has_native_arm=_has_native_arm(summary_by_label), parity_summary_path=inputs.parity_summary_path
    )
    promotion_gate = _promotion_gate(summary_by_label)
    review_lock_gate = _review_lock_gate(
        current_release_path=inputs.current_release_path,
        candidate_config_path=inputs.run_dir / "config.json",
        family_id=inputs.family_id,
        task_contract_version=inputs.task_contract_version,
    )

    review_locked = artifact_gate.status == "green" and review_lock_gate.status == "green"
    publishable_arms = _compute_publishable_arms(
        summary_by_label=summary_by_label,
        artifact_gate=artifact_gate,
        parity_gate=parity_gate,
        promotion_gate=promotion_gate,
    )

    if artifact_gate.status != "green":
        state = "experimental"
    elif not review_locked:
        state = "candidate"
    elif promotion_gate.status == "green":
        state = "review-locked"
    else:
        state = "candidate"

    status = {
        "run_id": inputs.run_dir.name,
        "family_id": inputs.family_id,
        "task_contract_version": inputs.task_contract_version,
        "fixture_version": inputs.fixture_version,
        "state": state,
        "artifact_gate": artifact_gate.status,
        "fixture_gate": fixture_gate.status,
        "parity_gate": parity_gate.status,
        "promotion_gate": promotion_gate.status,
        "review_locked": review_locked,
        "publishable_arms": publishable_arms,
        "gate_details": {
            "artifact_gate": artifact_gate.as_dict(),
            "fixture_gate": fixture_gate.as_dict(),
            "parity_gate": parity_gate.as_dict(),
            "promotion_gate": promotion_gate.as_dict(),
            "review_lock_gate": review_lock_gate.as_dict(),
        },
    }

    _write_json(inputs.run_dir / "governance_status.json", status)
    return status
