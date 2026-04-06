from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from conicshield.governance.family_bump import initialize_new_family, next_family_version
from conicshield.governance.family_policy import decide_family_compatibility
from conicshield.governance.publish import publish_from_governance_status


class ReleaseError(RuntimeError):
    pass


@dataclass(slots=True)
class ReleaseDecision:
    mode: str
    family_id: str
    target_family_id: str
    requires_family_bump: bool
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "family_id": self.family_id,
            "target_family_id": self.target_family_id,
            "requires_family_bump": self.requires_family_bump,
            "reason": self.reason,
        }


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _current_release_path(family_id: str) -> Path:
    return Path("benchmarks") / "releases" / family_id / "CURRENT.json"


def _run_status_path(run_dir: Path) -> Path:
    return run_dir / "governance_status.json"


def _family_bump_note_path(run_dir: Path) -> Path:
    return run_dir / "FAMILY_BUMP_NOTE.md"


def _release_decision_record_path(run_dir: Path) -> Path:
    return run_dir / "release_decision.json"


def _validate_publishable_status(status: dict[str, Any]) -> None:
    if str(status["state"]) != "review-locked":
        raise ReleaseError("Run is not releasable: governance state is not review-locked")
    if str(status["artifact_gate"]) != "green":
        raise ReleaseError("Run is not releasable: artifact_gate is not green")
    if str(status["promotion_gate"]) != "green":
        raise ReleaseError("Run is not releasable: promotion_gate is not green")
    if not bool(status["review_locked"]):
        raise ReleaseError("Run is not releasable: review_locked is false")


def decide_release_mode(*, run_dir: str | Path, family_id: str) -> ReleaseDecision:
    run_dir = Path(run_dir)
    status = _load_json(_run_status_path(run_dir))
    _validate_publishable_status(status)

    current_path = _current_release_path(family_id)
    if not current_path.exists():
        return ReleaseDecision("same-family", family_id, family_id, False, "No current family release exists yet.")

    current = _load_json(current_path)
    current_run_id = current.get("current_run_id")
    if current_run_id is None:
        return ReleaseDecision("same-family", family_id, family_id, False, "Family exists but has no published run yet.")

    current_config = _load_json(Path("benchmarks") / "runs" / str(current_run_id) / "config.json")
    candidate_config = _load_json(run_dir / "config.json")
    compatibility = decide_family_compatibility(
        family_id=family_id,
        current_config=current_config,
        candidate_config=candidate_config,
    )
    if compatibility.same_family_allowed:
        return ReleaseDecision("same-family", family_id, family_id, False, compatibility.reason)

    new_family = next_family_version(family_id)
    return ReleaseDecision("new-family", family_id, new_family, True, compatibility.reason)


def release_run(*, run_dir: str | Path, family_id: str, reason: str, allow_family_bump: bool = False) -> ReleaseDecision:
    run_dir = Path(run_dir)
    status = _load_json(_run_status_path(run_dir))
    _validate_publishable_status(status)

    decision = decide_release_mode(run_dir=run_dir, family_id=family_id)

    if decision.requires_family_bump:
        if not allow_family_bump:
            raise ReleaseError("Release requires a new benchmark family version. Re-run with allow_family_bump=True.")
        if not _family_bump_note_path(run_dir).exists():
            raise ReleaseError("Missing FAMILY_BUMP_NOTE.md for family bump release")
        initialize_new_family(
            current_family_id=family_id,
            new_family_id=decision.target_family_id,
            task_contract_version=str(status["task_contract_version"]),
            fixture_version=str(status["fixture_version"]),
        )
        status = dict(status)
        status["family_id"] = decision.target_family_id
        _write_json(_run_status_path(run_dir), status)

    publish_from_governance_status(run_dir=run_dir, reason=reason)

    release_record = {
        "run_id": status["run_id"],
        "source_family_id": family_id,
        "target_family_id": decision.target_family_id,
        "mode": decision.mode,
        "requires_family_bump": decision.requires_family_bump,
        "reason": reason,
        "compatibility_reason": decision.reason,
    }
    _write_json(_release_decision_record_path(run_dir), release_record)
    return decision
