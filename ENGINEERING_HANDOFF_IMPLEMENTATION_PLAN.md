# ConicShield Engineering Handoff and Implementation Plan

## Purpose

This document is the handoff plan for the engineering team taking over the ConicShield repository.

It has one goal: **turn the current repository from a comprehensive governed scaffold into the full system vision we designed**.

That final vision is:

- a **proof-aware runtime optimization shield** for learned controllers,
- with a **reference solver path** and a **native compiled production path**,
- integrated first with **`inter-sim-rl`** as the benchmark host,
- then extended into **proof-linked constraints** and a second benchmark host such as **LabTrust-Gym**,
- with **auditable runtime evidence**, **native parity validation**, **governed benchmark families**, **release orchestration**, and **publication-quality benchmarking**.

This plan is intentionally detailed. It is written so a senior engineering team can take ownership without guessing what was intended.

---

# 1. Current repository status: what already exists vs. what is still a scaffold

## 1.1 What already exists in the repo

The current repo already contains substantial structure and should be treated as the canonical starting point, not as a blank slate.

It already includes:

- package structure for `conicshield/`
- reference and native solver seams
- shield logic on a 4-action simplex
- geometry-prior utilities
- JSON Schema sources under **repository root** `schemas/` (copied into run bundles as needed; not under `conicshield/`)
- artifact schemas and run-bundle validation
- parity replay machinery and parity gates
- promotion policy
- governance finalization, release orchestration, family manifests, dashboard, and audit layers
- fixture policy and regeneration policy
- GitHub Actions workflows (path-filtered; see note below)
- tests for governance and core logic
- proposer and architecture docs

**CI note:** The `ci` workflow runs the full `pytest tests/` suite on every pull request and on pushes to `main` using `.[dev]` only (no solver extras). Path-filtered workflows still cover governance audit, dashboard generation, fixture-policy checks, and an additional `tests/test_parity_replay.py` job where listed paths change. A separate **solver-enabled** CI job (Phase 1) remains to be added when Moreau integration tests are marked and wired.

## 1.2 What is still intentionally incomplete or synthetic

The repo is **not yet the final production system**. Several parts are still scaffolds and must be completed by engineering.

The most important gaps are:

### Solver realism
- The repository contains the structure for native/reference paths, but the team must verify and harden all Moreau-backed code against the **real installed package**, not just the abstract interface.
- Some parts were written from the design we established and should be treated as a strong architectural draft, not as the last word on exact package behavior.

### `inter-sim-rl` integration
- The repo intentionally does **not vendor** `inter-sim-rl`.
- The environment integration path is documented, but the team must make the actual patches in the external environment and align the adapter against the real repo state.

### Transition-bank generation
- The benchmark architecture is defined, but the engineering team must build the full transition-bank generation pipeline against the real environment and confirm the semantics.

### End-to-end benchmarks
- The governance system is present, but the team must produce the first real benchmark family, real fixture, real run bundles, and real published outputs.

### Formal methods integration
- The proof-linked roadmap is designed, but the actual Lean / proof-artifact bridge remains a later implementation phase.

### LabTrust-Gym expansion
- The second benchmark host is part of the strategic direction, but the repo is currently centered on `inter-sim-rl`.

## 1.3 The correct mental model for the team

Treat the current repo as:

- **strong on architecture**,
- **strong on governance**,
- **strong on benchmark discipline**,
- **medium on synthetic implementation completeness**,
- **not yet complete on external environment and solver integration**.

Do not rewrite it casually. Complete it.

---

# 2. Final vision to implement

The final system should satisfy all of the following.

## 2.1 Runtime control vision

A learned policy proposes an action.
ConicShield computes the nearest admissible action under explicit safety and operational constraints.
The corrected action is executed.
Every intervention is recorded with machine-readable evidence.

## 2.2 Solver vision

There are two solver paths:

### Reference path
- high-level, transparent, easy to inspect
- CVXPY + Moreau
- used for correctness, modeling, and parity reference

### Production path
- native Moreau compiled/shared-structure path
- used for repeated low-latency execution
- trusted only through parity against the reference path

## 2.3 Benchmark vision

The benchmark should eventually support:

### First host
`inter-sim-rl`
- 4 maneuver actions
- action-conditioned transitions
- frozen transition-bank benchmarking
- rules-only and rules+geometry shield comparisons
- native parity and promotion to endorsed benchmark arms

