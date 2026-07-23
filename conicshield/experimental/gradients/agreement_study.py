"""Corpus-wide research KKT / smoothed-projection vs finite-difference agreement (R2).

Quantifies ``exact_research_kkt`` and ``smoothed_research_projection`` against
``central_finite_difference`` across the versioned corpus. This is numerical
evidence only — not a proof — and explicitly does **not** claim native Moreau
``exact_backend_gradient`` / ``smoothed_backend_gradient`` availability.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import numpy as np

from conicshield.experimental.corpus.generate import load_all_scenarios
from conicshield.experimental.corpus.paths import CORPUS_VERSION, RESEARCH_ROOT
from conicshield.experimental.gradients.capability import CapabilityStatus
from conicshield.experimental.gradients.finite_difference import (
    central_finite_difference_jacobian,
    fd_agreement_metric,
)
from conicshield.experimental.gradients.kkt_research import exact_research_kkt_jacobian
from conicshield.experimental.gradients.modes import GradientMode
from conicshield.experimental.gradients.smoothed_research import smoothed_research_projection_jacobian
from conicshield.experimental.provenance import begin_experiment_provenance, finalize_experiment_provenance
from conicshield.experimental.solver_assurance.backends import create_research_projector
from conicshield.specs.schema import SafetySpec

AGREEMENT_STUDY_SCHEMA_ID = "research.kkt_fd_agreement_study.v0"
FAILURE_MODES: tuple[str, ...] = (
    "ok",
    "kkt_unavailable",
    "smoothed_unavailable",
    "singular_kkt",
    "active_set_change",
    "undefined_fd",
    "non_finite",
    "shape_mismatch",
)


@dataclass(slots=True)
class ScenarioAgreementRow:
    scenario_id: str
    family: str
    expected_regime: str
    kkt_status: str
    kkt_available: bool
    kkt_failure_mode: str
    kkt_rel_fro: float | None
    kkt_abs_fro: float | None
    kkt_singular_value_rel: float | None
    kkt_condition_number: float | None
    smoothed_status: str
    smoothed_available: bool
    smoothed_failure_mode: str
    smoothed_rel_fro: float | None
    smoothed_abs_fro: float | None
    smoothed_singular_value_rel: float | None
    fd_active_set_changed: bool
    active_set: tuple[str, ...] = ()
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "family": self.family,
            "expected_regime": self.expected_regime,
            "modes": {
                "reference": str(GradientMode.CENTRAL_FINITE_DIFFERENCE),
                "research_kkt": str(GradientMode.EXACT_RESEARCH_KKT),
                "research_smoothed": str(GradientMode.SMOOTHED_RESEARCH_PROJECTION),
                "native_exact": str(GradientMode.EXACT_BACKEND_GRADIENT),
                "native_smoothed": str(GradientMode.SMOOTHED_BACKEND_GRADIENT),
            },
            "kkt_status": self.kkt_status,
            "kkt_available": self.kkt_available,
            "kkt_failure_mode": self.kkt_failure_mode,
            "kkt_rel_fro": self.kkt_rel_fro,
            "kkt_abs_fro": self.kkt_abs_fro,
            "kkt_singular_value_rel": self.kkt_singular_value_rel,
            "kkt_condition_number": self.kkt_condition_number,
            "smoothed_status": self.smoothed_status,
            "smoothed_available": self.smoothed_available,
            "smoothed_failure_mode": self.smoothed_failure_mode,
            "smoothed_rel_fro": self.smoothed_rel_fro,
            "smoothed_abs_fro": self.smoothed_abs_fro,
            "smoothed_singular_value_rel": self.smoothed_singular_value_rel,
            "fd_active_set_changed": self.fd_active_set_changed,
            "active_set": list(self.active_set),
            "notes": self.notes,
            "not_native_moreau": True,
        }


@dataclass(slots=True)
class StratifiedSummary:
    key: str
    stratum: str
    n: int
    kkt_available_rate: float
    kkt_mean_rel_fro: float | None
    kkt_median_rel_fro: float | None
    smoothed_available_rate: float
    smoothed_mean_rel_fro: float | None
    failure_mode_counts: dict[str, int] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "stratum": self.stratum,
            "n": self.n,
            "kkt_available_rate": self.kkt_available_rate,
            "kkt_mean_rel_fro": self.kkt_mean_rel_fro,
            "kkt_median_rel_fro": self.kkt_median_rel_fro,
            "smoothed_available_rate": self.smoothed_available_rate,
            "smoothed_mean_rel_fro": self.smoothed_mean_rel_fro,
            "failure_mode_counts": dict(self.failure_mode_counts),
        }


@dataclass(slots=True)
class AgreementStudyReport:
    schema_id: str = AGREEMENT_STUDY_SCHEMA_ID
    corpus_version: str = CORPUS_VERSION
    backend_id: str = "cvxpy_clarabel"
    fd_h: float = 1e-5
    smoothing_epsilon: float = 1e-2
    ci_small: bool = False
    rows: list[ScenarioAgreementRow] = field(default_factory=list)
    by_family: list[StratifiedSummary] = field(default_factory=list)
    by_regime: list[StratifiedSummary] = field(default_factory=list)
    overall: dict[str, Any] = field(default_factory=dict)
    negative_results: list[str] = field(default_factory=list)
    conclusions: list[str] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_id": self.schema_id,
            "corpus_version": self.corpus_version,
            "backend_id": self.backend_id,
            "fd_h": self.fd_h,
            "smoothing_epsilon": self.smoothing_epsilon,
            "ci_small": self.ci_small,
            "mode_labels": {
                "exact_research_kkt": "research_adapter_not_native",
                "smoothed_research_projection": "research_adapter_not_native",
                "central_finite_difference": "numerical_baseline",
                "exact_backend_gradient": "moreau_compiled_solver_backward_experimental",
                "smoothed_backend_gradient": "softplus_moreau_qp_experimental",
            },
            "rows": [r.as_dict() for r in self.rows],
            "by_family": [s.as_dict() for s in self.by_family],
            "by_regime": [s.as_dict() for s in self.by_regime],
            "overall": dict(self.overall),
            "negative_results": list(self.negative_results),
            "conclusions": list(self.conclusions),
            "evidence_kind": "numerical_agreement_only",
            "not_a_proof": True,
            "provenance": dict(self.provenance),
        }


def _singular_values(jac: np.ndarray) -> np.ndarray:
    if jac.size == 0:
        return np.asarray([], dtype=np.float64)
    try:
        return np.linalg.svd(jac, compute_uv=False)
    except np.linalg.LinAlgError:
        return np.asarray([float("nan")], dtype=np.float64)


def _sv_rel(a: np.ndarray, b: np.ndarray) -> float | None:
    sa = _singular_values(a)
    sb = _singular_values(b)
    if sa.size == 0 or sb.size == 0 or sa.size != sb.size:
        return None
    if not (np.all(np.isfinite(sa)) and np.all(np.isfinite(sb))):
        return None
    denom = max(float(np.linalg.norm(sa)), 1e-16)
    return float(np.linalg.norm(sa - sb) / denom)


def _abs_fro(a: np.ndarray, b: np.ndarray) -> float | None:
    aa = np.asarray(a, dtype=np.float64)
    bb = np.asarray(b, dtype=np.float64)
    if aa.shape != bb.shape:
        return None
    if not (np.all(np.isfinite(aa)) and np.all(np.isfinite(bb))):
        return None
    return float(np.linalg.norm(aa - bb, ord="fro"))


def _classify_kkt_failure(reason: str, *, fd_changed: bool) -> str:
    r = (reason or "").lower()
    if "singular" in r or "ill-conditioned" in r or "condition" in r:
        return "singular_kkt"
    if "active" in r and "change" in r:
        return "active_set_change"
    if fd_changed:
        return "active_set_change"
    if "undefined" in r:
        return "undefined_fd"
    return "kkt_unavailable"


def _mean_or_none(vals: list[float]) -> float | None:
    finite = [v for v in vals if np.isfinite(v)]
    if not finite:
        return None
    return float(np.mean(finite))


def _median_or_none(vals: list[float]) -> float | None:
    finite = [v for v in vals if np.isfinite(v)]
    if not finite:
        return None
    return float(np.median(finite))


def _stratify(
    rows: list[ScenarioAgreementRow],
    *,
    key: Literal["family", "expected_regime"],
) -> list[StratifiedSummary]:
    buckets: dict[str, list[ScenarioAgreementRow]] = defaultdict(list)
    for row in rows:
        buckets[getattr(row, key)].append(row)
    out: list[StratifiedSummary] = []
    for stratum, group in sorted(buckets.items()):
        kkt_rels = [float(r.kkt_rel_fro) for r in group if r.kkt_rel_fro is not None]
        sm_rels = [float(r.smoothed_rel_fro) for r in group if r.smoothed_rel_fro is not None]
        fail_counts: dict[str, int] = defaultdict(int)
        for r in group:
            fail_counts[r.kkt_failure_mode] += 1
        out.append(
            StratifiedSummary(
                key=key,
                stratum=stratum,
                n=len(group),
                kkt_available_rate=float(sum(1 for r in group if r.kkt_available) / max(len(group), 1)),
                kkt_mean_rel_fro=_mean_or_none(kkt_rels),
                kkt_median_rel_fro=_median_or_none(kkt_rels),
                smoothed_available_rate=float(
                    sum(1 for r in group if r.smoothed_available) / max(len(group), 1)
                ),
                smoothed_mean_rel_fro=_mean_or_none(sm_rels),
                failure_mode_counts=dict(fail_counts),
            )
        )
    return out


def _evaluate_scenario(
    scenario: dict[str, Any],
    *,
    backend_id: str,
    fd_h: float,
    smoothing_epsilon: float,
) -> ScenarioAgreementRow:
    spec = SafetySpec.model_validate(scenario["spec"])
    proposed = np.asarray(scenario["proposed_action"], dtype=np.float64)
    previous = np.asarray(scenario["previous_action"], dtype=np.float64)
    reference = np.asarray(scenario["reference_action"], dtype=np.float64)
    weights = scenario.get("weights") or {}
    policy_weight = float(weights.get("policy_weight", 1.0))
    reference_weight = float(weights.get("reference_weight", 0.0))

    def _project(p: np.ndarray) -> Any:
        projector = create_research_projector(backend_id=backend_id, spec=spec)
        return projector.project(
            p,
            previous,
            reference_action=reference,
            policy_weight=policy_weight,
            reference_weight=reference_weight,
        )

    def forward(p: np.ndarray) -> np.ndarray:
        return np.asarray(_project(p).corrected_action, dtype=np.float64)

    def active_set_fn(p: np.ndarray) -> tuple[str, ...]:
        return tuple(_project(p).active_constraints)

    fd = central_finite_difference_jacobian(
        forward,
        proposed,
        h=fd_h,
        parameter_name="proposed_action",
        active_set_fn=active_set_fn,
    )
    fd_changed = bool(fd.active_set_changed)
    fd_ok = fd.failure_status is None and fd.jacobian.size > 0 and np.all(np.isfinite(fd.jacobian))

    kkt = exact_research_kkt_jacobian(
        spec=spec,
        proposed_action=proposed,
        previous_action=previous,
        reference_action=reference,
        policy_weight=policy_weight,
        reference_weight=reference_weight,
        backend_id=backend_id,
        compare_central_fd=False,
        fd_h=fd_h,
    )
    sm = smoothed_research_projection_jacobian(
        spec=spec,
        proposed_action=proposed,
        previous_action=previous,
        reference_action=reference,
        policy_weight=policy_weight,
        reference_weight=reference_weight,
        epsilon=smoothing_epsilon,
        backend_id=backend_id,
        compare_fd=False,
        fd_h=fd_h,
    )

    kkt_rel: float | None = None
    kkt_abs: float | None = None
    kkt_sv: float | None = None
    kkt_mode = "ok"
    if not fd_ok:
        kkt_mode = "undefined_fd"
    elif not kkt.available or kkt.jacobian is None:
        kkt_mode = _classify_kkt_failure(kkt.reason, fd_changed=fd_changed)
    else:
        if kkt.jacobian.shape != fd.jacobian.shape:
            kkt_mode = "shape_mismatch"
        elif not np.all(np.isfinite(kkt.jacobian)):
            kkt_mode = "non_finite"
        else:
            kkt_rel = fd_agreement_metric(kkt.jacobian, fd.jacobian)
            kkt_abs = _abs_fro(kkt.jacobian, fd.jacobian)
            kkt_sv = _sv_rel(kkt.jacobian, fd.jacobian)
            if fd_changed:
                kkt_mode = "active_set_change"

    sm_rel: float | None = None
    sm_abs: float | None = None
    sm_sv: float | None = None
    sm_mode = "ok"
    if not fd_ok:
        sm_mode = "undefined_fd"
    elif not sm.available or sm.jacobian is None:
        sm_mode = "smoothed_unavailable"
    else:
        if sm.jacobian.shape != fd.jacobian.shape:
            sm_mode = "shape_mismatch"
        elif not np.all(np.isfinite(sm.jacobian)):
            sm_mode = "non_finite"
        else:
            sm_rel = fd_agreement_metric(sm.jacobian, fd.jacobian)
            sm_abs = _abs_fro(sm.jacobian, fd.jacobian)
            sm_sv = _sv_rel(sm.jacobian, fd.jacobian)
            if fd_changed:
                sm_mode = "active_set_change"

    return ScenarioAgreementRow(
        scenario_id=str(scenario["scenario_id"]),
        family=str(scenario.get("family") or "unknown"),
        expected_regime=str(scenario.get("expected_regime") or "unknown"),
        kkt_status=str(kkt.status),
        kkt_available=bool(kkt.available),
        kkt_failure_mode=kkt_mode,
        kkt_rel_fro=kkt_rel,
        kkt_abs_fro=kkt_abs,
        kkt_singular_value_rel=kkt_sv,
        kkt_condition_number=kkt.kkt_condition_number,
        smoothed_status=str(sm.status),
        smoothed_available=bool(sm.available),
        smoothed_failure_mode=sm_mode,
        smoothed_rel_fro=sm_rel,
        smoothed_abs_fro=sm_abs,
        smoothed_singular_value_rel=sm_sv,
        fd_active_set_changed=fd_changed,
        active_set=tuple(kkt.active_set or fd.active_set_at_base),
        notes=kkt.reason or sm.reason or "",
    )


def _select_scenarios(
    *,
    ci_small: bool,
    families: list[str] | None,
    max_scenarios: int | None,
) -> list[dict[str, Any]]:
    scenarios = load_all_scenarios()
    if families:
        allow = set(families)
        scenarios = [s for s in scenarios if s.get("family") in allow]
    if ci_small:
        # Deterministic CI-small: prioritize active-set transitions + a few other regimes.
        preferred = [
            "active_set_transition_neighborhoods",
            "interior_feasible",
            "single_active_bound",
            "rate_limited_transitions",
        ]
        picked: list[dict[str, Any]] = []
        for fam in preferred:
            fam_rows = [s for s in scenarios if s.get("family") == fam]
            if fam == "active_set_transition_neighborhoods":
                picked.extend(fam_rows[:4])
            else:
                picked.extend(fam_rows[:1])
        # Stable unique by scenario_id
        seen: set[str] = set()
        out: list[dict[str, Any]] = []
        for s in picked:
            sid = str(s["scenario_id"])
            if sid in seen:
                continue
            seen.add(sid)
            out.append(s)
        return out[: max_scenarios or 8]
    if max_scenarios is not None:
        return scenarios[: max(0, int(max_scenarios))]
    return scenarios


def run_agreement_study(
    *,
    backend_id: str = "cvxpy_clarabel",
    fd_h: float = 1e-5,
    smoothing_epsilon: float = 1e-2,
    ci_small: bool = False,
    families: list[str] | None = None,
    max_scenarios: int | None = None,
    output_dir: Path | None = None,
    exact_command: str = "python -m conicshield.experimental.gradients.agreement_study",
) -> AgreementStudyReport:
    """Run corpus (or CI-small) KKT/smoothed vs central-FD agreement study."""

    scenarios = _select_scenarios(ci_small=ci_small, families=families, max_scenarios=max_scenarios)
    prov = begin_experiment_provenance(
        scenario_corpus_version=CORPUS_VERSION,
        backend=backend_id,
        exact_command=exact_command,
        random_seeds={"agreement_study": 0},
        solver_settings={
            "ci_small": ci_small,
            "fd_h": fd_h,
            "smoothing_epsilon": smoothing_epsilon,
            "n_scenarios": len(scenarios),
        },
        tolerances={"fd_h": float(fd_h)},
        solver_distribution="cvxpy",
        warm_start_policy="cold",
        fallback_policy="record_only",
        batch_size=1,
    )

    rows = [
        _evaluate_scenario(
            s,
            backend_id=backend_id,
            fd_h=fd_h,
            smoothing_epsilon=smoothing_epsilon,
        )
        for s in scenarios
    ]

    by_family = _stratify(rows, key="family")
    by_regime = _stratify(rows, key="expected_regime")

    kkt_rels = [float(r.kkt_rel_fro) for r in rows if r.kkt_rel_fro is not None]
    sm_rels = [float(r.smoothed_rel_fro) for r in rows if r.smoothed_rel_fro is not None]
    kkt_ok = sum(1 for r in rows if r.kkt_available)
    sm_ok = sum(1 for r in rows if r.smoothed_available)
    active_set_fail = sum(1 for r in rows if r.kkt_failure_mode == "active_set_change")
    singular_fail = sum(1 for r in rows if r.kkt_failure_mode == "singular_kkt")

    negative: list[str] = []
    if kkt_ok == 0:
        negative.append("exact_research_kkt unavailable on all selected scenarios")
    if active_set_fail > 0:
        negative.append(
            f"{active_set_fail}/{len(rows)} scenarios flagged active-set-change under FD neighborhood"
        )
    if singular_fail > 0:
        negative.append(f"{singular_fail}/{len(rows)} scenarios failed closed on singular/ill-conditioned KKT")
    as_rows = [r for r in rows if r.family == "active_set_transition_neighborhoods"]
    if as_rows:
        as_avail = sum(1 for r in as_rows if r.kkt_available)
        if as_avail < len(as_rows):
            negative.append(
                f"active_set_transition_neighborhoods: KKT available on {as_avail}/{len(as_rows)} "
                "(expected frequent fail-closed near transitions)"
            )

    conclusions = [
        "exact_research_kkt is a fixed-active-set public-QP KKT adapter — not native Moreau "
        "exact_backend_gradient.",
        "smoothed_research_projection is an epsilon-smoothed research adapter — not "
        "smoothed_backend_gradient.",
        "Agreement metrics are numerical evidence only; they do not prove correctness of "
        "implicit differentiation under active-set changes.",
        "Experimental exact_backend_gradient uses CompiledSolver.backward; "
        "smoothed_backend_gradient uses softplus inequality softening on the Moreau QP. "
        "Production differentiation_api identity flag remains separate; R2 native gate "
        "not claimed passed.",
    ]

    from conicshield.experimental.gradients.exact_backend import (
        _probe_vendor_compiled_backward,
    )

    _caps = _probe_vendor_compiled_backward()
    _exact_status = (
        CapabilityStatus.AVAILABLE
        if _caps.get("vendor_compiled_backward_api")
        else CapabilityStatus.UNAVAILABLE
    )
    _sm_status = (
        CapabilityStatus.AVAILABLE
        if _caps.get("vendor_compiled_backward_api")
        and not _caps.get("windows_native_unsupported")
        else CapabilityStatus.UNAVAILABLE
    )

    overall = {
        "n_scenarios": len(rows),
        "kkt_available_count": kkt_ok,
        "kkt_available_rate": float(kkt_ok / max(len(rows), 1)),
        "kkt_mean_rel_fro": _mean_or_none(kkt_rels),
        "kkt_median_rel_fro": _median_or_none(kkt_rels),
        "smoothed_available_count": sm_ok,
        "smoothed_available_rate": float(sm_ok / max(len(rows), 1)),
        "smoothed_mean_rel_fro": _mean_or_none(sm_rels),
        "failure_mode_counts": {
            mode: sum(1 for r in rows if r.kkt_failure_mode == mode) for mode in FAILURE_MODES
        },
        "native_exact_backend_gradient": str(_exact_status),
        "native_smoothed_backend_gradient": str(_sm_status),
        "research_differentiation_surface": bool(
            _caps.get("research_differentiation_surface")
        ),
    }

    report = AgreementStudyReport(
        corpus_version=CORPUS_VERSION,
        backend_id=backend_id,
        fd_h=fd_h,
        smoothing_epsilon=smoothing_epsilon,
        ci_small=ci_small,
        rows=rows,
        by_family=by_family,
        by_regime=by_regime,
        overall=overall,
        negative_results=negative,
        conclusions=conclusions,
    )

    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        name = "kkt_fd_agreement_ci_small.json" if ci_small else "kkt_fd_agreement.json"
        out_path = output_dir / name
        md_path = output_dir / (name.replace(".json", ".md"))
        md_path.write_text(render_agreement_report_markdown(report), encoding="utf-8")
        finalize_experiment_provenance(prov, artifact_paths=[out_path, md_path])
        report.provenance = prov.as_dict()
        out_path.write_text(json.dumps(report.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        # Re-hash after final write
        finalize_experiment_provenance(prov, artifact_paths=[out_path, md_path])
        report.provenance = prov.as_dict()
        out_path.write_text(json.dumps(report.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        prov.to_json(output_dir / "provenance.json")

    return report


def render_agreement_report_markdown(report: AgreementStudyReport | dict[str, Any]) -> str:
    """Markdown filler for the agreement study (numerical evidence, not proof)."""

    data = report.as_dict() if isinstance(report, AgreementStudyReport) else dict(report)
    overall = data.get("overall") or {}
    lines = [
        "# Research KKT / smoothed vs central FD agreement",
        "",
        f"- schema: `{data.get('schema_id')}`",
        f"- corpus_version: `{data.get('corpus_version')}`",
        f"- ci_small: {data.get('ci_small')}",
        f"- scenarios: {overall.get('n_scenarios')}",
        f"- kkt_available_rate: {overall.get('kkt_available_rate')}",
        f"- kkt_mean_rel_fro: {overall.get('kkt_mean_rel_fro')}",
        f"- smoothed_available_rate: {overall.get('smoothed_available_rate')}",
        f"- smoothed_mean_rel_fro: {overall.get('smoothed_mean_rel_fro')}",
        "",
        "## Honest conclusions",
        "",
    ]
    for c in data.get("conclusions") or []:
        lines.append(f"- {c}")
    lines.extend(["", "## Negative / inconclusive results", ""])
    negs = data.get("negative_results") or []
    if not negs:
        lines.append("- (none recorded)")
    else:
        for n in negs:
            lines.append(f"- {n}")
    lines.extend(
        [
            "",
            "## Stratification by family",
            "",
            "| family | n | kkt_avail | kkt_mean_rel | sm_avail | sm_mean_rel |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for s in data.get("by_family") or []:
        lines.append(
            f"| {s.get('stratum')} | {s.get('n')} | {s.get('kkt_available_rate')} | "
            f"{s.get('kkt_mean_rel_fro')} | {s.get('smoothed_available_rate')} | "
            f"{s.get('smoothed_mean_rel_fro')} |"
        )
    lines.extend(
        [
            "",
            "## Mode separation",
            "",
            "- `exact_research_kkt` ≠ `exact_backend_gradient` (Moreau CompiledSolver.backward)",
            "- `smoothed_research_projection` ≠ `smoothed_backend_gradient` "
            "(softplus Moreau QP)",
            "- Primary baseline: `central_finite_difference`",
            "",
        ]
    )
    return "\n".join(lines)


def write_ci_small_fixture(
    report: AgreementStudyReport,
    *,
    fixture_path: Path | None = None,
) -> Path:
    """Write a compact CI fixture (strip per-scenario jacobians — rows only keep scalars)."""

    path = fixture_path or (RESEARCH_ROOT / "fixtures" / "kkt_fd_agreement_ci_small.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = report.as_dict()
    # Compact: drop verbose notes if huge; keep all scalar metrics.
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Corpus-wide research KKT vs FD agreement study")
    parser.add_argument("--ci-small", action="store_true")
    parser.add_argument("--write-fixture", action="store_true", help="Write committed CI-small fixture")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output/research/agreement_study"),
    )
    parser.add_argument("--max-scenarios", type=int, default=None)
    args = parser.parse_args()
    report = run_agreement_study(
        output_dir=args.output_dir,
        ci_small=args.ci_small,
        max_scenarios=args.max_scenarios,
    )
    if args.write_fixture and args.ci_small:
        path = write_ci_small_fixture(report)
        print(f"wrote fixture {path}")
    ov = report.overall
    print(
        f"agreement study: n={ov.get('n_scenarios')} "
        f"kkt_avail={ov.get('kkt_available_rate'):.3f} "
        f"kkt_mean_rel={ov.get('kkt_mean_rel_fro')} "
        f"neg={len(report.negative_results)}"
    )


if __name__ == "__main__":
    main()
