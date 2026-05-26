# Documentation

Policy and runbooks for ConicShield. The repository root [`README.md`](../README.md) lists everything in one map.

| Document | Purpose |
|----------|---------|
| [REFERENCE_AUTHORITY.md](REFERENCE_AUTHORITY.md) | Flagship release, closed loop, maintainer gates |
| [HOST_REALISTIC_REFRESH_PROCEDURE.md](HOST_REALISTIC_REFRESH_PROCEDURE.md) | Repeatable host-realistic refresh cycle |
| [REVIEWER_MERGE_CHECKLIST.md](REVIEWER_MERGE_CHECKLIST.md) | Binding merge checklist (Policy B) |
| [PUBLISHED_BUNDLE_CATALOG.md](PUBLISHED_BUNDLE_CATALOG.md) | Published bundle artifact catalog |
| [DIFFERENTIATION_PUBLIC_STANCE.md](DIFFERENTIATION_PUBLIC_STANCE.md) | Public claims vs deferred autograd |
| [V2_STRATEGY.md](V2_STRATEGY.md) | v2 direction (Option A default) |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System layers and design intent |
| [ENGINEERING_STATUS.md](ENGINEERING_STATUS.md) | What ships in-tree vs vendor-only |
| [ROADMAP.md](ROADMAP.md) | External deps, closed milestones, open backlog |
| [MAINTAINER_RUNBOOK.md](MAINTAINER_RUNBOOK.md) | Commands, publish flow, CI notes |
| [HOST_REALISTIC_RUNBOOK.md](HOST_REALISTIC_RUNBOOK.md) | Flagship host-realistic loop (closed in-repo; live export path documented) |
| [REFERENCE_REFRESH_LOG.md](REFERENCE_REFRESH_LOG.md) | Flagship refresh cadence record |
| [SOLVER_PATHS_AND_BATCHING.md](SOLVER_PATHS_AND_BATCHING.md) | Reference vs sequential native vs compiled batch |
| [BENCHMARK_GOVERNANCE.md](BENCHMARK_GOVERNANCE.md) | How benchmark claims are published |
| [NATIVE_ARM_PUBLISH_CHECKLIST.md](NATIVE_ARM_PUBLISH_CHECKLIST.md) | Steps to get `shielded-native-moreau` into `publishable_arms` |
| [RELEASE_POLICY.md](RELEASE_POLICY.md) | Same-family vs new-family release; no ad-hoc `CURRENT.json` edits |
| [VERIFICATION_AND_STRESS_TEST_PLAN.md](VERIFICATION_AND_STRESS_TEST_PLAN.md) | Trust ladder, layers, policies |
| [PARITY_AND_FIXTURES.md](PARITY_AND_FIXTURES.md) | Frozen fixture and native parity |
| [DEVENV.md](DEVENV.md) | Python matrix, pytest markers, workflows |
| [CONTRIBUTING.md](../CONTRIBUTING.md) | Contributor workflow, hybrid vendor policy, published-bundle rules |
| [REFERENCE_EVIDENCE_TIERS.md](REFERENCE_EVIDENCE_TIERS.md) | S0–S3 evidence tiers for published runs |
| [CI_MERGE_GATES.md](CI_MERGE_GATES.md) | Required checks and binding vendor attestation for solver-touch merges |
| [BRANCH_PROTECTION.md](BRANCH_PROTECTION.md) | GitHub branch protection checklist (vendor-ci not required; attestation binding) |
| [INTER_SIM_RL_INTEGRATION.md](INTER_SIM_RL_INTEGRATION.md) | Host integration |
| [MOREAU_INSTALL_AND_ENVIRONMENT_POLICY.md](MOREAU_INSTALL_AND_ENVIRONMENT_POLICY.md) | Vendor install expectations |
| [MOREAU_API_NOTES.md](MOREAU_API_NOTES.md) | API drift and upgrade checks |
| [adr/001-progress-clearance-constraints.md](adr/001-progress-clearance-constraints.md) | Deferred `progress` / `clearance` constraint kinds |

**Dashboard:** registry view via `dashboard_cli` and unified `generate_trust_dashboard` — [MAINTAINER_RUNBOOK.md](MAINTAINER_RUNBOOK.md). Short pointer: [`benchmarks/DASHBOARD_README.md`](../benchmarks/DASHBOARD_README.md).
