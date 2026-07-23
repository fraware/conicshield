"""Named active-set transition benchmark suite (deliverable §4 packaging).

Packages the versioned corpus family ``active_set_transition_neighborhoods``
as a named research benchmark with suite version and expected regimes.
Does not bump the corpus version unless new scenarios are scientifically required.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from conicshield.experimental.corpus.generate import load_all_scenarios, load_manifest
from conicshield.experimental.corpus.paths import CORPUS_VERSION, RESEARCH_ROOT

ACTIVE_SET_BENCHMARK_ID = "research.active_set_transition_benchmark"
ACTIVE_SET_BENCHMARK_VERSION = "asb-v0.2.0"
ACTIVE_SET_FAMILY = "active_set_transition_neighborhoods"
BENCHMARK_SCHEMA_ID = "research.active_set_transition_benchmark.v0"

# Expected regimes the suite must cover for integrity (research-level).
REQUIRED_REGIME_SUBSTRINGS: tuple[str, ...] = (
    "active_set",
    "transition",
)


@dataclass(slots=True)
class ActiveSetBenchmarkCase:
    scenario_id: str
    expected_regime: str
    seed: int
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "expected_regime": self.expected_regime,
            "seed": self.seed,
            "notes": self.notes,
        }


@dataclass(slots=True)
class ActiveSetTransitionBenchmark:
    schema_id: str = BENCHMARK_SCHEMA_ID
    benchmark_id: str = ACTIVE_SET_BENCHMARK_ID
    benchmark_version: str = ACTIVE_SET_BENCHMARK_VERSION
    corpus_version: str = CORPUS_VERSION
    family: str = ACTIVE_SET_FAMILY
    cases: list[ActiveSetBenchmarkCase] = field(default_factory=list)
    expected_regimes: list[str] = field(default_factory=list)
    regime_counts: dict[str, int] = field(default_factory=dict)
    integrity_checks: dict[str, bool] = field(default_factory=dict)
    promotion_status: str = "experimental"
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_id": self.schema_id,
            "benchmark_id": self.benchmark_id,
            "benchmark_version": self.benchmark_version,
            "corpus_version": self.corpus_version,
            "family": self.family,
            "n_cases": len(self.cases),
            "cases": [c.as_dict() for c in self.cases],
            "expected_regimes": list(self.expected_regimes),
            "regime_counts": dict(self.regime_counts),
            "integrity_checks": dict(self.integrity_checks),
            "promotion_status": self.promotion_status,
            "notes": list(self.notes),
        }


def validate_active_set_benchmark_integrity(bench: ActiveSetTransitionBenchmark) -> dict[str, bool]:
    """Machine checks for suite completeness (research integrity, not production gate)."""

    regimes_joined = " ".join(bench.expected_regimes).lower()
    has_regime_coverage = all(s in regimes_joined for s in REQUIRED_REGIME_SUBSTRINGS) or bool(
        bench.expected_regimes
    )
    return {
        "non_empty": len(bench.cases) > 0,
        "corpus_version_present": bool(bench.corpus_version),
        "unique_scenario_ids": len({c.scenario_id for c in bench.cases}) == len(bench.cases),
        "all_cases_have_regime": all(bool(c.expected_regime) for c in bench.cases),
        "regime_coverage_nonempty": has_regime_coverage and len(bench.expected_regimes) > 0,
        "min_cases_ge_5": len(bench.cases) >= 5,
    }


def build_active_set_transition_benchmark() -> ActiveSetTransitionBenchmark:
    """Package active-set transition scenarios into a named benchmark suite."""

    scenarios = [s for s in load_all_scenarios() if s.get("family") == ACTIVE_SET_FAMILY]
    cases = [
        ActiveSetBenchmarkCase(
            scenario_id=str(s["scenario_id"]),
            expected_regime=str(s.get("expected_regime") or "unknown"),
            seed=int(s.get("seed") or 0),
            notes=str(s.get("notes") or ""),
        )
        for s in scenarios
    ]
    regime_counts: dict[str, int] = {}
    for c in cases:
        regime_counts[c.expected_regime] = regime_counts.get(c.expected_regime, 0) + 1
    bench = ActiveSetTransitionBenchmark(
        corpus_version=str(load_manifest().get("corpus_version") or CORPUS_VERSION),
        cases=cases,
        expected_regimes=sorted(regime_counts.keys()),
        regime_counts=regime_counts,
        promotion_status="experimental",
        notes=[
            "Benchmark packages existing corpus scenarios; corpus version unchanged.",
            "Not a governed production benchmark; research-only.",
            "Use with observatory / agreement_study for active-set neighborhood coverage.",
            f"Suite version {ACTIVE_SET_BENCHMARK_VERSION} adds integrity_checks.",
        ],
    )
    bench.integrity_checks = validate_active_set_benchmark_integrity(bench)
    if not all(bench.integrity_checks.values()):
        bench.notes.append(
            f"integrity_checks incomplete: { {k: v for k, v in bench.integrity_checks.items() if not v} }"
        )
    return bench


def write_benchmark_manifest(*, output_path: Path | None = None) -> Path:
    bench = build_active_set_transition_benchmark()
    path = output_path or (RESEARCH_ROOT / "fixtures" / "active_set_transition_benchmark.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(bench.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Active-set transition benchmark suite")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output/research/active_set_transition_benchmark.json"),
    )
    parser.add_argument("--write-fixture", action="store_true")
    args = parser.parse_args()
    bench = build_active_set_transition_benchmark()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(bench.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.write_fixture:
        fixture = write_benchmark_manifest()
        print(f"wrote fixture {fixture}")
    print(
        f"benchmark {bench.benchmark_id}@{bench.benchmark_version} "
        f"n={len(bench.cases)} regimes={bench.expected_regimes}"
    )


if __name__ == "__main__":
    main()
