#!/usr/bin/env python3
"""Compare reference vs native arm metrics from the flagship ``summary.json``.

Audience: researcher inspecting published benchmark metrics at publish time.
Prerequisites: ``pip install -e .``; flagship bundle committed in repo.
Proves: ``load_summary`` exposes per-arm solve-time metrics for reference and native arms.
Does not prove: universal speedup, production readiness, or that metrics override governance —
  comparison is informative only; public batch narrative remains viability_only.
Expected: both arms present; p50/p95 printed; ratio line with disclaimer.
"""

from __future__ import annotations

from _common import FLAGSHIP_RUN_ID, configure_stdio, repo_root, section

from conicshield.published_runs import load_run, load_summary, verify_run

REFERENCE = "shielded-rules-plus-geometry"
NATIVE = "shielded-native-moreau"


def _fmt_ms(row_label: str, rows: dict) -> str:
    row = rows[row_label]
    p50 = row.solve_time_p50_ms
    p95 = row.extra.get("solve_time_p95_ms")
    parts = [f"p50_ms={p50}"]
    if p95 is not None:
        parts.append(f"p95_ms={p95}")
    return f"{row_label}: " + ", ".join(parts)


def main() -> int:
    configure_stdio()
    root = repo_root()

    section("verify_run")
    verify_run(FLAGSHIP_RUN_ID, repo_root=root)
    print("integrity OK")

    bundle = load_run(FLAGSHIP_RUN_ID, repo_root=root)
    gov = bundle.governance_status or {}
    print("governance state:", gov.get("state"), "(metrics do not override this)")

    section("load_summary")
    rows = {r.label: r for r in load_summary(FLAGSHIP_RUN_ID, repo_root=root)}
    missing = [a for a in (REFERENCE, NATIVE) if a not in rows]
    if missing:
        print("missing arms:", ", ".join(missing))
        print("available:", ", ".join(sorted(rows)))
        return 1

    print(_fmt_ms(REFERENCE, rows))
    print(_fmt_ms(NATIVE, rows))

    ref = rows[REFERENCE]
    nat = rows[NATIVE]
    if ref.solve_time_p50_ms and nat.solve_time_p50_ms and ref.solve_time_p50_ms > 0:
        ratio = float(nat.solve_time_p50_ms) / float(ref.solve_time_p50_ms)
        print(f"\nnative/reference p50 ratio: {ratio:.3f}")
        if ratio < 1.0:
            print("(snapshot: native p50 lower than reference p50 on this bundle only)")
        else:
            print("(snapshot: native p50 not lower than reference p50 on this bundle)")

    section("Disclaimer")
    print(
        "Published metrics reflect this run_id at publish time. "
        "They are not a universal speedup claim and do not replace governance gates. "
        "See docs/PUBLIC_CLAIMS.md and docs/SOLVER_PATHS_AND_BATCHING.md."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
