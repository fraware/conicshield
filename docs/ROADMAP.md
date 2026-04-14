# Roadmap

This file tracks **external dependencies**, **deferred product semantics**, and a short **open backlog**. Operational commands live in [`MAINTAINER_RUNBOOK.md`](MAINTAINER_RUNBOOK.md).

## External integration (host-realistic bar)

- **inter-sim-rl:** Production benchmarks still assume a real offline graph export and transition bank from the patched host, not only minimal JSON fixtures. Pin policy: `third_party/inter-sim-rl/` and [`INTER_SIM_RL_INTEGRATION.md`](INTER_SIM_RL_INTEGRATION.md). The full loop (export → bank → `reference_run` → [`benchmarks/published_runs/<run_id>/`](../benchmarks/published_runs/README.md) → parity) remains the acceptance bar for **host-realistic** evidence; that loop is **not** fully demonstrated with a live upstream export in-repo yet.

## Solver and parity (operations)

- **Validated solver versions:** After a green **Vendor CI** (`vendor-ci-moreau`) or licensed local run, update [`ENGINEERING_STATUS.md`](ENGINEERING_STATUS.md) from `solver_versions.json`.
- **Parity fixture:** The frozen stream under `tests/fixtures/parity_reference/` is **promoted from a committed governed bundle** (`benchmarks/published_runs/wsl-real-20260409-132450/`). See [`REGENERATION_NOTE.md`](../tests/fixtures/parity_reference/REGENERATION_NOTE.md) and [`PARITY_AND_FIXTURES.md`](PARITY_AND_FIXTURES.md).

## Deferred product semantics

- **`progress` and `clearance`** constraint kinds in `SafetySpec` are not implemented for projection. See [adr/001-progress-clearance-constraints.md](adr/001-progress-clearance-constraints.md).

---

## Closed milestones (benchmark governance v1 cycle)

The following were delivered and are kept auditable in Git:

| Milestone | What shipped |
|-----------|----------------|
| **Parity gold + bundles** | Committed bundles under `benchmarks/published_runs/` (`wsl-real-*`, `wsl-native-*` per `CURRENT.json` / `benchmark_bundle_paths`); fixture regenerated from the real reference bundle; updated `REGENERATION_NOTE.md`. |
| **Publish metadata** | `release_cli` preserves optional `benchmark_bundle_paths` / `external_artifact` on `CURRENT.json`; family README documents discovery. |
| **Native batching** | `NativeMoreauCompiledBatchProjector` + `test_batched_compiled_matches_sequential_native`; default `performance_benchmark.py` compares sequential microbatch vs `native_compiled_real_batch`. |
| **CI** | Always-on `conic-trusted-shape` + `quality`; path-triggered [`.github/workflows/solver-touch.yml`](../.github/workflows/solver-touch.yml) (index check, governance parity/native evidence tests, parity). |
| **Conic suite scale** | Larger sparse LP / SOCP regimes in [`conicshield/reference_correctness/conic_suite.py`](../conicshield/reference_correctness/conic_suite.py); grouping tests in [`tests/reference/test_reference_conic_grouping.py`](../tests/reference/test_reference_conic_grouping.py); `standard` / `stress` trusted-shape CI unchanged. |
| **Test layout map** | [`tests/STRUCTURE.md`](../tests/STRUCTURE.md), [`tests/LAYERS.md`](../tests/LAYERS.md), [`tests/README.md`](../tests/README.md); incremental moves from repo-root `tests/test_*.py`. |
| **Shield batch + differentiation** | `InterSimConicShield.project_softmax_batch` (native); vendor FD on inter-sim shield path; `python scripts/differentiation_check.py --shield-inter-sim` on licensed hosts. |
| **Reporting** | [`scripts/conic_suite_report.py`](../scripts/conic_suite_report.py) — JSON summary of trusted conic runs by case (public solvers). |

---

## Open backlog (priority order)

What is **not** closed or only partially addressed:

1. **Host-realistic substrate** — One real upstream `inter-sim-rl` export through the full publish + parity loop (see [External integration](#external-integration-host-realistic-bar)).
2. **Vendor trust on every merge** — Policy choice: require `vendor-ci-moreau` or manual pre-merge runs for PRs touching native/Moreau (default CI stays public-solver-only by design).
3. **Shield autograd vs finite differences** — Inter-sim shield **FD** and `differentiation_check.py --shield-inter-sim` exist; **autograd / `enable_grad` vs FD** on the production shield QP remains a vendor follow-on when differentiability is part of the public story.
4. **Conic suite: failure clustering** — Optional richer **CI artifacts** or dashboards aggregating `conic_suite_report.py` by regime (suite rows already carry case metadata).
5. **Physical test tree** — Continue incremental moves per [`tests/STRUCTURE.md`](../tests/STRUCTURE.md); no mass rename required for correctness.
6. **Follow-on product** — Retraining comparisons, richer proof metadata, second benchmark host — each needs a family manifest and governance review.

---

## After first governed publish

Possible follow-ons (not blocking core development): items in **Open backlog** and any new family forks when the task contract changes materially.

## Where to run commands

[`MAINTAINER_RUNBOOK.md`](MAINTAINER_RUNBOOK.md). Verification layers: [`VERIFICATION_AND_STRESS_TEST_PLAN.md`](VERIFICATION_AND_STRESS_TEST_PLAN.md).
