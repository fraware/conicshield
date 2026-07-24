# Assurance semantics (proof-carrying discipline)

## Public claim language (fixed)

> ConicShield emits independently checkable numerical evidence for a declared projection problem, with optional cross-solver and sensitivity evidence under explicit qualification levels.

This is **not** a system-level safety proof and does not claim universal safety. Evidence levels L0–L4 are numerical assurance tiers only.

Flagship object: `conicshield.experimental.assurance.proof_carrying.ProofCarryingProjection` (R14). Promotion predicates live in `evaluate_flagship_promotion_gate` and remain fail-closed (including sidecar protocol v2 features, native Moreau multi-host participation, real linked gradients, verified CBF, corrupted/incomplete rejection, recomputed digests, and this limitations statement).

## Naming

Use the term **proof-carrying** only with an explicit evidence taxonomy. The object must distinguish:

| Kind | Meaning |
| ---- | ------- |
| analytically checked facts | Closed-form or symbolic checks |
| machine-evaluated numerical residuals | Independently recomputed residuals |
| solver-reported claims | Status, duals, iterations from a solver |
| cross-solver agreement | Shadow comparison on the same problem |
| empirical gradient validation | FD / exact / smoothed agreement metrics |
| unverified contextual assumptions | Declared and marked unverified |

Evidence levels **L0–L4** are **numerical assurance tiers**, not universal safety guarantees and **not** system-level safety proofs. **L4 is numerical assurance, not a safety proof.**

## Three-valued verification

| Status | Meaning |
| ------ | ------- |
| `VERIFIED_FEASIBLE` | Residuals present, finite, within tolerance; status policy confirms feasibility |
| `VERIFIED_INFEASIBLE` | Residuals present and independently show infeasibility / failing status policy |
| `UNVERIFIED` | Missing residuals, action, or specification — **never** coerce missing evidence to zero |

Boolean `primal_feasible` may be retained as a derived field; level gates use `verification_status`.

## Four independent full SHA-256 digests

| Digest | Inputs only | Notes |
| ------ | ----------- | ----- |
| `topology_digest` | dims, sparse indices, cone topology, structural flags | **Never** include active set |
| `problem_digest` | topology + spec + proposed/prev/ref actions + weights + bounds + solver-independent tolerances | Canonical JSON |
| `forward_solution_digest` | problem + corrected action + primal/dual + canonical status + verification report | |
| `evidence_bundle_digest` | forward + shadow + sensitivity + provenance + replay + governed manifest | |

Digests are **full** SHA-256 hex (64 chars). Truncated `[:16]` digests are deprecated (`pre_v1_digest_semantics`).

## Levels

- `L0_RECORDED` — complete normalized problem manifest, corrected action, provenance, bundle digest (no feasibility claim). Missing residuals ⇒ ≤ L0.
- `L1_FEASIBILITY_VERIFIED` — L0 + recomputed residuals + verified status policy + `VERIFIED_FEASIBLE` + no required field missing.
- `L2_SHADOW_COMPARED` — L1 + second backend on the **same** `problem_digest` + independently verified second result + disagreement metrics; **reject copied primary-as-shadow**.
- `L3_SENSITIVITY_VALIDATED` — L1 + **live** sensitivity linked to exact `forward_solution_digest` + declared mode + finite Jacobian + FD comparison + active-set stability + thresholds + backend/version provenance. Manual / synthetic `jacobian_norm` injection **does not** qualify. Keep **smoothed** vs **exact** as separate modes.
- `L4_REPLAYED_AND_GOVERNED` — required lower evidence + attested governed manifest + exact commit + immutable artifact index + ≥2 independent qualification envs + matching problem digests + replay success + no synthetic host/sensitivity + clean worktree + schema migration checks. Governed-hash verify must check **actual** artifact hashes + attestation — nonempty digest strings alone **do not** pass.

## Schema and tooling

See `schemas/assurance_bundle.schema.json` and `conicshield.experimental.assurance`.

