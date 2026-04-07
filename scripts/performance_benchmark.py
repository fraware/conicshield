#!/usr/bin/env python3
"""Layer E: measure CVXPY vs native shield solves; optional CPU vs CUDA; write JSON/CSV/MD."""

from __future__ import annotations

import argparse
import csv
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

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


def _spec() -> SafetySpec:
    return SafetySpec(
        spec_id="perf/minimal",
        version="0.1.0",
        action_dim=4,
        constraints=[
            SimplexConstraint(total=1.0),
            TurnFeasibilityConstraint(allowed_actions=[0, 1, 2, 3]),
            BoxConstraint(lower=[0.0] * 4, upper=[1.0] * 4),
            RateConstraint(max_delta=[0.9] * 4),
        ],
    )


def _run_timed(project, proposed: np.ndarray, prev: np.ndarray | None) -> tuple[float, Any]:
    t0 = time.perf_counter()
    r = project.project(proposed, prev, policy_weight=1.0, reference_weight=0.0)
    return time.perf_counter() - t0, r


def _bench_cvxpy(spec: SafetySpec, proposed: np.ndarray, prev: np.ndarray, repeats: int) -> dict[str, Any]:
    times: list[float] = []
    for _ in range(repeats):
        proj = create_projector(
            spec=spec,
            backend=Backend.CVXPY_MOREAU,
            cvxpy_options=SolverOptions(device="cpu", max_iter=500, verbose=False),
        )
        dt, _ = _run_timed(proj, proposed, prev)
        times.append(dt)
    arr = np.array(times, dtype=np.float64)
    return {
        "path": "cvxpy_moreau",
        "device": "cpu",
        "repeats": repeats,
        "mean_sec": float(arr.mean()),
        "p50_sec": float(np.percentile(arr, 50)),
        "p95_sec": float(np.percentile(arr, 95)),
    }


def _bench_native_cold(
    spec: SafetySpec,
    proposed: np.ndarray,
    prev: np.ndarray,
    repeats: int,
    device: str,
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
            ),
        )
        dt, _ = _run_timed(proj, proposed, prev)
        times.append(dt)
    arr = np.array(times, dtype=np.float64)
    return {
        "path": "native_cold",
        "device": device,
        "repeats": repeats,
        "mean_sec": float(arr.mean()),
        "p50_sec": float(np.percentile(arr, 50)),
        "p95_sec": float(np.percentile(arr, 95)),
    }


def _bench_native_warm(
    spec: SafetySpec,
    proposed: np.ndarray,
    prev: np.ndarray,
    repeats: int,
    device: str,
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
    arr = np.array(times, dtype=np.float64)
    return {
        "path": "native_warm_sequence",
        "device": device,
        "repeats": repeats,
        "mean_sec": float(arr.mean()),
        "p50_sec": float(np.percentile(arr, 50)),
        "p95_sec": float(np.percentile(arr, 95)),
        "warm_start_speedup_vs_first": float(times[0] / max(times[-1], 1e-12)) if len(times) > 1 else None,
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
    p.add_argument("--out-dir", type=Path, default=None)
    p.add_argument("--skip-cuda", action="store_true")
    p.add_argument("--no-plots", action="store_true", help="Skip matplotlib PNG even if rows exist.")
    args = p.parse_args()
    root = Path(__file__).resolve().parents[1]
    out_dir = args.out_dir or (root / "output")
    out_dir.mkdir(parents=True, exist_ok=True)

    spec = _spec()
    proposed = np.array([0.65, 0.2, 0.1, 0.05], dtype=np.float64)
    prev = np.array([0.25, 0.25, 0.25, 0.25], dtype=np.float64)

    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    try:
        rows.append(_bench_cvxpy(spec, proposed, prev, args.repeats))
    except Exception as exc:
        errors.append(f"cvxpy: {exc}")

    for dev in ("cpu",):
        try:
            rows.append(_bench_native_cold(spec, proposed, prev, args.repeats, dev))
            rows.append(_bench_native_warm(spec, proposed, prev, args.repeats, dev))
        except Exception as exc:
            errors.append(f"native_{dev}: {exc}")

    if not args.skip_cuda and _cuda_available():
        try:
            rows.append(_bench_native_cold(spec, proposed, prev, max(3, args.repeats // 2), "cuda"))
        except Exception as exc:
            errors.append(f"native_cuda: {exc}")

    summary: dict[str, Any] = {
        "generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repeats_config": args.repeats,
        "rows": rows,
        "errors": errors,
        "cuda_claim_note": (
            "CUDA rows only when device_available(cuda) and solve succeeds; " "see PERFORMANCE_BENCHMARKING_POLICY.md"
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

    md_lines = [
        "# Performance report",
        "",
        f"Generated: {summary['generated_at_utc']}",
        "",
        "| path | device | mean_sec | p95_sec |",
        "|------|--------|----------|---------|",
    ]
    for row in rows:
        md_lines.append(f"| {row.get('path')} | {row.get('device')} | {row.get('mean_sec')} | {row.get('p95_sec')} |")
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
