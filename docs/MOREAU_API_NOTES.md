# Moreau API notes (ConicShield integration)

This file records how ConicShield calls Moreau and CVXPY, with pointers to vendor documentation. Re-verify when upgrading `moreau`, `cvxpy`, or `cvxpylayers`.

## Documentation

- Installation and license: https://docs.moreau.so/installation.html
- CVXPY integration (solver settings, `cp.MOREAU`): https://docs.moreau.so/guide/cvxpy-integration.html
- Core API (`moreau.Solver`, `CompiledSolver`, `Cones`, `Settings`, `solve`, `solver.info`): https://docs.moreau.so/api/core.html
- CVXPY examples: https://docs.moreau.so/examples/cvxpy.html

## Reference path (CVXPY + Moreau)

- Solver constant: `problem.solve(solver=cp.MOREAU, ...)`.
- Settings passed as kwargs to `solve()`: `device`, `max_iter`, `verbose`, `time_limit`, nested `ipm_settings` dict (see vendor guide).
- Requires `cvxpy>=1.8.2`, `cvxpylayers>=1.0.4`, and a licensed `moreau` install for `solve()` to succeed.

## Native path (NumPy / SciPy sparse)

- **Production-style shared structure:** `moreau.CompiledSolver(n, m, P_row_offsets, P_col_indices, A_row_offsets, A_col_indices, cones, settings)` with `settings.batch_size=1` for per-step shield solves; each step calls `setup(P_values, A_values)` then `solve(qs, bs, warm_start=...)`. ConicShield’s `NativeMoreauCompiledProjector` uses this path by default (`NativeMoreauCompiledOptions.use_compiled_solver=True`).
- **Legacy single-build API:** `moreau.Solver(P, q, A, b, cones=cones, settings=settings)` then `solution = solver.solve(warm_start=...)` (still available via `use_compiled_solver=False`).
- `solver.info` exposes solve metadata (status, timings, iterations, etc.); batched metadata is reduced to the first batch row where needed for telemetry parity.
- Warm start: `WarmStart` / `BatchedWarmStart` from `solution.to_warm_start()` on a previous solve.

## License

- `solve()` requires a valid key via `MOREAU_LICENSE_KEY`, `.moreau_key`, `~/.moreau/key`, or `~/.moreau_key` (vendor order).

## Version pinning

- **Declared lower bounds** live in `pyproject.toml` under `[project.optional-dependencies] solver` (`cvxpy>=1.8.2`, `cvxpylayers>=1.0.4`, `moreau[cuda]`).
- **Exact versions** used in a known-good environment belong in `ENGINEERING_STATUS.md` under **Validated solver stack** after you run solver CI or `make test-solver` with a license and copy `pip freeze` output for `moreau`, `cvxpy`, and `cvxpylayers`.
- The **Vendor CI track** (`vendor-ci-moreau`) prints a filtered `pip freeze` (those three packages) into the GitHub Actions job Summary on each successful dispatch; use that block when updating the table after upgrades or before a governed publish.

## Vendor upgrade checklist (re-audit bindings)

When bumping `moreau`, `cvxpy`, or `cvxpylayers` (or Python minor), walk this list and update [`ENGINEERING_STATUS.md`](ENGINEERING_STATUS.md) **Validated solver stack** after a green **Vendor CI track** run (`vendor-ci-moreau`) or licensed local run.

| File | Re-verify |
| ---- | -------- |
| [`conicshield/specs/compiler.py`](../conicshield/specs/compiler.py) | `cp.MOREAU` availability; kwargs to `problem.solve()` (`device`, `max_iter`, `verbose`, `time_limit`, `ipm_settings`); telemetry via `extract_cvxpy_telemetry` / problem value types. |
| [`conicshield/core/moreau_compiled.py`](../conicshield/core/moreau_compiled.py) | `moreau.CompiledSolver` construction (CSR structure + `setup`/`solve`); fallback `moreau.Solver`; `Cones`, `Settings` (`batch_size=1`); batched vs single `solve()` return shapes; `solver.info` / batched telemetry; `WarmStart` / `BatchedWarmStart` / `to_warm_start()`. |
| [`conicshield/core/solver_factory.py`](../conicshield/core/solver_factory.py) | Backend dispatch; optional-extra error messages; projector construction for reference vs native. |
| Tests | `make test-solver` or Vendor CI track (`vendor-ci-moreau`); [`conicshield/core/solver_smoke_cli.py`](../conicshield/core/solver_smoke_cli.py) reference + native arms; [`tests/vendor/native/test_native_moreau_projector.py`](../tests/vendor/native/test_native_moreau_projector.py) asserts CVXPY parity for both native paths (`test_native_compiled_and_legacy_match_reference`). |

If the vendor changes status strings or timing fields, update [`conicshield/core/telemetry.py`](../conicshield/core/telemetry.py) `normalize_moreau_info` and any strict parity comparisons in tests.

## See also (in-repo)

- [MOREAU_INSTALL_AND_ENVIRONMENT_POLICY.md](MOREAU_INSTALL_AND_ENVIRONMENT_POLICY.md)
- [PARITY_AND_FIXTURES.md](PARITY_AND_FIXTURES.md), [VERIFICATION_AND_STRESS_TEST_PLAN.md](VERIFICATION_AND_STRESS_TEST_PLAN.md) (performance and differentiation sections)
