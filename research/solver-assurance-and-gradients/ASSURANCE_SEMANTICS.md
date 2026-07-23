# Assurance semantics (proof-carrying discipline)

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

Evidence levels **L0–L4** are assurance tiers, not universal safety guarantees.

## Levels

- `L0_RECORDED` — solution and provenance recorded
- `L1_FEASIBILITY_VERIFIED` — residuals recomputed and feasible
- `L2_SHADOW_COMPARED` — independent shadow solver compared
- `L3_SENSITIVITY_VALIDATED` — sensitivity evidence linked to forward solution
- `L4_REPLAYED_AND_GOVERNED` — replayed under governance with hash verification

## Schema and tooling

See `schemas/assurance_bundle.schema.json` and `conicshield.experimental.assurance`.

- Builder: `build_assurance_bundle`
- Replay: `replay_bundle` / `load_bundle`
- Checks: `run_machine_checks` (digest, residuals, provenance, fallback, sensitivity/shadow linkage, level consistency)
- Migration: `normalize_bundle_dict` — missing `schema_id` treated as `research.assurance_bundle.v0`; unknown schemas fail closed unless an explicit rule exists in `MIGRATION_RULES`

## Empirical gradient validation kinds

| Mode label | Meaning | Status |
| ---------- | ------- | ------ |
| `central_finite_difference` / `one_sided_finite_difference` | Numerical FD of the public projection map | implemented |
| `exact_backend_gradient` | Native / vendor Moreau exact gradient via `CompiledSolver.backward` + `enable_grad` | **experimental implemented** (WSL/Linux; UNAVAILABLE on native Windows). Production `differentiation_api` identity flag stays **False**. |
| `smoothed_backend_gradient` | Softplus inequality softening on the Moreau shield QP (ε recorded); IFT jacobian | **experimental implemented** (same host gate as exact). Not a vendor envelope API. |
| `exact_research_kkt` | Fixed-active-set KKT sensitivity of the **public QP** | research adapter (not native Moreau) |
| `smoothed_research_projection` | Quadratic-penalty smoothed public projection + FD Jacobian | research adapter (explicit \(\varepsilon\)) |

Never relabel `exact_research_kkt` or `smoothed_research_projection` as native backend gradients.
Gradient confidence fields on AssuranceBundle sensitivity evidence must record the mode string verbatim.

## Version migration rules (summary)

1. Current schema id: `research.assurance_bundle.v0`.
2. `research.assurance_bundle.v0_legacy` migrates via `migrate_v0_legacy_to_v0` (`action`→`corrected_action`, `level`→`evidence_level`).
3. Do not silently reinterpret evidence kinds or levels across versions.
4. Forward migrations must be explicit callables registered in `MIGRATION_RULES`.
5. Preserve unknown `extras` keys when migrating.
6. Sealed `corrected_action_digest` checks catch action corruption against a recorded digest.
