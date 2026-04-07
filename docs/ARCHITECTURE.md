# Architecture

## Mission

ConicShield is a proof-aware runtime safety layer and a governed benchmark system.

It sits between:

- a policy that proposes actions
- a structured safety specification
- a runtime optimizer that corrects actions
- an evidence pipeline that records interventions
- a governance stack that decides which results are trustworthy

## Thesis

The project is not a generic solver demo. It targets **learned controllers** and systems where safety must be **evidence-backed**: a policy proposes an action, a safety layer defines admissibility, an optimizer finds the nearest admissible action, interventions are recorded, and **benchmark claims** are governed so comparisons stay meaningful over time.

**Why conic optimization:** the shield encodes “stay close to the proposal” subject to hard constraints and optional geometry priors, with structured outputs suitable for replay and audit.

**Why governance is first-class:** a benchmark is a claim about a **stable task**. The repo therefore ships schemas, bundle validation, parity checks, family manifests, release orchestration, audit, and dashboards — not only application code.

## Layered view

### 1. Policy layer

Policy outputs action scores or Q-values.

### 2. Shield layer

The shield turns scores into a simplex distribution, applies hard admissibility and optional geometry priors, and decodes back to a concrete action.

### 3. Solver layer

Two paths are supported:

- reference path: CVXPY/Moreau
- production path: native Moreau compiled solver

The native path inherits trust through **parity** against the reference stream on a frozen fixture.

### 4. Evidence layer

Interventions record proposed and corrected distributions, chosen action, active constraints, solver status, and timing where applicable.

### 5. Benchmark layer

Benchmarks run on frozen transition-bank artifacts and serialize into validated run bundles (not live environment calls for published evaluations).

### 6. Governance layer

Governance decides whether results are candidates, review-locked, published, or deprecated. Semantic task changes **fork families** instead of silently overwriting scores.

## Repository layout

| Area | Location |
|------|----------|
| Package code | `conicshield/` |
| JSON Schemas for bundles | `schemas/` |
| Benchmark registry and releases | `benchmarks/` |
| Governed run bundles (typical) | `benchmarks/runs/<run_id>/` |
| Frozen parity fixture | `tests/fixtures/parity_reference/` |
| Maintainer scripts (verification, perf, dashboard) | `scripts/` |
| Tests | `tests/` (see `tests/README.md`) |
| Policies and verification ladder | `docs/` |

## Related

- [README.md](../README.md) — documentation map and quick commands
- [VERIFICATION_AND_STRESS_TEST_PLAN.md](VERIFICATION_AND_STRESS_TEST_PLAN.md) — trust ladder
- [BENCHMARK_GOVERNANCE.md](BENCHMARK_GOVERNANCE.md) — publication rules
