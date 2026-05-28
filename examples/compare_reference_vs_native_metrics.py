#!/usr/bin/env python3
"""Compare reference vs native arm metrics from flagship summary.json.

Audience: researcher inspecting published benchmark metrics.
Prerequisites: ``pip install -e .``; flagship bundle committed in repo.
Proves: ``load_summary`` can read per-arm p50 solve times from a published bundle.
Does not prove: universal speedup, production readiness, or that governance would
  approve a stronger claim — metric comparison is informative only.
Expected: prints two p50_ms lines and a native/reference ratio when both arms exist.
"""

from __future__ import annotations

from conicshield.published_runs import load_run, load_summary, verify_run

REFERENCE = "shielded-rules-plus-geometry"
NATIVE = "shielded-native-moreau"
FLAGSHIP = "host-realistic-20260525"


def main() -> int:
    verify_run(FLAGSHIP)
    bundle = load_run(FLAGSHIP)
    gov = bundle.governance_status or {}
    print("governance state:", gov.get("state"), "(metrics do not override this)")

    rows = {r.label: r for r in load_summary(FLAGSHIP)}
    if REFERENCE not in rows or NATIVE not in rows:
        print("Missing expected arms in summary.json")
        return 1
    ref = rows[REFERENCE]
    nat = rows[NATIVE]
    print(f"{REFERENCE} p50_ms={ref.solve_time_p50_ms}")
    print(f"{NATIVE} p50_ms={nat.solve_time_p50_ms}")
    if ref.solve_time_p50_ms and nat.solve_time_p50_ms:
        ratio = float(nat.solve_time_p50_ms) / float(ref.solve_time_p50_ms)
        print(f"native/reference p50 ratio: {ratio:.3f}")
    print(
        "\nDisclaimer: published metrics at publish time only. "
        "Not a universal speedup claim. See docs/PUBLIC_CLAIMS.md and "
        "docs/SOLVER_PATHS_AND_BATCHING.md."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
