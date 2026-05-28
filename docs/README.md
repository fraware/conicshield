# Documentation index

Start here after the repository [`README.md`](../README.md).

**External users:** [COMMUNITY_LAYER.md](COMMUNITY_LAYER.md) (quickstarts + API + examples in one page).

## Start by audience

| You are | Start here |
|---------|------------|
| Researcher (inspect / cite bundles) | [QUICKSTART_RESEARCHER.md](QUICKSTART_RESEARCHER.md) |
| Integrator (use the library) | [QUICKSTART_INTEGRATOR.md](QUICKSTART_INTEGRATOR.md) |
| Maintainer (publish / refresh) | [QUICKSTART_MAINTAINER.md](QUICKSTART_MAINTAINER.md) |

Public claim boundaries: [PUBLIC_CLAIMS.md](PUBLIC_CLAIMS.md). Examples: [examples/README.md](../examples/README.md).

## v1 reference system (read first)

| Document | Use when |
|----------|----------|
| [REFERENCE_SYSTEM.md](REFERENCE_SYSTEM.md) | Auditor one-page map + status JSON |
| [V1_LOCK_CHECKLIST.md](V1_LOCK_CHECKLIST.md) | Pre-lock verification (`make verify-v1-lock`) |
| [REFERENCE_AUTHORITY.md](REFERENCE_AUTHORITY.md) | Flagship `host-realistic-20260525`, gates, closed loop |
| [HOST_REALISTIC_CADENCE_POLICY.md](HOST_REALISTIC_CADENCE_POLICY.md) | Monthly + immediate refresh triggers |
| [REFERENCE_AUTHORITY_LOG.md](REFERENCE_AUTHORITY_LOG.md) | Durable refresh log |
| [REFERENCE_REFRESH_LOG.md](REFERENCE_REFRESH_LOG.md) | Legacy pointer → authority log |
| [PUBLISHED_RUN_INDEX_FOR_CONSUMERS.md](PUBLISHED_RUN_INDEX_FOR_CONSUMERS.md) | External bundle consumption |
| [PUBLISHED_RUN_INDEX_SCHEMA.md](PUBLISHED_RUN_INDEX_SCHEMA.md) | Index stability contract |
| [COMMUNITY_METADATA_SCHEMA.md](COMMUNITY_METADATA_SCHEMA.md) | `COMMUNITY_METADATA.json` fields |
| [PUBLISHED_RUNS_API.md](PUBLISHED_RUNS_API.md) | `conicshield.published_runs` reference |
| [CITING_CONICSHIELD_ARTIFACTS.md](CITING_CONICSHIELD_ARTIFACTS.md) | How to cite runs and index |
| [HOST_REALISTIC_REFRESH_PROCEDURE.md](HOST_REALISTIC_REFRESH_PROCEDURE.md) | Maintainer refresh commands |
| [REFERENCE_EVIDENCE_TIERS.md](REFERENCE_EVIDENCE_TIERS.md) | `evidence_tier` S0–S3 |
| [CI_MERGE_GATES.md](CI_MERGE_GATES.md) | Required GitHub checks, Policy B |
| [REVIEWER_MERGE_CHECKLIST.md](REVIEWER_MERGE_CHECKLIST.md) | Merge sign-off |

## Benchmark publish and artifacts

| Document | Use when |
|----------|----------|
| [MAINTAINER_RUNBOOK.md](MAINTAINER_RUNBOOK.md) | validate → parity → finalize → release → audit |
| [BENCHMARK_GOVERNANCE.md](BENCHMARK_GOVERNANCE.md) | States, gates, family bump |
| [RELEASE_POLICY.md](RELEASE_POLICY.md) | `release_cli` vs hand-edited `CURRENT.json` |
| [PUBLISHED_BUNDLE_CATALOG.md](PUBLISHED_BUNDLE_CATALOG.md) | Files per bundle; `validate_published_bundle_profile.py` |
| [HOST_REALISTIC_RUNBOOK.md](HOST_REALISTIC_RUNBOOK.md) | Step-by-step host-realistic proof |
| [NATIVE_ARM_PUBLISH_CHECKLIST.md](NATIVE_ARM_PUBLISH_CHECKLIST.md) | `shielded-native-moreau` in `publishable_arms` |
| [PARITY_AND_FIXTURES.md](PARITY_AND_FIXTURES.md) | Frozen `parity_reference/` policy |

## Solver, batch, upstream

| Document | Use when |
|----------|----------|
| [SOLVER_PATHS_AND_BATCHING.md](SOLVER_PATHS_AND_BATCHING.md) | Reference / sequential native / compiled batch; acceptance tiers |
| [MOREAU_INSTALL_AND_ENVIRONMENT_POLICY.md](MOREAU_INSTALL_AND_ENVIRONMENT_POLICY.md) | Licensed install |
| [MOREAU_API_NOTES.md](MOREAU_API_NOTES.md) | API drift |
| [INTER_SIM_RL_INTEGRATION.md](INTER_SIM_RL_INTEGRATION.md) | Pin, export contract, capture path |
| [DIFFERENTIATION_PUBLIC_STANCE.md](DIFFERENTIATION_PUBLIC_STANCE.md) | FD validation only; no autograd product claim |

## Engineering record

| Document | Use when |
|----------|----------|
| [ENGINEERING_STATUS.md](ENGINEERING_STATUS.md) | In-tree vs vendor-only; validated solver versions |
| [ROADMAP.md](ROADMAP.md) | Closed milestones, open backlog |
| [V2_STRATEGY.md](V2_STRATEGY.md) | Option A default; B/C deferred |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Layered design |
| [VERIFICATION_AND_STRESS_TEST_PLAN.md](VERIFICATION_AND_STRESS_TEST_PLAN.md) | Trust layers A–G |
| [DEVENV.md](DEVENV.md) | Python, pytest markers, workflows |
| [CONTRIBUTING.md](../CONTRIBUTING.md) | PR requirements |
| [adr/001-progress-clearance-constraints.md](adr/001-progress-clearance-constraints.md) | `progress` / `clearance` not implemented |

**Dashboard:** `dashboard_cli`, `generate_trust_dashboard` — [MAINTAINER_RUNBOOK.md](MAINTAINER_RUNBOOK.md). Pointer: [`benchmarks/DASHBOARD_README.md`](../benchmarks/DASHBOARD_README.md).