### Second host
`LabTrust-Gym`
- constrained coordination/dispatch repair
- trust/evidence oriented benchmark setting
- same governed benchmark principles

## 2.4 Governance vision

Every published result should be:

- schema-valid,
- invariant-valid,
- parity-qualified where required,
- promotion-qualified,
- family-version governed,
- audit-visible,
- dashboard-visible,
- and operationally reviewable.

## 2.5 Research vision

The repository should evolve into:

- a serious systems repo,
- a reproducible benchmark stack,
- a publication-ready experimental substrate,
- and eventually a bridge from formal safety structure to runtime enforcement.

---

# 3. Non-negotiable engineering rules

These are hard rules for the team.

## 3.1 Do not collapse reference and native paths

The native path must remain subordinate to the reference path.

Reference path is for:
- semantic clarity
- modeling clarity
- parity truth

Native path is for:
- throughput
- repeated execution
- deployment realism

Never optimize away the distinction.

## 3.2 Do not let semantic task changes overwrite the benchmark family

If the task contract changes materially, fork a new family.
Do not “just update the score.”

## 3.3 Do not let governance logic live in CI only

The repository code must remain the source of truth.
CI should invoke repository logic, not duplicate it.

## 3.4 Do not weaken parity discipline just to ship the native path

If native parity fails, the native arm is not endorsed.
Fix the implementation or fork semantics explicitly.

## 3.5 Do not use live API calls in final benchmark evaluation

Use live APIs only to build transition banks or synthetic candidate corpora.
Published benchmark runs must be replayed on frozen artifacts.

## 3.6 Do not break the fixed observation contract casually

If you change the `inter-sim-rl` observation contract, that is probably a new family.

---

# 4. Repository map and ownership model

## 4.1 Recommended team split

I recommend five ownership tracks.

### Track A — Solver and shield runtime
Owns:
- `conicshield/core/`
- `conicshield/specs/`
- `conicshield/adapters/inter_sim_rl/shield.py`
- native/reference equivalence

### Track B — Environment and transition-bank integration
Owns:
- `inter-sim-rl` external patching
- transition-bank export and replay
- context generation
- benchmark environment realism

### Track C — Benchmark artifacts and evaluation
Owns:
- `conicshield/bench/`
- metrics, reports, payloads
- benchmark cards
- summary integrity

### Track D — Governance and release system
Owns:
- `conicshield/governance/`
- `conicshield/parity/`
- schemas
- run finalization
- release orchestration
- audit and dashboard

### Track E — Formal methods and second-host expansion
Owns:
- proof-linked constraints roadmap
- Lean integration later
- LabTrust-Gym integration later

## 4.2 Suggested lead roles

- one **technical lead** over Tracks A+B
- one **benchmark/governance lead** over Tracks C+D
- one **research systems lead** over Track E

---

# 5. Phase plan

The work should be executed in order. Do not jump to later phases before earlier gates are green.

---

# Phase 0 — Repository hardening and takeover

## Goal
Make the repo adoptable by the engineering team without ambiguity.

## Deliverables
- clean developer setup
- reproducible local test environment
- pinned dependency strategy
- documented optional solver installation path
- real CI green on the current codebase

## Tasks

### 0.1 Remove generated clutter
- remove `.pytest_cache/` from the tracked repo if present
- ensure `.gitignore` is correct
- ensure no transient local files are committed

### 0.2 Normalize Python version strategy
The repo currently targets Python 3.11 in `pyproject.toml`, while Moreau install guidance in earlier work referenced Python 3.12+ for CUDA on Windows.

Action:
- decide the canonical engineering baseline for CI and Linux development
- document supported versions explicitly
- test solver extras against the actual Moreau package on the chosen baseline

### 0.3 Replace placeholder author/package metadata
- update package author fields
- update licensing if needed
- add canonical project metadata

### 0.4 Make CI deterministic
Ensure all current tests pass in CI on every push.

### 0.5 Add a top-level `ENGINEERING_STATUS.md`
This should list:
- what is complete
- what is stubbed
- what depends on external repos
- which milestones are current blockers

A living `ENGINEERING_STATUS.md` is maintained at the repo root; keep it updated as milestones land.

## Acceptance criteria
- engineers can clone and run tests immediately (`pytest tests/` locally)
- base CI runs the full `pytest tests/` suite without solver extras on PRs and `main` (see `.github/workflows/ci.yml`)
- optional solver install instructions are verified on at least one real environment

