# Test layout

Target mapping to verification layers: [LAYERS.md](LAYERS.md).

This tree uses **pytest markers** (`solver`, `requires_moreau`, `reference_correctness`, `slow`, …) as the primary way to filter runs. Physical subtrees group ownership:

| Path | Role |
|------|------|
| `tests/environment/` | Repo hygiene, imports, pins, optional deps, metadata. |
| `tests/smoke/` | CLI `--help`, verification scripts, solver smoke contracts. |
| `tests/reference/` | Layer C: full MOREAU-vs-reference checks (`test_reference_conic_correctness.py`, vendor); CLARABEL/SCS-only suite shape (`test_reference_conic_trusted_shape.py`, default CI). |
| `tests/vendor/native/` | Native Moreau projector integration; includes CVXPY parity, batched compiled vs sequential checks, inter-sim shield batch path, and a dual-backend check (`CompiledSolver` vs legacy `moreau.Solver` via `NativeMoreauCompiledOptions.use_compiled_solver`). |
| `tests/performance/` | Performance summary JSON schema contract. |
| `tests/core/` | Small factory/API contracts (e.g. `solver_factory` single vs batch projectors). |
| `tests/vendor/diff/` | Layer F: `differentiation_check` contract, optional torch/jax micrograd probes, inter-sim shield FD on licensed hosts. |
| `tests/artifacts/` | Bundle / validator contracts. |
| `tests/governance/` | Finalize, release, audit, manifests, dashboard, **published-run index integrity**, **native-arm `summary.json` evidence vs `CURRENT.json`**. |
| `tests/parity/` | Parity replay and gate tests. |
| `tests/` (remaining) | Core shield, bench, replay, adapters, integration flows. |

**Vendor-only reference tests:** `pytest -m "solver or requires_moreau"` (see `Makefile` `test-solver`).
