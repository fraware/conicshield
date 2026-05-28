# Public claims

Short authoritative claim surface for engineers, collaborators, and external materials.

PRs that change public-facing docs or examples must cite this file (or ROADMAP / DIFFERENTIATION_PUBLIC_STANCE / SOLVER_PATHS_AND_BATCHING) and pass `python scripts/check_public_claim_phrases.py`.

## Safe to claim publicly now

- Convex shield projection with **`simplex`, `turn_feasibility`, `box`, `rate`** constraints.
- Governed, hash-indexed **published benchmark bundles** with provenance and release metadata.
- Flagship **`host-realistic-20260525`**: closed export→bank→publish loop at **`vendor_native`** tier.
- **Reference CVXPY/Moreau** path for parity and reproducible reference arms.
- **Native compiled sequential** and **true batched compiled** solve paths exist (`NATIVE_MOREAU`, `NATIVE_MOREAU_BATCH`).
- Batch path is **governed and viability-tested** (not universally faster).
- Host-realistic export uses **live upstream dump** with **fork** topology validated via pinned inter-sim API.
- Differentiation tooling supports **finite-difference validation** (Layer F), not a productized autograd stack.

## Qualified claims only

- **Throughput / batch speedup:** only where `batch_solve_report` and policy tiers support it; default public narrative remains **viability_only** (see `reference_system_status.json`).
- **Native arm metrics:** only for bundles with `includes_native_arm` and appropriate `evidence_tier`.
- **Parity:** only for arms listed under `publishable_arms` with green gates at publish time.
- **Graph realism:** fork topology via inter-sim — **not** full Maps/session navigation unless future provenance documents it.

## Not yet claimable

- `progress` / `clearance` constraint kinds.
- Production **shield autograd** or differentiable-shield product guarantees.
- **`conicshield-shield-qp-micro-v1`** or other families as reference authority.
- Universal **batch speedup** on all scenarios.
- Full **navigation-session** upstream graphs for the flagship export.
- Second-family or Option B/C platform features ([V2_STRATEGY.md](V2_STRATEGY.md)).