---

# Phase 1 — Real Moreau integration and solver-path hardening

## Goal
Turn solver scaffolding into a real, verified integration with the actual Moreau package.

## Deliverables
- real CVXPY + Moreau reference path working end-to-end
- real native Moreau path working end-to-end
- consistent solver metadata extraction
- optional dependency behavior hardened

## Tasks

### 1.1 Verify Moreau package API against reality
Audit these files against the actual installed package:
- `conicshield/core/moreau_compiled.py`
- `conicshield/specs/compiler.py`
- `conicshield/core/solver_factory.py`

Check specifically:
- constructor signatures
- `Settings` fields
- `CompiledSolver` API
- `setup()` argument names
- `solve()` inputs and outputs
- warm-start object behavior
- `info` field names and shapes

Do not assume the scaffold is perfect. Confirm every call.

### 1.2 Make optional dependency failures precise
Current optional dependency support is good conceptually. Improve it so errors explain exactly:
- what package is missing
- which feature path required it
- how to install it

### 1.3 Implement canonical solver telemetry extraction
Standardize telemetry extraction into one place.

Expose at least:
- solver status
- objective value
- solve time
- setup time
- construction time
- iterations
- device
- warm-start flag

### 1.4 Add solver integration tests behind markers
Split tests into:
- base tests that run without Moreau
- solver tests that run only when solver extras are installed

Suggested markers:
- `@pytest.mark.solver`
- `@pytest.mark.integration`
- `@pytest.mark.requires_moreau`

### 1.5 Add a solver smoke-test CLI
Create a CLI that runs one minimal reference solve and one minimal native solve and prints normalized telemetry.

## Acceptance criteria
- CVXPY + Moreau reference solve works on real package
- native Moreau solve works on real package
- telemetry extraction is correct and stable
- solver tests pass in a solver-enabled environment

---

# Phase 2 — Real `inter-sim-rl` integration

## Goal
Replace the documented seam with a real working integration against the actual external repo.

## Deliverables
- actual environment patch in `inter-sim-rl`
- actual `get_shield_context()` output
- action-conditioned transition semantics
- ConicShield action selection running live against the environment

## Tasks

### 2.1 Fork or mirror `inter-sim-rl` under explicit engineering control
Do not integrate against an uncontrolled moving target.

Create:
- a tracked fork or submodule strategy
- a documented revision pin

### 2.2 Patch the environment so actions affect transitions
This is essential.

The original repo semantics, as discussed, used chosen actions primarily in reward logic and stored instruction, while transitions were driven by nearby-place sampling. That is not enough for the final vision.

Implement:
- candidate transitions from nearby map/directions data
- action-conditioned transition pools
- graceful fallback behavior
- explicit transition candidate metadata in context

### 2.3 Keep the observation contract stable in the first pass
Do not retrain yet.

First integration should keep:
- the state vector shape stable
- the DQN interface stable
- the shield as a control layer around the policy

### 2.4 Add `get_shield_context()` in the real environment
Context should include at minimum:
- `allowed_actions`
- `blocked_actions`
- `action_upper_bounds`
- `rule_choice`
- `previous_instruction`
- `hazard_score`
- `transition_candidates`
- `current_heading_deg` where available
- geometry metadata derived from candidate transitions

### 2.5 Implement a real policy adapter
`InterSimKerasDQNPolicy` or equivalent must point to the actual model object and actual state object.

### 2.6 Add integration tests against the real environment fork
Test at least:
- shield returns a valid action string
- action-conditioned transitions differ by action choice
- context is well-formed
- environment step remains stable under shield intervention

## Acceptance criteria
- shield can sit in the actual inference loop
- actions now affect reachable next states
- environment patch is tested and documented

---

# Phase 3 — Transition-bank generation and replay benchmark substrate

## Goal
Freeze the environment into reproducible benchmark artifacts.

## Deliverables
- real transition-bank builder
- deterministic replay environment
- full episode serialization
- no live API dependence during evaluation

## Tasks

### 3.1 Build transition-bank generation as an offline pipeline
This should query the environment or map stack offline and generate a bank with:
- nodes keyed by address or canonical state id
- candidate outgoing branches
- action classes
- branch costs and metadata

### 3.2 Decide deterministic branch-selection policy for replay
When multiple candidates exist for the same action class, pick deterministically in replay.

