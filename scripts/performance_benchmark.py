#!/usr/bin/env python3
"""Layer E: measure CVXPY vs native shield solves; optional CPU vs CUDA; write JSON/CSV/MD.

When Moreau is available and ``--batch-sizes`` is set, emits both ``native_microbatch`` (sequential
``project``) and ``native_compiled_real_batch`` rows via ``NativeMoreauCompiledBatchProjector`` (see
``_bench_native_microbatch`` / ``_bench_native_compiled_real_batch``). Programmatic access to batching:
``conicshield.core.solver_factory.create_batch_projector``.
"""

from __future__ import annotations

import argparse
import csv
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from conicshield.core.moreau_batched import NativeMoreauCompiledBatchProjector
from conicshield.core.moreau_compiled import NativeMoreauCompiledOptions
from conicshield.core.solver_factory import Backend, create_projector
from conicshield.specs.compiler import SolverOptions
from conicshield.specs.schema import (
    BoxConstraint,
    RateConstraint,
    SafetySpec,
    SimplexConstraint,
    TurnFeasibilityConstraint,
)


def _conditioning_to_rate(conditioning: str) -> float:
    if conditioning == "tight":
        return 0.12
    if conditioning == "loose":
        return 0.95
    return 0.9


def _parse_int_csv(s: str) -> list[int]:
    return [int(x.strip()) for x in s.split(",") if x.strip()]


def _spec_dim(n: int, rate_delta: float) -> SafetySpec:
    if n < 2:
        raise ValueError("action_dim must be >= 2")
    md = float(rate_delta)
    return SafetySpec(
        spec_id=f"perf/n{n}",
        version="0.1.0",
        action_dim=n,
        constraints=[
            SimplexConstraint(total=1.0),
            TurnFeasibilityConstraint(allowed_actions=list(range(n))),
            BoxConstraint(lower=[0.0] * n, upper=[1.0] * n),
            RateConstraint(max_delta=[md] * n),
        ],
    )


def _scenario_vectors_dim(n: int) -> list[tuple[str, np.ndarray, np.ndarray]]:
    prev = np.ones(n, dtype=np.float64) / n
    p0 = np.linspace(2.0, 0.5, n)
    p0 = p0 / p0.sum()
    p1 = np.sin(np.linspace(0.0, 3.0, n)) + 1.1
    p1 = p1 / p1.sum()
    p2 = np.zeros(n, dtype=np.float64)
    p2[0] = 0.85
    if n > 1:
        p2[1:] = 0.15 / (n - 1)
    return [("s0", p0, prev.copy()), ("s1", p1, prev.copy()), ("s2", p2, prev.copy())]


def _batch_proposals(*, spec: SafetySpec, prev: np.ndarray, batch_size: int, seed: int) -> list[np.ndarray]:
    rng = np.random.default_rng(seed)
    n = spec.action_dim
    out: list[np.ndarray] = []
    for _ in range(batch_size):
        x = rng.random(n)
        x = x / x.sum()
        out.append(x.astype(np.float64))
    return out


def _run_timed(project, proposed: np.ndarray, prev: np.ndarray | None) -> tuple[float, Any]:
    t0 = time.perf_counter()
    r = project.project(proposed, prev, policy_weight=1.0, reference_weight=0.0)
    return time.perf_counter() - t0, r


def _stats_from_times(times: list[float], *, warmup: int) -> np.ndarray:
    if warmup < 0:
        raise ValueError("warmup must be >= 0")
    if warmup >= len(times):
        raise ValueError("warmup must be smaller than number of measurements")
    return np.array(times[warmup:], dtype=np.float64)


def _tag_row(row: dict[str, Any], *, scenario_id: str, conditioning: str) -> dict[str, Any]:
    row = dict(row)
    row["scenario_id"] = scenario_id
    row["conditioning"] = conditioning
    return row


def _bench_cvxpy(
    spec: SafetySpec, proposed: np.ndarray, prev: np.ndarray, repeats: int, *, warmup: int = 0
) -> dict[str, Any]:
    times: list[float] = []
    for _ in range(repeats):
        proj = create_projector(
            spec=spec,
            backend=Backend.CVXPY_MOREAU,
            cvxpy_options=SolverOptions(device="cpu", max_iter=500, verbose=False),
        )
        dt, _ = _run_timed(proj, proposed, prev)
        times.append(dt)
    arr = _stats_from_times(times, warmup=warmup)
    return {
        "path": "cvxpy_moreau",
        "device": "cpu",
        "repeats": repeats,
        "warmup": warmup,
        "measure_iters": int(arr.size),
        "mean_sec": float(arr.mean()),
        "p50_sec": float(np.percentile(arr, 50)),
        "p95_sec": float(np.percentile(arr, 95)),
        "action_dim": spec.action_dim,
        "auto_tune": False,
    }


