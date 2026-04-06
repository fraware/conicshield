from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any

from conicshield.artifacts.validator import validate_run_bundle
from conicshield.governance.family_manifest import validate_family_manifest
from conicshield.governance.release_validator import validate_release_directory


@dataclass(slots=True)
class AuditIssue:
    level: str
    scope: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"level": self.level, "scope": self.scope, "message": self.message}


@dataclass(slots=True)
class AuditReport:
    ok: bool
    families_checked: int
    runs_checked: int
    issues: list[AuditIssue] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "families_checked": self.families_checked,
            "runs_checked": self.runs_checked,
            "issues": [issue.as_dict() for issue in self.issues],
        }


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _run_dir(run_id: str) -> Path:
    return Path("benchmarks") / "runs" / run_id


def _release_dir(family_id: str) -> Path:
    return Path("benchmarks") / "releases" / family_id


def _governance_status_path(run_id: str) -> Path:
    return _run_dir(run_id) / "governance_status.json"


def _append_issue(issues: list[AuditIssue], level: str, scope: str, message: str) -> None:
    issues.append(AuditIssue(level=level, scope=scope, message=message))


def _check_file_exists(path: Path, issues: list[AuditIssue], *, scope: str) -> bool:
    if not path.exists():
        _append_issue(issues, "error", scope, f"Missing file: {path}")
        return False
    return True


def _validate_run_bundle_safe(run_id: str, issues: list[AuditIssue]) -> bool:
    run_dir = _run_dir(run_id)
    try:
        validate_run_bundle(run_dir)
        return True
    except Exception as exc:
        _append_issue(issues, "error", f"run:{run_id}", f"Run bundle validation failed: {exc}")
        return False


def _validate_release_dir_safe(family_id: str, issues: list[AuditIssue]) -> bool:
    try:
        validate_release_directory(family_id)
        return True
    except Exception as exc:
        _append_issue(issues, "error", f"family:{family_id}", f"Release directory validation failed: {exc}")
        return False


def _validate_family_manifest_safe(family_id: str, issues: list[AuditIssue]) -> dict[str, Any] | None:
    try:
        return validate_family_manifest(family_id)
    except Exception as exc:
        _append_issue(issues, "error", f"family:{family_id}", f"Family manifest validation failed: {exc}")
        return None


def _check_registry_release_consistency(*, family_entry: dict[str, Any], current_payload: dict[str, Any], manifest: dict[str, Any] | None, issues: list[AuditIssue]) -> None:
    family_id = str(family_entry["family_id"])
    if family_entry.get("current_run_id") != current_payload.get("current_run_id"):
        _append_issue(issues, "error", f"family:{family_id}", "registry current_run_id does not match CURRENT.json current_run_id")
    if family_entry.get("task_contract_version") != current_payload.get("task_contract_version"):
        _append_issue(issues, "error", f"family:{family_id}", "registry task_contract_version does not match CURRENT.json")
    if family_entry.get("current_fixture_version") != current_payload.get("fixture_version"):
        _append_issue(issues, "error", f"family:{family_id}", "registry current_fixture_version does not match CURRENT.json")
    if manifest is not None:
        if manifest.get("task_contract_version") != current_payload.get("task_contract_version"):
            _append_issue(issues, "error", f"family:{family_id}", "FAMILY_MANIFEST task_contract_version does not match CURRENT.json")
        if manifest["fixture_lineage"]["current_fixture_version"] != current_payload.get("fixture_version"):
            _append_issue(issues, "error", f"family:{family_id}", "FAMILY_MANIFEST fixture version does not match CURRENT.json")


