# Promotion gates

## R1 — Advanced solver assurance

Advanced sampling may enter production only when it is shown that mandatory verification remains complete and sampling affects only the optional secondary solve.

**Wave 6 status:** Public-solver sampling study now emits Wilson 95% intervals and a cost-detection curve (CI-small + nightly). Candidate-stack promotion and formal R1.H1/H2 hypothesis protocols remain runnable. Sampling remains confined to the optional shadow solve. Production promotion remains **not** claimed.

## R2 — Safety-Gradient Observatory

No public differentiable-shield claim until:

- gradients are validated across the scenario corpus;
- active-set transitions are explicitly covered;
- exact and finite-difference agreement is quantified;
- failure and undefined-gradient cases are reported;
- backward solves are independently linked to verified forward solutions.

**Wave 6+ status:** Corpus-wide `exact_research_kkt` / `smoothed_research_projection` vs `central_finite_difference` agreement study exists (CI-small fixture + nightly full), stratified by family/regime with failure modes. Experimental `exact_backend_gradient` wires Moreau `CompiledSolver.backward` under `Settings(enable_grad=True)` with fail-closed assumption checks + FD agreement (WSL/Linux; not Windows-native). Experimental `smoothed_backend_gradient` implements softplus inequality softening on the Moreau shield QP (ε recorded; IFT jacobian; FD agreement vs smoothed map). No vendor envelope API on Moreau 0.3.3 (`moreau.torch` is exact autograd only). Production `BackendCapabilities.differentiation_api` stays **False** (identity still probes `differentiate` / `DiffSettings` / `cvxpylayers` only — unchanged). Research adapters do **not** satisfy a full native exact+smoothed Track-1/S6 gate. Gate **not passed**.

## R3 — Counterfactual frontiers

Final reported results must use Track 1's heterogeneous batch interface. Do not emulate batching through Python loops in publication-grade results. Research adapters must set `batch_emulation: sequential_adapter` when Track 1 batch attestation is unavailable.

**Probe v0.2.1 status:** Safety response map export with regime tags added. Track 1 probe requires a **live** `NATIVE_MOREAU_BATCH` sample (capability discovery alone insufficient). **WSL** with Moreau 0.3.3 live-attested S4 (`batch_emulation=none` on that host). **Native Windows** S4 remains unattested (`sequential_adapter`). S5 live sidecar attested on Windows when `CONICSHIELD_WSL_PYTHON` points at a Moreau WSL venv. Exact + softplus-smoothed experimental grads available on WSL; production `differentiation_api` false. Publication-grade / R3 is host-local only — **not** a production pass.

## R4 — Proof-carrying projection

A public flagship claim requires:

- an explicit assurance semantics document;
- schema validation;
- replay tools;
- corrupted-bundle tests;
- missing-evidence tests;
- version migration rules;
- independent reproduction from a clean environment.

**Wave 7+ status:** Platform-matrix soak harness records OS/Python/CPU/GPU/solver versions/commit/dirty/artifact hashes and supports multi-host aggregation with digest-mismatch flags and explicit `host_kind` (`real` vs `synthetic`). Local **synthetic** second-host simulation + governed-hash **research** adapter exist for aggregation QA. Operator runbook: `MULTI_HOST_SOAK_RUNBOOK.md` (Windows+WSL same-machine distinct-OS policy documented). Optional CI workflow `research-multi-host-soak.yml` runs soak on `ubuntu-latest` + `windows-latest` and aggregates digests (does **not** modify `research-public.yml`; never sets `promotion_claim`). Nightly retains soak artifacts (30-day retention). **Local evidence:** Windows + WSL real soaks aggregated with matching sealed digests → `r4_multi_host_gate_ready=true` (evidence-readiness only). Remote `gh workflow run` blocked until workflow exists on default/remote branch. Gate **not passed** for production/public flagship claims. Evidence levels remain assurance tiers, not universal safety guarantees.

**Still blocking R4 production gate (honest):** (1) governed hash policy integration with **production** release tooling (research adapter only today); (2) optional stronger independence via pushed CI multi-OS matrix or physically separate machines; (3) no overclaim of universal safety from L0–L4 tiers. Synthetic fixtures still **do not count**. Local Windows+WSL multi-host evidence does **not** alone clear production.

## R5 — CBF domain

Promote only after single-step nominal CBF QP is validated; receding horizon remains optional and later.

**Wave 8 status:** Stages 1–3 implemented. Held-out corpus `cbf-v0.1.0` + machine-checkable unexplained-infeasibility taxonomy feed the stage-4 gate. Required checklist criteria pass with committed evidence. Stage-4 status is `experimental_rh_available` with minimal single-agent short-horizon RH filter `rh-v0.1.0` (fail-closed unless checklist green). Full RH-MPC / multi-robot / AD stacks remain **unimplemented**. Domain not production-qualified.

## R6 — Intervention-aware training

Blocked until R2 and R4 promotion gates pass. No claim of "learning safer policies" unless independent safety metrics improve under distribution shift, with failure cases and robustness to solver/smoothing choices.

**Wave 8 status:** Decision document strengthened to a scientific **evidence matrix** (`r6-decision-v0.2.0`) with acceptance criteria, decision logic, and negative-retention protocol — still **BLOCKED**; no training results. R4 multi-host *evidence* advanced (Windows+WSL) and experimental exact native grads exist on WSL, but R2/R4 **production** gates remain unpassed, so R6 stays blocked.
