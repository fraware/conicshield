# Public claims

Short authoritative claim surface for engineers, collaborators, and external materials.

PRs that change public-facing docs or examples must cite this file (or ROADMAP / DIFFERENTIATION_PUBLIC_STANCE / SOLVER_PATHS_AND_BATCHING) and pass `python scripts/check_public_claim_phrases.py`.

Track 1 runtime qualification evidence:
[`docs/stabilization/PRODUCTION_QUALIFICATION_REPORT.md`](stabilization/PRODUCTION_QUALIFICATION_REPORT.md) and
[`benchmarks/reports/s8_qualification/`](../benchmarks/reports/s8_qualification/).
Published v1 bundles remain a **separate** authority from runtime qualification.

## Safe to claim publicly now

- Convex shield projection with **`simplex`, `turn_feasibility`, `box`, `rate`** constraints.
- **Independent residual and status verification** before any corrected action is released.
- Governed, hash-indexed **published benchmark bundles** with provenance and release metadata.
- Flagship **`host-realistic-20260525`**: closed export→bank→publish loop at **`vendor_native`** tier (bundle authority; not the same as S8 host runtime numbers).
- **Reference CVXPY/Moreau** path for parity and reproducible reference arms (**requires** licensed Moreau on a supported OS — not native Windows).
- **Native compiled sequential** and **true batched compiled** solve APIs exist (`NATIVE_MOREAU`, `NATIVE_MOREAU_BATCH`) on vendor-capable hosts.
- **Public Clarabel / SCS / AUTO** paths run without vendor credentials; Windows public mode is a qualified operating mode.
- Batch path is **governed and viability-tested** (not universally faster); default public narrative remains **viability_only**.
- Host-realistic export uses **live upstream dump** with **fork** topology validated via pinned inter-sim API.
- Differentiation tooling supports **finite-difference validation** (Layer F), not a productized autograd stack.
- Episode reset clears warm-start / projector state; concurrency models are declared on stateful projectors.
- Vendor CI is wired to fail on capability skips when `CONICSHIELD_VENDOR_REQUIRED=1` (attestation requires secrets).

## Qualified claims only

- **Throughput / batch speedup:** only where `batch_solve_report` and policy tiers support it; default public narrative remains **viability_only** (see `reference_system_status.json`).
- **Native arm metrics:** only for bundles with `includes_native_arm` and appropriate `evidence_tier`, or S8 cells with status `ok` on Moreau backends (not this Windows host capture).
- **Public path latency (p50/p95/p99/max):** only with environment provenance from `decision_grade_summary.json`; host-specific.
- **Parity:** only for arms listed under `publishable_arms` with green gates at publish time.
- **Graph realism:** fork topology via inter-sim — **not** full Maps/session navigation unless future provenance documents it.
- **WSL Moreau sidecar:** protocol and scaffolding exist; declared qualification is **not** production-ready live Moreau until attested.

## Not yet claimable

- `progress` / `clearance` constraint kinds.
- Production **shield autograd** or differentiable-shield product guarantees.
- **`conicshield-shield-qp-micro-v1`** or other families as reference authority.
- Universal **batch speedup** on all scenarios.
- Full **navigation-session** upstream graphs for the flagship export.
- **Native Windows Moreau** support (unsupported by platform policy).
- Moreau CVXPY / native / CUDA / sidecar **latency or throughput** numbers from hosts where those cells are `NOT_RUN`.
- Second-family or Option B/C platform features ([V2_STRATEGY.md](V2_STRATEGY.md)).
- Track 1 merge-to-`main` completion while vendor attestation / v1-lock cadence gates remain red (see [`stabilization/RELEASE_GATE_EVALUATION.md`](stabilization/RELEASE_GATE_EVALUATION.md)).
