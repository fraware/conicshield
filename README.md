# ConicShield

ConicShield is a proof-aware runtime safety layer for learned controllers and cyber-physical systems.

A policy proposes an action. ConicShield solves a constrained optimization problem to find the nearest admissible action under explicit safety constraints. The environment executes the corrected action, not the raw proposal. Every intervention produces structured evidence that can be inspected, hashed, replayed, validated, and governed.

This repository is intentionally comprehensive. It contains:
- solver interfaces and reference/native backends
- benchmark schemas and bundle validation
- parity and promotion gates
- benchmark-family governance
- release orchestration
- governance audit and dashboard generation
- maintainer runbooks and policy documents
- a frozen parity fixture contract
- extensive tests for governance, payloads, schemas, family policy, dashboard logic, and shield logic

## Repository status

This repo is a high-quality implementation scaffold and governance system. It is structured so that:
- pure-Python governance and artifact layers run without optional solver dependencies
- solver-backed paths become available when installing the optional `solver` extras
- external environment integration is explicit and documented rather than hidden

## Installation

Base install:

```bash
pip install -e ".[dev]"
```

Optional solver stack:

```bash
pip install -e ".[solver,dev]" --extra-index-url "<YOUR_PRIVATE_MOREAU_INDEX_URL>"
```

Moreau also requires a license key, typically placed at:

```bash
mkdir -p ~/.moreau
printf "%s" "<YOUR_MOREAU_LICENSE_KEY>" > ~/.moreau/key
```

## Quick commands

Validate a run bundle:

```bash
python -m conicshield.artifacts.validator_cli --run-dir benchmarks/runs/<run_id>
```

Run governance audit:

```bash
python -m conicshield.governance.audit_cli --strict
```

Generate governance dashboard:

```bash
python -m conicshield.governance.dashboard_cli   --json-output output/governance_dashboard.json   --markdown-output output/governance_dashboard.md
```

Dry-run a release decision:

```bash
python -m conicshield.governance.release_cli   --run-dir benchmarks/runs/<run_id>   --family-id conicshield-transition-bank-v1   --reason "candidate release review"   --dry-run
```

## Layout

```text
conicshield/          # Python package
├── adapters/
│   └── inter_sim_rl/
├── artifacts/
├── bench/
├── core/
├── governance/
├── parity/
├── specs/
└── scripts/
schemas/              # JSON Schema sources for run bundles (repo root, not under the package)
benchmarks/           # registry, releases, run bundles
tests/                # pytest suite (repository root)
docs/
scripts/
```

## Design principles

1. Formal intent, operational enforcement.
2. Minimal intervention.
3. Evidence by default.
4. Reproducible benchmark bundles.
5. Native compiled results are never trusted without parity.
6. Semantic task changes fork benchmark families instead of silently overwriting scores.

## Documentation map

- `ENGINEERING_STATUS.md` — what is implemented vs scaffold, CI gaps, and external deps (keep updated)
- `ENGINEERING_HANDOFF_IMPLEMENTATION_PLAN.md` — phased plan for completing the system
- `docs/PROPOSER_DOCUMENTATION.md` — consolidated design rationale and proposal-level notes
- `BENCHMARK_GOVERNANCE.md` — benchmark governance policy
- `MAINTAINER_RUNBOOK.md` — operational procedures
- `docs/ARCHITECTURE.md` — architecture and repo structure
- `docs/INTER_SIM_RL_INTEGRATION.md` — how to integrate with the external environment
- `docs/FIXTURE_POLICY.md` — frozen parity fixture policy
- `docs/RELEASE_POLICY.md` — release orchestration policy

## Notes on optional dependencies

This repo intentionally keeps the governance, artifact, and audit stack usable without `cvxpy` or `moreau`.

When the optional solver stack is not installed:
- governance and artifact tests still run
- parity replay logic can still be tested against fake shields
- solver-backed shield execution raises a clear optional-dependency error