def _check_history_consistency(*, family_id: str, history_payload: dict[str, Any], current_payload: dict[str, Any], issues: list[AuditIssue]) -> None:
    entries = history_payload.get("entries", [])
    current_run_id = current_payload.get("current_run_id")

    if current_run_id is not None:
        if not any(e.get("run_id") == current_run_id and e.get("status") == "published" for e in entries):
            _append_issue(issues, "warning", f"family:{family_id}", "CURRENT.json current_run_id not present as published entry in HISTORY.json")

    for entry in entries:
        run_id = entry.get("run_id")
        if run_id is None:
            _append_issue(issues, "error", f"family:{family_id}", "HISTORY.json contains entry without run_id")
            continue
        if not _run_dir(str(run_id)).exists():
            _append_issue(issues, "error", f"family:{family_id}", f"HISTORY.json references missing run bundle: {run_id}")


def _check_current_run_governance_status(*, family_id: str, current_payload: dict[str, Any], issues: list[AuditIssue]) -> int:
    current_run_id = current_payload.get("current_run_id")
    if current_run_id is None:
        return 0
    path = _governance_status_path(str(current_run_id))
    if not path.exists():
        _append_issue(issues, "error", f"family:{family_id}", f"Current run missing governance_status.json: {current_run_id}")
        return 1
    status = _load_json(path)
    if status.get("family_id") != family_id:
        _append_issue(issues, "error", f"run:{current_run_id}", "governance_status family_id does not match release family_id")
    if status.get("artifact_gate") != "green":
        _append_issue(issues, "error", f"run:{current_run_id}", "Current published run artifact_gate is not green")
    if "shielded-native-moreau" in status.get("publishable_arms", []):
        if status.get("parity_gate") != "green":
            _append_issue(issues, "error", f"run:{current_run_id}", "Native arm is publishable but parity_gate is not green")
    return 1


def audit_benchmark_tree(*, family_id: str | None = None) -> AuditReport:
    issues: list[AuditIssue] = []
    families_checked = 0
    runs_checked = 0
    registry_path = Path("benchmarks") / "registry.json"
    if not registry_path.exists():
        return AuditReport(False, 0, 0, [AuditIssue("error", "registry", "Missing benchmarks/registry.json")])

    registry = _load_json(registry_path)
    families = list(registry.get("benchmark_families", []))
    if family_id is not None:
        families = [f for f in families if str(f.get("family_id")) == family_id]
        if not families:
            return AuditReport(False, 0, 0, [AuditIssue("error", "registry", f"Family {family_id!r} not found in registry")])

    seen_family_ids: set[str] = set()
    for fam in families:
        fid = str(fam["family_id"])
        families_checked += 1
        if fid in seen_family_ids:
            _append_issue(issues, "error", "registry", f"Duplicate family_id in registry: {fid}")
            continue
        seen_family_ids.add(fid)
        release_dir = _release_dir(fid)
        if not release_dir.exists():
            _append_issue(issues, "error", f"family:{fid}", f"Missing release directory: {release_dir}")
            continue

        _validate_release_dir_safe(fid, issues)
        manifest = _validate_family_manifest_safe(fid, issues)

        current_path = release_dir / "CURRENT.json"
        history_path = release_dir / "HISTORY.json"
        if not (_check_file_exists(current_path, issues, scope=f"family:{fid}") and _check_file_exists(history_path, issues, scope=f"family:{fid}")):
            continue

        current_payload = _load_json(current_path)
        history_payload = _load_json(history_path)

        _check_registry_release_consistency(family_entry=fam, current_payload=current_payload, manifest=manifest, issues=issues)
        _check_history_consistency(family_id=fid, history_payload=history_payload, current_payload=current_payload, issues=issues)

        current_run_id = current_payload.get("current_run_id")
        if current_run_id is not None:
            if _validate_run_bundle_safe(str(current_run_id), issues):
                runs_checked += 1
            runs_checked += _check_current_run_governance_status(family_id=fid, current_payload=current_payload, issues=issues)

    ok = not any(issue.level == "error" for issue in issues)
    return AuditReport(ok=ok, families_checked=families_checked, runs_checked=runs_checked, issues=issues)
