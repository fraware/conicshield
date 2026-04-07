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

- Single-problem API: `moreau.Solver(P, q, A, b, cones=cones, settings=settings)` then `solution = solver.solve(warm_start=...)`.
- `solver.info` exposes solve metadata (status, timings, iterations, etc.).
- Warm start: optional `WarmStart` from `solution.to_warm_start()` on a previous solve.

## License

- `solve()` requires a valid key via `MOREAU_LICENSE_KEY`, `.moreau_key`, `~/.moreau/key`, or `~/.moreau_key` (vendor order).

## Version pinning

- **Declared lower bounds** live in `pyproject.toml` under `[project.optional-dependencies] solver` (`cvxpy>=1.8.2`, `cvxpylayers>=1.0.4`, `moreau[cuda]`).
- **Exact versions** used in a known-good environment belong in `ENGINEERING_STATUS.md` under **Validated solver stack** after you run solver CI or `make test-solver` with a license and copy `pip freeze` output for `moreau`, `cvxpy`, and `cvxpylayers`.
- The **Vendor CI track** (`vendor-ci-moreau`) prints a filtered `pip freeze` (those three packages) into the GitHub Actions job Summary on each successful dispatch; use that block when updating the table after upgrades or before a governed publish.

## Vendor upgrade checklist (re-audit bindings)

When bumping `moreau`, `cvxpy`, or `cvxpylayers` (or Python minor), walk this list and update [`ENGINEERING_STATUS.md`](../ENGINEERING_STATUS.md) **Validated solver stack** after a green **Vendor CI track** run (`vendor-ci-moreau`) or licensed local run.

| File | Re-verify |
| ---- | -------- |
| [`conicshield/specs/compiler.py`](../conicshield/specs/compiler.py) | `cp.MOREAU` availability; kwargs to `problem.solve()` (`device`, `max_iter`, `verbose`, `time_limit`, `ipm_settings`); telemetry via `extract_cvxpy_telemetry` / problem value types. |
| [`conicshield/core/moreau_compiled.py`](../conicshield/core/moreau_compiled.py) | `moreau.Solver` construction; `Cones`, `Settings` fields; `solve()` return shape; `solver.info` attribute names and types; `WarmStart` / `to_warm_start()` lifecycle. |
| [`conicshield/core/solver_factory.py`](../conicshield/core/solver_factory.py) | Backend dispatch; optional-extra error messages; projector construction for reference vs native. |
| Tests | `make test-solver` or Vendor CI track (`vendor-ci-moreau`); [`conicshield/core/solver_smoke_cli.py`](../conicshield/core/solver_smoke_cli.py) reference + native arms. |

If the vendor changes status strings or timing fields, update [`conicshield/core/telemetry.py`](../conicshield/core/telemetry.py) `normalize_moreau_info` and any strict parity comparisons in tests.

## See also (in-repo)

- [MOREAU_INSTALL_AND_ENVIRONMENT_POLICY.md](MOREAU_INSTALL_AND_ENVIRONMENT_POLICY.md)
- [NATIVE_PARITY_POLICY.md](NATIVE_PARITY_POLICY.md), [PERFORMANCE_BENCHMARKING_POLICY.md](PERFORMANCE_BENCHMARKING_POLICY.md)
- [DIFFERENTIATION_VALIDATION_POLICY.md](DIFFERENTIATION_VALIDATION_POLICY.md)
