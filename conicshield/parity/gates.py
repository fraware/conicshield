from __future__ import annotations

import json

from conicshield.parity.replay import ParitySummary


class ParityGateError(RuntimeError):
    pass


def list_default_parity_gate_violations(summary: ParitySummary) -> list[str]:
    """Return human-readable violation lines; empty list means gates pass."""
    violations: list[str] = []
    if summary.action_match_rate < 1.0:
        violations.append(f"Action match rate below 1.0: {summary.action_match_rate:.6f}")
    if summary.active_constraints_match_rate < 0.999:
        violations.append(f"Active-constraint match rate below 0.999: {summary.active_constraints_match_rate:.6f}")
    if summary.max_corrected_linf > 1e-5:
        violations.append(f"max_corrected_linf too large: {summary.max_corrected_linf:.6e} (tol 1e-5)")
    if summary.p95_corrected_linf > 1e-6:
        violations.append(f"p95_corrected_linf too large: {summary.p95_corrected_linf:.6e} (tol 1e-6)")
    if summary.max_corrected_l2 > 1e-5:
        violations.append(f"max_corrected_l2 too large: {summary.max_corrected_l2:.6e} (tol 1e-5)")
    return violations


def enforce_default_parity_gates(summary: ParitySummary) -> None:
    violations = list_default_parity_gate_violations(summary)
    if violations:
        bullets = "\n".join(f"- {line}" for line in violations)
        metrics = json.dumps(summary.as_dict(), indent=2, sort_keys=True)
        raise ParityGateError(
            "Native/reference parity gates failed:\n"
            f"{bullets}\n\n"
            "Parity summary (metrics):\n"
            f"{metrics}\n\n"
            "See conicshield.parity.gates for thresholds; compare parity_steps.jsonl if written."
        )
