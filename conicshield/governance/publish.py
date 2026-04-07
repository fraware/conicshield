from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class PublishError(RuntimeError):
    pass


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _append_history_entry(family_id: str, entry: dict[str, Any]) -> None:
    history_path = Path("benchmarks") / "releases" / family_id / "HISTORY.json"
    history = _load_json(history_path)
    history.setdefault("entries", []).append(entry)
    _write_json(history_path, history)


def publish_from_governance_status(*, run_dir: str | Path, reason: str) -> None:
    run_dir = Path(run_dir)
    status_path = run_dir / "governance_status.json"
    if not status_path.exists():
        raise PublishError("Missing governance_status.json")
    decision_record = run_dir / "governance_decision.md"
    if not decision_record.exists():
        raise PublishError("Missing governance_decision.md")

    status = _load_json(status_path)
    family_id = str(status["family_id"])
    run_id = str(status["run_id"])
    task_contract_version = str(status["task_contract_version"])
    fixture_version = str(status["fixture_version"])
    state = str(status["state"])
    artifact_gate = str(status["artifact_gate"])
    parity_gate = str(status["parity_gate"])
    promotion_gate = str(status["promotion_gate"])
    review_locked = bool(status["review_locked"])
    publishable_arms = list(status["publishable_arms"])

    if state != "review-locked":
        raise PublishError(f"Run is not publishable: governance state is {state!r}, expected 'review-locked'")
    if artifact_gate != "green":
        raise PublishError("Run is not publishable: artifact_gate is not green")
    if promotion_gate != "green":
        raise PublishError("Run is not publishable: promotion_gate is not green")
    if not review_locked:
        raise PublishError("Run is not publishable: review_locked is false")
    if "shielded-native-moreau" in publishable_arms and parity_gate != "green":
        raise PublishError("Run is not publishable: native arm present but parity_gate is not green")

    current_path = Path("benchmarks") / "releases" / family_id / "CURRENT.json"
    current = _load_json(current_path)
    previous_run_id = current.get("current_run_id")

    published_at = datetime.now(UTC).isoformat()
    new_current = {
        "family_id": family_id,
        "task_contract_version": task_contract_version,
        "fixture_version": fixture_version,
        "current_run_id": run_id,
        "state": "published",
        "publishable_arms": publishable_arms,
        "artifact_gate": artifact_gate,
        "parity_gate": parity_gate,
        "promotion_gate": promotion_gate,
        "published_at_utc": published_at,
        "notes": reason,
    }
    _write_json(current_path, new_current)

    if previous_run_id is not None:
        _append_history_entry(
            family_id,
            {
                "run_id": previous_run_id,
                "status": "deprecated",
                "deprecated_at_utc": published_at,
                "reason": f"Superseded by {run_id}",
            },
        )

    _append_history_entry(
        family_id,
        {
            "run_id": run_id,
            "status": "published",
            "published_at_utc": published_at,
            "reason": reason,
        },
    )

    registry_path = Path("benchmarks") / "registry.json"
    registry = _load_json(registry_path)
    for fam in registry.get("benchmark_families", []):
        if fam["family_id"] == family_id:
            fam["current_run_id"] = run_id
            fam["published_at_utc"] = published_at
            break
    _write_json(registry_path, registry)

    published_status = dict(status)
    published_status["state"] = "published"
    _write_json(run_dir / "governance_status.json", published_status)