def _bench_native_cold(
    spec: SafetySpec,
    proposed: np.ndarray,
    prev: np.ndarray,
    repeats: int,
    device: str,
    *,
    auto_tune: bool = False,
    warmup: int = 0,
) -> dict[str, Any]:
    times: list[float] = []
    for _ in range(repeats):
        proj = create_projector(
            spec=spec,
            backend=Backend.NATIVE_MOREAU,
            native_options=NativeMoreauCompiledOptions(
                device=device,
                max_iter=500,
                verbose=False,
                persist_warm_start=False,
                auto_tune=auto_tune,
            ),
        )
        dt, _ = _run_timed(proj, proposed, prev)
        times.append(dt)
    arr = _stats_from_times(times, warmup=warmup)
    row: dict[str, Any] = {
        "path": "native_cold",
        "device": device,
        "repeats": repeats,
        "warmup": warmup,
        "measure_iters": int(arr.size),
        "mean_sec": float(arr.mean()),
        "p50_sec": float(np.percentile(arr, 50)),
        "p95_sec": float(np.percentile(arr, 95)),
        "auto_tune": auto_tune,
        "action_dim": spec.action_dim,
    }
    return row


def _bench_native_microbatch(
    spec: SafetySpec,
    prev: np.ndarray,
    proposals: list[np.ndarray],
    repeats: int,
    device: str,
    *,
    auto_tune: bool = False,
    warmup: int = 0,
) -> dict[str, Any]:
    k = len(proposals)
    if k < 1:
        raise ValueError("batch requires at least one proposal")
    proj = create_projector(
        spec=spec,
        backend=Backend.NATIVE_MOREAU,
        native_options=NativeMoreauCompiledOptions(
            device=device,
            max_iter=500,
            verbose=False,
            persist_warm_start=False,
            auto_tune=auto_tune,
        ),
    )
    wall: list[float] = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        for pr in proposals:
            proj.project(pr, prev, policy_weight=1.0, reference_weight=0.0)
        wall.append(time.perf_counter() - t0)
    arr = _stats_from_times(wall, warmup=warmup)
    mean_wall = float(arr.mean())
    return {
        "path": "native_microbatch",
        "device": device,
        "repeats": repeats,
        "warmup": warmup,
        "measure_iters": int(arr.size),
        "batch_size": k,
        "mean_sec": mean_wall,
        "mean_sec_per_solve": mean_wall / k,
        "p50_sec": float(np.percentile(arr, 50)),
        "p95_sec": float(np.percentile(arr, 95)),
        "auto_tune": auto_tune,
        "action_dim": spec.action_dim,
    }


def _bench_native_compiled_real_batch(
    spec: SafetySpec,
    prev: np.ndarray,
    proposals: list[np.ndarray],
    repeats: int,
    device: str,
    *,
    auto_tune: bool = False,
    warmup: int = 0,
) -> dict[str, Any]:
    """Single ``CompiledSolver.solve(qs, bs)`` per timing iteration (true batching)."""
    k = len(proposals)
    if k < 1:
        raise ValueError("batch requires at least one proposal")
    batch = np.stack(proposals, axis=0)
    proj = NativeMoreauCompiledBatchProjector(
        spec=spec,
        options=NativeMoreauCompiledOptions(
            device=device,
            max_iter=500,
            verbose=False,
            persist_warm_start=False,
            auto_tune=auto_tune,
        ),
    )
    wall: list[float] = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        proj.project_batch(batch, prev, policy_weight=1.0, reference_weight=0.0)
        wall.append(time.perf_counter() - t0)
    arr = _stats_from_times(wall, warmup=warmup)
    mean_wall = float(arr.mean())
    return {
        "path": "native_compiled_real_batch",
        "device": device,
        "repeats": repeats,
        "warmup": warmup,
        "measure_iters": int(arr.size),
        "batch_size": k,
        "mean_sec": mean_wall,
        "mean_sec_per_solve": mean_wall / k,
        "p50_sec": float(np.percentile(arr, 50)),
        "p95_sec": float(np.percentile(arr, 95)),
        "auto_tune": auto_tune,
        "action_dim": spec.action_dim,
    }


