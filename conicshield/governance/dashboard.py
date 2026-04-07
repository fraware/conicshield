from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from conicshield.governance.audit import audit_benchmark_tree


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


@dataclass(slots=True)
class FamilyDashboardRow:
    family_id: str
    status: str
    task_contract_version: str | None
    fixture_version: str | None
    current_run_id: str | None
    published_at_utc: str | None
    current_state: str | None
    artifact_gate: str | None
    parity_gate: str | None
    promotion_gate: str | None
    native_endorsed: bool
    publishable_arms: list[str] = field(default_factory=list)
    notes: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "family_id": self.family_id,
            "status": self.status,
            "task_contract_version": self.task_contract_version,
            "fixture_version": self.fixture_version,
            "current_run_id": self.current_run_id,
            "published_at_utc": self.published_at_utc,
            "current_state": self.current_state,
            "artifact_gate": self.artifact_gate,
            "parity_gate": self.parity_gate,
            "promotion_gate": self.promotion_gate,
            "native_endorsed": self.native_endorsed,
            "publishable_arms": list(self.publishable_arms),
            "notes": self.notes,
        }


@dataclass(slots=True)
class GovernanceDashboard:
    generated_at_hint: str | None
    audit_ok: bool
    total_families: int
    total_current_runs: int
    total_native_endorsed: int
    audit_errors: int
    audit_warnings: int
    families: list[FamilyDashboardRow] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "generated_at_hint": self.generated_at_hint,
            "audit_ok": self.audit_ok,
            "total_families": self.total_families,
            "total_current_runs": self.total_current_runs,
            "total_native_endorsed": self.total_native_endorsed,
            "audit_errors": self.audit_errors,
            "audit_warnings": self.audit_warnings,
            "families": [f.as_dict() for f in self.families],
        }


def _current_payload_for_family(family_id: str) -> dict[str, Any]:
    current_path = Path("benchmarks") / "releases" / family_id / "CURRENT.json"
    if not current_path.exists():
        return {
            "current_run_id": None,
            "state": None,
            "artifact_gate": None,
            "parity_gate": None,
            "promotion_gate": None,
            "publishable_arms": [],
            "published_at_utc": None,
            "notes": "Missing CURRENT.json",
        }
    return cast(dict[str, Any], _load_json(current_path))


def build_governance_dashboard() -> GovernanceDashboard:
    registry_path = Path("benchmarks") / "registry.json"
    registry = _load_json(registry_path)
    audit = audit_benchmark_tree()
    families: list[FamilyDashboardRow] = []
    total_current_runs = 0
    total_native_endorsed = 0

    for fam in registry.get("benchmark_families", []):
        family_id = str(fam["family_id"])
        current = _current_payload_for_family(family_id)
        current_run_id = current.get("current_run_id")
        if current_run_id is not None:
            total_current_runs += 1
        publishable_arms = list(current.get("publishable_arms", []))
        native_endorsed = "shielded-native-moreau" in publishable_arms
        if native_endorsed:
            total_native_endorsed += 1

        families.append(
            FamilyDashboardRow(
                family_id=family_id,
                status=str(fam.get("status", "unknown")),
                task_contract_version=fam.get("task_contract_version"),
                fixture_version=fam.get("current_fixture_version"),
                current_run_id=current_run_id,
                published_at_utc=fam.get("published_at_utc"),
                current_state=current.get("state"),
                artifact_gate=current.get("artifact_gate"),
                parity_gate=current.get("parity_gate"),
                promotion_gate=current.get("promotion_gate"),
                native_endorsed=native_endorsed,
                publishable_arms=publishable_arms,
                notes=current.get("notes"),
            )
        )

    families.sort(key=lambda x: x.family_id)
    audit_errors = sum(1 for issue in audit.issues if issue.level == "error")
    audit_warnings = sum(1 for issue in audit.issues if issue.level == "warning")

    return GovernanceDashboard(
        generated_at_hint=None,
        audit_ok=audit.ok,
        total_families=len(families),
        total_current_runs=total_current_runs,
        total_native_endorsed=total_native_endorsed,
        audit_errors=audit_errors,
        audit_warnings=audit_warnings,
        families=families,
    )


def render_markdown_dashboard(dashboard: GovernanceDashboard) -> str:
    lines: list[str] = []
    lines.append("# Benchmark Governance Dashboard")
    lines.append("")
    lines.append("## Global Status")
    lines.append("")
    lines.append(f"- Audit OK: {'yes' if dashboard.audit_ok else 'no'}")
    lines.append(f"- Families: {dashboard.total_families}")
    lines.append(f"- Current published runs: {dashboard.total_current_runs}")
    lines.append(f"- Native-endorsed families: {dashboard.total_native_endorsed}")
    lines.append(f"- Audit errors: {dashboard.audit_errors}")
    lines.append(f"- Audit warnings: {dashboard.audit_warnings}")
    lines.append("")
    lines.append("## Families")
    lines.append("")
    lines.append(
        "| Family | Status | Current Run | Task Contract | Fixture | State | "
        "Artifact | Parity | Promotion | Native Endorsed |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for fam in dashboard.families:
        lines.append(
            "| "
            f"{fam.family_id} | {fam.status} | {fam.current_run_id or '-'} | "
            f"{fam.task_contract_version or '-'} | {fam.fixture_version or '-'} | "
            f"{fam.current_state or '-'} | {fam.artifact_gate or '-'} | "
            f"{fam.parity_gate or '-'} | {fam.promotion_gate or '-'} | "
            f"{'yes' if fam.native_endorsed else 'no'} |"
        )
    lines.append("")
    lines.append("## Maintainer Quick Actions")
    lines.append("")
    lines.append("- Validate governance tree: `python -m conicshield.governance.audit_cli --strict`")
    lines.append(
        "- Generate dashboard: `python -m conicshield.governance.dashboard_cli "
        "--json-output output/governance_dashboard.json "
        "--markdown-output output/governance_dashboard.md`"
    )
    lines.append(
        "- Dry-run release: `python -m conicshield.governance.release_cli "
        "--run-dir benchmarks/runs/<run_id> --family-id <family_id> "
        "--reason '<reason>' --dry-run`"
    )
    lines.append("- Read runbook: `python -m conicshield.governance.runbook_cli`")
    lines.append("")
    return "\n".join(lines)
