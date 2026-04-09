# Test layout

This tree uses **pytest markers** (`solver`, `requires_moreau`, `reference_correctness`, `slow`, …) as the primary way to filter runs. Physical subtrees group ownership:

| Path | Role |
|------|------|
| `tests/environment/` | Repo hygiene, imports, pins, optional deps, metadata. |
| `tests/smoke/` | CLI `--help`, verification scripts, solver smoke contracts. |
| `tests/reference/` | Layer C: reference correctness vs trusted public solvers (`test_reference_conic_correctness.py`). |
| `tests/native/` | Native Moreau projector integration. |
| `tests/performance/` | Performance summary JSON schema contract. |
| `tests/diff/` | Layer F differentiation script and optional torch/jax micrograd probes. |
| `tests/artifacts/` | Bundle / validator contracts. |
| `tests/governance/` | Finalize, release, audit, manifests, dashboard. |
| `tests/parity/` | Parity replay and gate tests. |
| `tests/` (remaining) | Core shield, bench, replay, adapters, integration flows. |

**Vendor-only reference tests:** `pytest -m "solver or requires_moreau"` (see `Makefile` `test-solver`).