def _bench_native_warm(
    spec: SafetySpec,
    proposed: np.ndarray,
    prev: np.ndarray,
    repeats: int,
    device: str,
    *,
    warmup: int = 0,
) -> dict[str, Any]:
    proj = create_projector(
        spec=spec,
        backend=Backend.NATIVE_MOREAU,
        native_options=NativeMoreauCompiledOptions(
            device=device,
            max_iter=500,
            verbose=False,
            persist_warm_start=True,
        ),
    )
    times: list[float] = []
    cur_prev = prev
    for _ in range(repeats):
        dt, r = _run_timed(proj, proposed, cur_prev)
        times.append(dt)
        cur_prev = r.corrected_action
    arr = _stats_from_times(times, warmup=warmup)
    return {
        "path": "native_warm_sequence",
        "device": device,
        "repeats": repeats,
        "warmup": warmup,
        "measure_iters": int(arr.size),
        "mean_sec": float(arr.mean()),
        "p50_sec": float(np.percentile(arr, 50)),
        "p95_sec": float(np.percentile(arr, 95)),
        "warm_start_speedup_vs_first": float(times[0] / max(times[-1], 1e-12)) if len(times) > 1 else None,
        "action_dim": spec.action_dim,
        "auto_tune": False,
    }


def _write_plots(out_dir: Path, rows: list[dict[str, Any]]) -> list[str]:
    """Write PNG bar charts when matplotlib is available (non-interactive Agg backend)."""
    written: list[str] = []
    if not rows:
        return written
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return written

    labels = [f"{r.get('path')}\n({r.get('device')})" for r in rows]
    x = range(len(rows))
    means = [float(r["mean_sec"]) for r in rows]
    p95s = [float(r["p95_sec"]) for r in rows]

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    axes[0].bar(list(x), means, color="#3fb950")
    axes[0].set_title("Mean solve time (s)")
    axes[0].set_xticks(list(x))
    axes[0].set_xticklabels(labels, rotation=18, ha="right", fontsize=8)

    axes[1].bar(list(x), p95s, color="#58a6ff")
    axes[1].set_title("p95 solve time (s)")
    axes[1].set_xticks(list(x))
    axes[1].set_xticklabels(labels, rotation=18, ha="right", fontsize=8)

    fig.tight_layout()
    path = out_dir / "performance_latency.png"
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    written.append(str(path))
    return written


def _cuda_available() -> bool:
    try:
        import moreau

        if hasattr(moreau, "device_available"):
            return bool(moreau.device_available("cuda"))
    except Exception:
        pass
    return False


