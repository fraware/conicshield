#!/usr/bin/env python3
"""Compare reference vs native arm metrics from flagship summary.json."""

from __future__ import annotations

from conicshield.published_runs import load_summary

REFERENCE = "shielded-rules-plus-geometry"
NATIVE = "shielded-native-moreau"


def main() -> int:
    rows = {r.label: r for r in load_summary("host-realistic-20260525")}
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
    print("\nThis compares published benchmark metrics only — not a universal speedup claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
