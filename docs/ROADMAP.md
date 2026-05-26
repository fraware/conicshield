# Roadmap

This file tracks **external dependencies**, **deferred product semantics**, and a short **open backlog**. Operational commands live in [`MAINTAINER_RUNBOOK.md`](MAINTAINER_RUNBOOK.md).

## External integration (host-realistic bar)

- **inter-sim-rl:** The export → bank → `reference_run` → [`benchmarks/published_runs/<run_id>/`](../benchmarks/published_runs/README.md) → parity loop is **closed in-repo** with committed upstream-shaped export evidence ([`benchmarks/external_evidence/offline_graph_export_upstream.json`](../benchmarks/external_evidence/offline_graph_export_upstream.json)) and flagship published run [`host-realistic-20260525`](../benchmarks/published_runs/host-realistic-20260525/) at **`vendor_native`** (`real_projector`, native arm, green parity/promotion). Pin policy: `third_party/inter-sim-rl/` and [`INTER_SIM_RL_INTEGRATION.md`](INTER_SIM_RL_INTEGRATION.md). **Checklist:** [`HOST_REALISTIC_RUNBOOK.md`](HOST_REALISTIC_RUNBOOK.md). **Optional refresh:** replace the committed export with a **live** upstream dump when available (see runbook).

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
| **Host-realistic export loop** | Committed upstream-shaped export (`benchmarks/external_evidence/`), orchestration [`scripts/run_host_realistic_publish.py`](../scripts/run_host_realistic_publish.py), published run `host-realistic-20260525` with non-minimal `RUN_PROVENANCE.json`. |
| **Host-realistic vendor native (S3)** | `host-realistic-20260525`: family `current_run_id`, `evidence_tier: vendor_native`, `real_projector`, `parity_out/`, **published** governance with `shielded-native-moreau` in `publishable_arms`; repeatable cycle [`HOST_REALISTIC_REFRESH_PROCEDURE.md`](HOST_REALISTIC_REFRESH_PROCEDURE.md) + `make host-realistic-refresh-cycle`. |
| **Publish metadata** | `release_cli` preserves optional `benchmark_bundle_paths` / `external_artifact` on `CURRENT.json`; family README documents discovery. |
| **Native batching (first-class)** | `Backend.NATIVE_MOREAU_BATCH`; `create_batch_projector`; default `native_microbatch` vs `native_compiled_real_batch` rows in [`performance_benchmark.py`](../scripts/performance_benchmark.py); [`batch_solve_report.py`](../scripts/batch_solve_report.py). |
| **Published-run integrity** | [`PUBLISHED_RUN_INDEX.json`](../benchmarks/PUBLISHED_RUN_INDEX.json) schema v2: required + optional on-disk files indexed; `assert_index_covers_present_optional_files` in CI/index `--check`. |
| **CI merge gates** | Documented required checks (`quality`, `conic-trusted-shape`, `solver-touch`, `governance-audit`); hybrid path-triggered `vendor-ci-moreau` on upstream PRs ([`docs/CI_MERGE_GATES.md`](CI_MERGE_GATES.md), [`docs/BRANCH_PROTECTION.md`](BRANCH_PROTECTION.md)); **binding maintainer attestation** for solver-touch merges. |
| **Conic suite scale** | Larger sparse LP / SOCP regimes in [`conicshield/reference_correctness/conic_suite.py`](../conicshield/reference_correctness/conic_suite.py); grouping tests in [`tests/reference/test_reference_conic_grouping.py`](../tests/reference/test_reference_conic_grouping.py); `standard` / `stress` trusted-shape CI unchanged. |
| **Test layout map** | [`tests/STRUCTURE.md`](../tests/STRUCTURE.md), [`tests/LAYERS.md`](../tests/LAYERS.md), [`tests/README.md`](../tests/README.md); incremental moves from repo-root `tests/test_*.py`. |
| **Shield batch + differentiation** | `InterSimConicShield.project_softmax_batch` (native); vendor FD on inter-sim shield path; `python scripts/differentiation_check.py --shield-inter-sim` on licensed hosts (Layer F validation only; autograd product claim deferred). |
| **Reporting** | [`scripts/conic_suite_report.py`](../scripts/conic_suite_report.py) — JSON summary of trusted conic runs by case (public solvers). |

---

## Open backlog (priority order)

What is **not** closed or only partially addressed:

1. **Live inter-sim re-export** — **Operational path shipped:** `make capture-inter-sim-graph` → `make refresh-live-upstream-export-live` → `make host-realistic-refresh-cycle` (or `--live-graph-json`). **Remaining:** re-capture when upstream `REVISION` sha changes or a richer Maps-built graph exists on a patched host.
2. **Shield autograd vs finite differences** — **Decision: defer autograd product claim.** Inter-sim shield **FD** (`tests/vendor/diff/`) and `python scripts/differentiation_check.py --shield-inter-sim` support internal validation only; **autograd / `enable_grad` vs FD** on the production shield QP remains out of scope for external narrative until explicitly promoted.
3. **Conic suite: failure clustering** — `conic_suite_report.py` emits `clusters.by_family` and `families_with_failures`; optional committed CI artifacts under `benchmarks/reports/`.
4. **Physical test tree** — Continue incremental moves per [`tests/STRUCTURE.md`](../tests/STRUCTURE.md); no mass rename required for correctness.
5. **Second benchmark family** — [`conicshield-shield-qp-micro-v1`](../benchmarks/releases/conicshield-shield-qp-micro-v1/FAMILY_README.md) is scaffold-only (`current_run_id: null`) until you publish a real run and bundles.
6. **Follow-on product** — Retraining comparisons, richer proof metadata, second benchmark host — each needs a family manifest and governance review.

---

## After first governed publish

Possible follow-ons (not blocking core development): items in **Open backlog** and any new family forks when the task contract changes materially.

## v2 direction

See [`V2_STRATEGY.md`](V2_STRATEGY.md) — **Option A (deepen same family)** is the active default.

## Where to run commands

[`MAINTAINER_RUNBOOK.md`](MAINTAINER_RUNBOOK.md). Host-realistic refresh: [`HOST_REALISTIC_REFRESH_PROCEDURE.md`](HOST_REALISTIC_REFRESH_PROCEDURE.md). Merge law: [`REVIEWER_MERGE_CHECKLIST.md`](REVIEWER_MERGE_CHECKLIST.md). Solver paths: [`SOLVER_PATHS_AND_BATCHING.md`](SOLVER_PATHS_AND_BATCHING.md).
