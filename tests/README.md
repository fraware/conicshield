# Test layout (verification plan §15)

This tree uses **pytest markers** (`solver`, `requires_moreau`, `reference_correctness`, `slow`, …) as the primary way to filter runs. The plan also recommends **physical subtrees**; the following mapping is in place:

| Planned path | Role |
|--------------|------|
| `tests/reference/` | Reference correctness vs trusted public solvers (Layer C). Example: `test_reference_conic_correctness.py`. |
| `tests/` (flat) | Everything else: parity, governance, artifacts, bench, replay, smoke contracts, etc. |

Optional future subtrees (`tests/environment/`, `tests/smoke/`, `tests/native/`, `tests/performance/`, `tests/diff/`, `tests/artifacts/`, `tests/governance/`) can be introduced by moving files and keeping the same module names; pytest discovers tests under `tests/` recursively.

**Vendor-only reference tests:** run with `pytest -m "solver or requires_moreau"` (see `Makefile` `test-solver`).