Possible deterministic key:
- duration
- distance
- lexical destination tie-breaker

### 3.3 Extend replay environment metrics
Replay env should emit:
- `matched_action`
- `fallback_used`
- selected candidate metadata
- out-of-bank termination flags

### 3.4 Lock the transition-bank schema
Formalize and validate:
- node structure
- edge structure
- metadata fields
- bank identity and provenance

### 3.5 Add large replay tests
Test at least:
- replay determinism
- branch validity
- no live API usage in replay mode
- arm divergence on the same bank

## Acceptance criteria
- benchmark runs can be reproduced from frozen bank artifacts only
- replay is deterministic
- bank artifacts validate cleanly

---

# Phase 4 — Reference shield correctness benchmark

## Goal
Make the CVXPY + Moreau reference shield the semantic source of truth.

## Deliverables
- real benchmark runner for baseline / rules-only / rules+geometry
- reference benchmark card
- valid run bundles
- first frozen parity fixture generated from the real reference path

## Tasks

### 4.1 Run the first true benchmark family
At minimum include arms:
- `baseline-unshielded`
- `shielded-rules-only`
- `shielded-rules-plus-geometry`

### 4.2 Fill `episodes.jsonl` completely
Every step should include:
- state/address context
- chosen action
- raw Q-values
- proposed distribution
- corrected distribution
- active constraints
- branch-selection metadata
- reward

### 4.3 Generate valid run bundles
Ensure:
- schemas pass
- invariants pass
- benchmark card renders correctly
- dashboard ingests results correctly

### 4.4 Generate the first real parity reference fixture
The fixture must come from the reference shield, not a synthetic placeholder.

### 4.5 Replace synthetic fixture if present
Do this only through the governed regeneration process.

## Acceptance criteria
- reference benchmark run exists as a full governed run bundle
- real parity fixture exists and validates

---

# Phase 5 — Native Moreau parity and native promotion

## Goal
Trust the native compiled path only after exact replay parity.

## Deliverables
- real parity harness output against the frozen reference fixture
- parity CI green
- native benchmark arm promotable only when parity is green

## Tasks

### 5.1 Ensure step-level shield inputs are recorded
Parity replay must consume the exact:
- raw Q-values
- action-space ordering
- context snapshot

### 5.2 Run parity on the real reference fixture
Check:
- action match rate
- corrected distribution distance
- active constraint equivalence
- objective differences where meaningful

### 5.3 Tighten native/reference numerical expectations where justified
The current thresholds are good defaults. The team may tighten after observing real distributions.

### 5.4 Wire parity to CI and release policy
If parity fails:
- native arm not publishable
- benchmark card must not endorse native

### 5.5 Benchmark native against reference shield
Only after parity passes.

## Acceptance criteria
- native path matches the reference path on the frozen fixture
- native arm is publishable only through green parity and green promotion

---

# Phase 6 — Governance completion on real artifacts

## Goal
Move governance from scaffold-only to real operational truth.

## Deliverables
- first real family manifest in use
- first real published run
- dashboard and audit over real run bundles

## Tasks

### 6.1 Create the first real benchmark family release
Family:
- `conicshield-transition-bank-v1`

### 6.2 Run finalization on real runs
Generate `governance_status.json` from actual benchmark outputs.

### 6.3 Publish the first same-family release
Only if:
- artifacts valid
- promotion green
- parity green where needed
- review-locked true

### 6.4 Verify registry, history, current pointers, and dashboard
Run full governance audit in strict mode.

### 6.5 Document release decision in `governance_decision.md`

## Acceptance criteria
- dashboard shows one real published family
- audit is clean
- registry/history/current are consistent

---

# Phase 7 — Retraining in the upgraded environment

## Goal
Move from shield-over-frozen-policy to policy learning in the improved action-conditioned environment.

## Deliverables
- retrained baseline policy on the action-conditioned environment
- comparison between:
  - unshielded retrained policy
  - shield-at-inference policy
  - shield-aware or shield-in-the-loop variants

## Tasks

### 7.1 Freeze benchmark family boundaries first
This phase may trigger a new family version if:
- the state contract changes,
- the training objective changes materially,
- or the task semantics are redefined.

### 7.2 Decide whether retraining stays in family or forks a new family
Most likely this becomes a new family if the benchmark meaning shifts materially.

