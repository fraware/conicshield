# Proposer documentation

This document consolidates the design rationale, architecture notes, benchmark policy, and research/engineering thesis behind the ConicShield repository.

## Project thesis

The project is not a generic solver demo. It is a proof-aware optimization shield for learned controllers and cyber-physical systems.

The central pattern is:
1. a policy proposes an action
2. a safety layer defines admissibility
3. an optimizer computes the nearest admissible action
4. an evidence layer records the intervention
5. a governed benchmark stack decides what results are trustworthy

## Why conic optimization belongs here

Conic optimization is the execution engine for constraint-respecting decisions.

The shield solves problems of the form:
- stay close to the proposed action
- satisfy hard constraints
- optionally incorporate geometry-aware priors
- emit machine-readable runtime evidence

## Why governance is first-class

A benchmark is not just a number. It is a governed claim about a stable task.

The repository therefore includes:
- artifact schemas
- run-bundle validation
- native parity validation
- promotion thresholds
- family manifests
- family-bump policy
- release orchestration
- global governance audit
- governance dashboard
- maintainer runbook

## Design notes captured from the project process

### Runtime semantics
The runtime shield works on a four-action simplex over:
- `turn_left`
- `turn_right`
- `go_straight`
- `turn_back`

### Reference versus native execution
The reference path is a high-level path intended to model the optimization transparently.
The native Moreau compiled path is the performance path and must inherit trust through parity.

### Evidence
Every intervention is intended to record:
- raw Q-values
- proposed distribution
- corrected distribution
- chosen action
- active constraints
- solver status
- timing metadata
- whether warm-starting was used

### Benchmark structure
Benchmarks are intended to run on transition banks rather than live environment calls.
This isolates policy and shield behavior from API variance.

### Family governance
Semantic task changes must fork benchmark families rather than overwrite scores.

## What is intentionally included in this repo

This repo includes not just code but all the written operational and policy artifacts:
- architecture
- benchmark governance
- release policy
- fixture policy
- maintainer runbook
- family manifests
- dashboard
- audit flows

The goal is to make the repository itself strong enough to serve as a trustworthy benchmark and release system, not merely a code dump.

## See also

- [README.md](../README.md) — documentation map and verification ladder
- [VERIFICATION_AND_STRESS_TEST_PLAN.md](VERIFICATION_AND_STRESS_TEST_PLAN.md) — operational trust layers
- [ARCHITECTURE.md](ARCHITECTURE.md) — layered system view
- [BENCHMARK_GOVERNANCE.md](../BENCHMARK_GOVERNANCE.md) — governed benchmark claims