def main() -> int:
    p = argparse.ArgumentParser(description="Performance benchmark (vendor; requires Moreau).")
    p.add_argument("--repeats", type=int, default=5)
    p.add_argument("--warmup", type=int, default=1, help="Discard the first N measurements from each timing row.")
    p.add_argument("--measure-iters", type=int, default=4, help="Number of retained timing measurements.")
    p.add_argument("--out-dir", type=Path, default=None)
    p.add_argument("--skip-cuda", action="store_true")
    p.add_argument("--no-plots", action="store_true", help="Skip matplotlib PNG even if rows exist.")
    p.add_argument(
        "--sweep",
        action="store_true",
        help="Run decision-grade sweeps (action_dim × conditioning × scenarios; optional batch + auto_tune).",
    )
    p.add_argument(
        "--shield-action-dims",
        default="",
        help="Comma-separated simplex dimensions. Sweep default when empty: 4,8. Non-sweep default: 4.",
    )
    p.add_argument(
        "--batch-sizes",
        default="",
        help="Comma-separated microbatch sizes for native throughput rows (sweep only; uses scenario s0).",
    )
    p.add_argument(
        "--sweep-auto-tune",
        action="store_true",
        help="Add native cold rows with auto_tune=True alongside the default False.",
    )
    args = p.parse_args()
    repeats = int(args.warmup) + int(args.measure_iters)
    if repeats < 1:
        raise SystemExit("warmup + measure-iters must be >= 1")
    root = Path(__file__).resolve().parents[1]
    out_dir = args.out_dir or (root / "output")
    out_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    errors: list[str] = []

    dims_csv = args.shield_action_dims.strip()
    if args.sweep:
        dims = _parse_int_csv(dims_csv) if dims_csv else [4, 8]
    else:
        dims = _parse_int_csv(dims_csv) if dims_csv else [4]
    batch_sizes = _parse_int_csv(args.batch_sizes.strip()) if args.sweep and args.batch_sizes.strip() else []

    def _push_sweep_cell(*, n: int, conditioning: str, scen_id: str, proposed: np.ndarray, prev: np.ndarray) -> None:
        tag = f"n{n}_{conditioning}_{scen_id}"
        spec = _spec_dim(n, _conditioning_to_rate(conditioning))
        try:
            rows.append(
                _tag_row(
                    _bench_cvxpy(spec, proposed, prev, repeats, warmup=args.warmup),
                    scenario_id=tag,
                    conditioning=conditioning,
                )
            )
        except Exception as exc:
            errors.append(f"cvxpy {tag}: {exc}")
        for dev in ("cpu",):
            for auto_tune in (False, True) if args.sweep_auto_tune else (False,):
                try:
                    rows.append(
                        _tag_row(
                            _bench_native_cold(
                                spec, proposed, prev, repeats, dev, auto_tune=auto_tune, warmup=args.warmup
                            ),
                            scenario_id=tag,
                            conditioning=conditioning,
                        )
                    )
                except Exception as exc:
                    errors.append(f"native_{dev} {tag} auto_tune={auto_tune}: {exc}")
            try:
                rows.append(
                    _tag_row(
                        _bench_native_warm(spec, proposed, prev, repeats, dev, warmup=args.warmup),
                        scenario_id=tag,
                        conditioning=conditioning,
                    )
                )
            except Exception as exc:
                errors.append(f"native_{dev}_warm {tag}: {exc}")
        if not args.skip_cuda and _cuda_available():
            try:
                rows.append(
                    _tag_row(
                        _bench_native_cold(
                            spec,
                            proposed,
                            prev,
                            max(3, repeats // 2),
                            "cuda",
                            auto_tune=False,
                        ),
                        scenario_id=tag,
                        conditioning=conditioning,
                    )
                )
            except Exception as exc:
                errors.append(f"native_cuda {tag}: {exc}")

    if args.sweep:
        for n in dims:
            for conditioning in ("nominal", "tight", "loose"):
                for scen_id, proposed, prev in _scenario_vectors_dim(n):
                    _push_sweep_cell(n=n, conditioning=conditioning, scen_id=scen_id, proposed=proposed, prev=prev)
                if batch_sizes:
                    scenarios = _scenario_vectors_dim(n)
                    _, prop0, prev0 = scenarios[0]
                    spec_b = _spec_dim(n, _conditioning_to_rate(conditioning))
                    for bs in batch_sizes:
                        proposals = _batch_proposals(spec=spec_b, prev=prev0, batch_size=bs, seed=11 + n + bs)
                        btag = f"n{n}_{conditioning}_batch{bs}"
                        for dev in ("cpu",):
                            for auto_tune in (False, True) if args.sweep_auto_tune else (False,):
                                try:
                                    rows.append(
                                        _tag_row(
                                            _bench_native_microbatch(
                                                spec_b,
                                                prev0,
                                                proposals,
                                                max(2, repeats // 2),
                                                dev,
                                                auto_tune=auto_tune,
                                                warmup=0,
                                            ),
                                            scenario_id=btag,
                                            conditioning=conditioning,
                                        )
                                    )
                                except Exception as exc:
                                    errors.append(
                                        f"native_microbatch n{n} {conditioning} bs={bs} at={auto_tune}: {exc}"
                                    )
                                try:
                                    rows.append(
                                        _tag_row(
                                            _bench_native_compiled_real_batch(
                                                spec_b,
                                                prev0,
                                                proposals,
                                                max(2, repeats // 2),
                                                dev,
                                                auto_tune=auto_tune,
                                                warmup=0,
                                            ),
                                            scenario_id=btag,
                                            conditioning=conditioning,
                                        )
                                    )
                                except Exception as exc:
                                    errors.append(
                                        f"native_compiled_real_batch n{n} {conditioning} bs={bs} at={auto_tune}: {exc}"
                                    )
    else:
        n = dims[0]
        spec = _spec_dim(n, _conditioning_to_rate("nominal"))
        if n == 4:
            proposed = np.array([0.65, 0.2, 0.1, 0.05], dtype=np.float64)
            prev = np.array([0.25, 0.25, 0.25, 0.25], dtype=np.float64)
        else:
            _, proposed, prev = _scenario_vectors_dim(n)[0]
        try:
            rows.append(_bench_cvxpy(spec, proposed, prev, repeats, warmup=args.warmup))
        except Exception as exc:
            errors.append(f"cvxpy: {exc}")

        for dev in ("cpu",):
            try:
                rows.append(
                    _bench_native_cold(spec, proposed, prev, repeats, dev, auto_tune=False, warmup=args.warmup)
                )
                rows.append(_bench_native_warm(spec, proposed, prev, repeats, dev, warmup=args.warmup))
            except Exception as exc:
                errors.append(f"native_{dev}: {exc}")
        batch_prop = _batch_proposals(spec=spec, prev=prev, batch_size=4, seed=7)
        for dev in ("cpu",):
            try:
                rows.append(
                    _bench_native_microbatch(
                        spec,
                        prev,
                        batch_prop,
                        max(2, repeats // 2),
                        dev,
                        auto_tune=False,
                        warmup=args.warmup,
                    )
                )
                rows.append(
                    _bench_native_compiled_real_batch(
                        spec,
                        prev,
                        batch_prop,
                        max(2, repeats // 2),
                        dev,
                        auto_tune=False,
                        warmup=args.warmup,
                    )
                )
            except Exception as exc:
                errors.append(f"native batch paths ({dev}): {exc}")

        if not args.skip_cuda and _cuda_available():
            try:
                rows.append(
                    _bench_native_cold(
                        spec, proposed, prev, max(3, repeats // 2), "cuda", auto_tune=False, warmup=0
                    )
                )
            except Exception as exc:
                errors.append(f"native_cuda: {exc}")

    summary: dict[str, Any] = {
        "generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repeats_config": repeats,
        "warmup": int(args.warmup),
        "measure_iters": int(args.measure_iters),
        "sweep_mode": bool(args.sweep),
        "shield_action_dims": dims,
        "batch_sizes": batch_sizes,
        "sweep_auto_tune": bool(args.sweep_auto_tune),
        "rows": rows,
        "errors": errors,
        "cuda_claim_note": (
            "CUDA rows only when device_available(cuda) and solve succeeds; "
            "see docs/VERIFICATION_AND_STRESS_TEST_PLAN.md (Performance policy)"
        ),
    }
    (out_dir / "performance_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    csv_path = out_dir / "performance_matrix.csv"
    if rows:
        fieldnames = sorted({k for row in rows for k in row})
        with csv_path.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fieldnames)
            w.writeheader()
            for row in rows:
                w.writerow({k: row.get(k) for k in fieldnames})

    sweep_cols = any("scenario_id" in r for r in rows)
    md_lines = [
        "# Performance report",
        "",
        f"Generated: {summary['generated_at_utc']}",
        "",
    ]
    if sweep_cols:
        md_lines.extend(
            [
                "| scenario_id | n | cond | path | dev | auto_tune | batch | mean_s | p95_s | /solve |",
                "|---------------|---|------|------|-----|-----------|-------|--------|-------|--------|",
            ]
        )
        for row in rows:
            per = row.get("mean_sec_per_solve", "")
            per_s = f"{per:.6f}" if per != "" and per is not None else ""
            md_lines.append(
                f"| {row.get('scenario_id', '')} | {row.get('action_dim', '')} | {row.get('conditioning', '')} | "
                f"{row.get('path')} | {row.get('device')} | {row.get('auto_tune', '')} | "
                f"{row.get('batch_size', '')} | {row.get('mean_sec')} | {row.get('p95_sec')} | {per_s} |"
            )
    else:
        md_lines.extend(
            [
                "| n | path | device | auto_tune | mean_sec | p95_sec | per_solve |",
                "|---|------|--------|-----------|----------|---------|-----------|",
            ]
        )
        for row in rows:
            per = row.get("mean_sec_per_solve", "")
            per_s = f"{per:.6f}" if per != "" and per is not None else ""
            md_lines.append(
                f"| {row.get('action_dim', '')} | {row.get('path')} | {row.get('device')} | "
                f"{row.get('auto_tune', '')} | {row.get('mean_sec')} | {row.get('p95_sec')} | {per_s} |"
            )
    if errors:
        md_lines.extend(["", "## Errors", "", "\n".join(errors)])

    plot_paths: list[str] = []
    if rows and not args.no_plots:
        plot_paths = _write_plots(out_dir, rows)
        if plot_paths:
            md_lines.extend(["", "## Plots", "", f"- `{plot_paths[0]}` — mean and p95 latency (bar chart)"])

    (out_dir / "performance_report.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(out_dir / "performance_summary.json")
    if not rows:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