### 7.3 Retrain with the stabilized environment semantics
Start with:
- same state vector if possible
- then consider a state upgrade only later

### 7.4 Evaluate whether shield-at-training adds value
Possible comparisons:
- no shield
- shield only at inference
- shield in rollout collection
- differentiable or implicit shield effects later

## Acceptance criteria
- retrained policy results are benchmarked under explicit family/version governance

---

# Phase 8 — Formal methods integration

## Goal
Connect formal artifacts to runtime constraints.

## Deliverables
- proof-linked spec fragments
- formal artifact identifiers in runtime evidence
- import path from proof artifacts to shield specs

## Tasks

### 8.1 Define the intermediate formal constraint representation
Do not go directly from arbitrary theorem artifacts to solver calls.

Create an explicit intermediate representation for:
- admissible actions
- rate limits
- state invariants
- action masks
- cost shaping priors where justified

### 8.2 Define proof provenance fields
Every runtime shield spec should eventually be able to point back to:
- proof artifact id
- proof build version
- source theorem/spec id

### 8.3 Add formal metadata to evidence payloads
This should be optional at first.

### 8.4 Only later attempt proof-generated specs
Do not block the operational benchmark system on full proof synthesis.

## Acceptance criteria
- proof-linked metadata can flow through benchmark and evidence artifacts without ambiguity

---

# Phase 9 — LabTrust-Gym expansion

## Goal
Generalize from discrete maneuver shielding to constrained coordination/dispatch repair.

## Deliverables
- second benchmark host
- family version or new family for LabTrust benchmarks
- reuse of governance stack

## Tasks

### 9.1 Define the analogous control object in LabTrust-Gym
Examples:
- dispatch priority vector
- allocation vector
- routing/repair choice
- queue-control action

### 9.2 Decide the optimization formulation
May remain quadratic-conic if the control object is a relaxed vector. Do not force mixed-integer early.

### 9.3 Reuse artifact and governance stack
The point is not to rebuild governance; it is to prove the governance stack generalizes.

### 9.4 Create a separate benchmark family
Do not conflate with `inter-sim-rl` family.

## Acceptance criteria
- second governed benchmark family exists using the same benchmark system

---

# 6. Detailed file-by-file engineering instructions

## 6.1 Files that must be treated as authoritative governance sources

Do not bypass these:
- `BENCHMARK_GOVERNANCE.md`
- `MAINTAINER_RUNBOOK.md`
- `benchmarks/registry.json`
- `benchmarks/releases/*/FAMILY_MANIFEST.json`
- `conicshield/governance/finalize.py`
- `conicshield/governance/release.py`
- `conicshield/governance/audit.py`

## 6.2 Files most likely to need real implementation correction

These are the highest-priority code review files:
- `conicshield/core/moreau_compiled.py`
- `conicshield/specs/compiler.py`
- `conicshield/adapters/inter_sim_rl/shield.py`
- `conicshield/bench/transition_bank.py`
- `conicshield/bench/replay_graph_env.py`
- `conicshield/parity/replay.py`

## 6.3 Files that should remain relatively stable

These should change only with care:
- schema files under `schemas/`
- family manifest schema
- governance status schema
- benchmark release files

---

# 7. Test plan the team should implement

The current repo already has a strong test start. The team should expand it aggressively.

## 7.1 Test categories

### Unit tests
For:
- schema validation
- family policy
- run spec id stability
- shield logic
- geometry prior
- artifact payload aggregation

### Solver tests
For:
- reference solve success
- native solve success
- telemetry extraction
- warm-start behavior

### Parity tests
For:
- replay correctness
- exact action parity
- constraint-set parity
- numerical tolerance discipline

### Environment integration tests
For:
- `inter-sim-rl` patched environment
- action-conditioned transitions
- context shape stability
- transition-bank generation

### Governance tests
For:
- finalization
- release orchestration
- family bump
- audit consistency
- dashboard generation

### End-to-end tests
For:
- generate run bundle
- finalize run
- dry-run release
- publish same-family
- audit clean afterward

## 7.2 Minimum additional tests to add immediately

Add tests for:
- actual Moreau reference solve with solver extras installed
- actual native Moreau compiled solve with warm start
- parity replay on a real reference fixture
- transition-bank determinism from a frozen artifact
- action-conditioned environment semantics
- full benchmark bundle generation from a real run
- release dry-run returns `same-family` or `new-family` correctly

## 7.3 CI matrix recommendation

