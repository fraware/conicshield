from __future__ import annotations

from conicshield.parity.replay import ParitySummary


class ParityGateError(RuntimeError):
    pass


def enforce_default_parity_gates(summary: ParitySummary) -> None:
    if summary.action_match_rate < 1.0:
        raise ParityGateError(f"Action match rate below 1.0: {summary.action_match_rate:.6f}")
    if summary.active_constraints_match_rate < 0.999:
        raise ParityGateError(f"Active-constraint match rate below 0.999: {summary.active_constraints_match_rate:.6f}")
    if summary.max_corrected_linf > 1e-5:
        raise ParityGateError(f"max_corrected_linf too large: {summary.max_corrected_linf:.6e}")
    if summary.p95_corrected_linf > 1e-6:
        raise ParityGateError(f"p95_corrected_linf too large: {summary.p95_corrected_linf:.6e}")
    if summary.max_corrected_l2 > 1e-5:
        raise ParityGateError(f"max_corrected_l2 too large: {summary.max_corrected_l2:.6e}")
