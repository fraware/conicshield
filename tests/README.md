# Test layout

Target mapping to verification layers: [LAYERS.md](LAYERS.md).

This tree uses **pytest markers** (`solver`, `requires_moreau`, `reference_correctness`, `slow`, …) as the primary way to filter runs. Physical subtrees group ownership:

| Path | Role |
|------|------|
| `tests/environment/` | Repo hygiene, imports, pins, optional deps, metadata. |
| `tests/smoke/` | CLI `--help`, verification scripts, solver smoke contracts. |
| `tests/reference/` | Layer C: full MOREau-vs-reference checks (`test_reference_conic_correctness.py`, vendor); CLARABEL/SCS-only suite shape (`test_reference_conic_trusted_shape.py`, default CI). |
| `tests/vendor/native/` | Native Moreau projector integration; includes CVXPY parity and a dual-backend check (`CompiledSolver` vs legacy `moreau.Solver` via `NativeMoreauCompiledOptions.use_compiled_solver`). |
| `tests/performance/` | Performance summary JSON schema contract. |
| `tests/vendor/diff/` | Layer F differentiation script and optional torch/jax micrograd probes. |
| `tests/artifacts/` | Bundle / validator contracts. |
| `tests/governance/` | Finalize, release, audit, manifests, dashboard. |
| `tests/parity/` | Parity replay and gate tests. |
| `tests/` (remaining) | Core shield, bench, replay, adapters, integration flows. |

**Vendor-only reference tests:** `pytest -m "solver or requires_moreau"` (see `Makefile` `test-solver`).