### Base CI
Runs without solver extras:
- governance
- artifacts
- dashboard
- family policy
- schemas

### Solver CI
Runs with solver extras:
- solver tests
- parity tests
- native parity fixture gate

### Release CI
Manual or gated:
- benchmark generation
- finalization
- release dry-run
- publish if explicitly approved

---

# 8. Benchmark and release operations checklist

## Before any benchmark run is considered real
- [ ] environment integration is on a pinned revision
- [ ] transition bank built offline
- [ ] policy checkpoint pinned
- [ ] run spec generated
- [ ] seeds fixed
- [ ] benchmark family known

## Before any native result is endorsed
- [ ] parity fixture validates
- [ ] parity CI green
- [ ] native arm included in `publishable_arms`

## Before any run is published
- [ ] artifact validator green
- [ ] finalization produced `governance_status.json`
- [ ] state is `review-locked`
- [ ] release dry-run checked
- [ ] governance decision record written
- [ ] audit clean
- [ ] dashboard reviewed

---

# 9. Concrete first 30 engineering tasks

This is the execution sequence I would actually assign.

1. Clean the repo metadata and developer ergonomics.
2. Verify optional solver installation against real Moreau.
3. Audit all Moreau API calls against the real package.
4. Add solver-marked tests.
5. Build a real solver smoke-test CLI.
6. Pin the `inter-sim-rl` integration target revision.
7. Patch `inter-sim-rl` environment so chosen actions affect transitions.
8. Add real `get_shield_context()` to `inter-sim-rl`.
9. Wire the real policy adapter to the actual model object.
10. Test live shield action selection in the real environment.
11. Build offline transition-bank generation from the patched environment.
12. Freeze a deterministic replay environment.
13. Validate transition-bank serialization.
14. Run the first real baseline benchmark arm.
15. Run the first real rules-only shield arm.
16. Run the first real rules+geometry shield arm.
17. Generate the first real run bundle.
18. Replace synthetic fixture with a real reference fixture through the governed process.
19. Run native parity against the new real fixture.
20. Fix native/reference mismatches until parity is green.
21. Benchmark native against the same bank.
22. Finalize `governance_status.json` for the run.
23. Dry-run release decision.
24. Publish the first same-family run if eligible.
25. Run governance audit and dashboard generation.
26. Document benchmark card and current published run.
27. Decide whether retraining remains in-family or becomes a new family.
28. Retrain baseline policy in the upgraded action-conditioned environment.
29. Evaluate shield-at-inference vs retrained unshielded policy.
30. Start proof-linked spec design for the next family or second-host expansion.

---

# 10. Suggested milestone definitions

## Milestone M1 — Real solver correctness
Reference and native paths work against the real Moreau package.

## Milestone M2 — Real environment semantics
`inter-sim-rl` actions affect transitions and expose shield context.

## Milestone M3 — Real frozen benchmark substrate
Transition bank and replay environment are real and deterministic.

## Milestone M4 — Real reference benchmark family
First real governed run bundle and fixture exist.

## Milestone M5 — Native endorsement
Parity is green and native arm is promotable.

## Milestone M6 — First published governed benchmark
Current published family exists, audit is clean, dashboard is populated.

## Milestone M7 — Post-inference expansion
Retraining, proof-linking, or second-host expansion begins.

---

# 11. What success looks like

You are done with the first major objective when all of this is true:

- ConicShield runs as a real control layer around a real external environment.
- Actions affect transitions, not just reward bookkeeping.
- Benchmarks run on frozen transition banks, not live API calls.
- The reference shield path is real and benchmarked.
- The native compiled path passes parity against the reference path.
- Run bundles are validated and governed.
- A benchmark family has a current published run.
- The governance audit is clean.
- The dashboard shows a healthy system.

You are done with the broader vision when all of this is also true:

- proof-linked constraints begin to flow into runtime specs,
- or a second benchmark host such as LabTrust-Gym reuses the same governed benchmark stack.

---

# 12. Final instruction to the team

Do not treat this repo as a prototype you should simplify.
Treat it as a **serious benchmark and release system** whose runtime capabilities must be completed carefully.

The architecture is already doing the right thing:
- separating semantics from performance,
- separating trust from speed,
- separating task meaning from implementation change,
- and separating benchmarking from governance.

Your job is to finish the implementation **without collapsing those distinctions**.

That is the whole point of ConicShield.
