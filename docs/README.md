# Documentation

Policy and runbooks for ConicShield. The repository root [`README.md`](../README.md) lists everything in one map.

| Document | Purpose |
|----------|---------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System layers and design intent |
| [ENGINEERING_STATUS.md](ENGINEERING_STATUS.md) | What ships in-tree vs vendor-only |
| [ROADMAP.md](ROADMAP.md) | External deps and deferred work |
| [MAINTAINER_RUNBOOK.md](MAINTAINER_RUNBOOK.md) | Commands, publish flow, CI notes |
| [BENCHMARK_GOVERNANCE.md](BENCHMARK_GOVERNANCE.md) | How benchmark claims are published |
| [NATIVE_ARM_PUBLISH_CHECKLIST.md](NATIVE_ARM_PUBLISH_CHECKLIST.md) | Steps to get `shielded-native-moreau` into `publishable_arms` |
| [RELEASE_POLICY.md](RELEASE_POLICY.md) | Same-family vs new-family release; no ad-hoc `CURRENT.json` edits |
| [VERIFICATION_AND_STRESS_TEST_PLAN.md](VERIFICATION_AND_STRESS_TEST_PLAN.md) | Trust ladder, layers, policies |
| [PARITY_AND_FIXTURES.md](PARITY_AND_FIXTURES.md) | Frozen fixture and native parity |
| [DEVENV.md](DEVENV.md) | Python matrix, pytest markers, workflows |
| [INTER_SIM_RL_INTEGRATION.md](INTER_SIM_RL_INTEGRATION.md) | Host integration |
| [MOREAU_INSTALL_AND_ENVIRONMENT_POLICY.md](MOREAU_INSTALL_AND_ENVIRONMENT_POLICY.md) | Vendor install expectations |
| [MOREAU_API_NOTES.md](MOREAU_API_NOTES.md) | API drift and upgrade checks |
| [adr/001-progress-clearance-constraints.md](adr/001-progress-clearance-constraints.md) | Deferred `progress` / `clearance` constraint kinds |

**Dashboard:** registry view via `dashboard_cli` and unified `generate_trust_dashboard` — [MAINTAINER_RUNBOOK.md](MAINTAINER_RUNBOOK.md). Short pointer: [`benchmarks/DASHBOARD_README.md`](../benchmarks/DASHBOARD_README.md).
