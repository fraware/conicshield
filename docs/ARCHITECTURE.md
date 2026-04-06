# Architecture

## Mission

ConicShield is a proof-aware runtime safety layer and a governed benchmark system.

It sits between:
- a policy that proposes actions
- a structured safety specification
- a runtime optimizer that corrects actions
- an evidence pipeline that records interventions
- a governance stack that decides which results are trustworthy

## Layered view

### 1. Policy layer
Policy outputs action scores or Q-values.

### 2. Shield layer
The shield turns scores into a simplex distribution, applies hard admissibility and optional geometry priors, and decodes back to a concrete action.

### 3. Solver layer
Two paths are supported:
- reference path: CVXPY/Moreau
- production path: native Moreau compiled solver

### 4. Evidence layer
Every intervention produces structured data: proposed distribution, corrected distribution, solver metadata, selected action, active constraints.

### 5. Benchmark layer
Benchmarks are run on frozen transition-bank artifacts and serialized into validated run bundles.

### 6. Governance layer
Governance decides whether results are:
- candidates
- review-locked
- published
- deprecated