- Builder: `build_assurance_bundle`
- Replay: `replay_bundle` / `load_bundle`
- Checks: `run_machine_checks` (recomputes digests, residuals, shadow/sensitivity linkage, governed hashes, level consistency)
- Migration: `normalize_bundle_dict` — missing `schema_id` treated as `research.assurance_bundle.v0` (deprecated); migrates to `research.assurance_bundle.v1` with invalidation watermark. Archival load (`archival=True`) keeps v0 readable and fail-closed for promotion.
- Status: `status_report.write_research_status` regenerates `RESEARCH_STATUS.md` from gate JSON records.

## Empirical gradient validation kinds

| Mode label | Meaning | Status |
| ---------- | ------- | ------ |
| `central_finite_difference` / `one_sided_finite_difference` | Numerical FD of the public projection map | implemented |
| `exact_backend_gradient` | Native / vendor Moreau exact gradient via `CompiledSolver.backward` + `enable_grad` | **experimental implemented** (WSL/Linux; UNAVAILABLE on native Windows). Production `differentiation_api` identity flag stays **False**. |
| `smoothed_backend_gradient` | Softplus inequality softening on the Moreau shield QP (ε recorded); IFT jacobian | **experimental implemented** (same host gate as exact). Not a vendor envelope API. |
| `exact_research_kkt` | Fixed-active-set KKT sensitivity of the **public QP** | research adapter (not native Moreau) |
| `smoothed_research_projection` | Quadratic-penalty smoothed public projection + FD Jacobian | research adapter (explicit ε) |

Never relabel `exact_research_kkt` or `smoothed_research_projection` as native backend gradients.
Gradient confidence fields on AssuranceBundle sensitivity evidence must record the mode string verbatim.
`SensitivityEvidence.synthetic=true` (or missing FD pass) blocks L3+.

## Version migration rules (summary)

1. Current schema id: `research.assurance_bundle.v1`.
2. `research.assurance_bundle.v0_legacy` migrates via `migrate_v0_legacy_to_v0` (`action`→`corrected_action`, `level`→`evidence_level`).
3. `research.assurance_bundle.v0` migrates via `migrate_v0_to_v1` (full digests, three-valued verification, downgrade overclaimed L3/L4, `invalidation_reason=pre_v1_digest_semantics`, `promotion_eligible=false`).
4. v0 remains loadable as deprecated/invalidated (`archival=True`).
5. Do not silently reinterpret evidence kinds or levels across versions.
6. Forward migrations must be explicit callables registered in `MIGRATION_RULES`.
7. Preserve unknown `extras` keys when migrating.
8. Sealed `corrected_action_digest` checks catch action corruption against a recorded digest.

## Platform soak aggregate (R12)

- Current aggregate schema: `research.platform_soak_aggregate.v1`.
- Matrix roles: `linux_public`, `windows_public`, `linux_wsl_moreau_cpu`, `linux_moreau_cuda`, `windows_wsl_sidecar`.
- Per-host artifacts: exact commit, `dirty_worktree=false`, package provenance, problem + forward digests, shadow/replay, artifact index, environment signature; live gradient required when L3 is claimed.
- Aggregate gate: byte-identical problem digests; tolerance vs byte-identity for numerical fields; rejects synthetic hosts, missing L3 gradients, stale commits, provenance mismatch, synthetic sensitivity; Moreau claims need ≥1 native Moreau host; L4 candidates need ≥2 independent envs.
- `r4_multi_host_gate_ready` may be true only when R12 predicates pass; `promotion_claim` / `promotion_eligible` remain false.
- Historical Phase-0 / v0 aggregates stay invalidated via `annotate_deprecated_soak_artifact` (`awaiting_r12_multihost_rebuild` watermark preserved on archival files).
- Governed-hash policy (`research.governed_hash_policy.v1`) verifies **actual** on-disk artifact hashes + attestation — nonempty digest strings alone do not pass.
