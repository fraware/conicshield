# Track 2 Research Charter — Solver Assurance and Gradients

## Mission

Extend ConicShield from a governed runtime projector into a solver-assured, structurally compiled, sensitivity-aware safety system — without weakening Track 1 / production guarantees.

## Research sequence

```text
advanced shadow-solver assurance
    -> intervention sensitivity observatory
    -> counterfactual safety frontiers
    -> proof-carrying differentiable projection
    -> one robust conic validation domain
    -> intervention-aware policy training
```

## Isolation

- Experimental code lives under `conicshield/experimental/`, `experiments/`, and this tree.
- Experimental modules are **not** exported from the stable `conicshield` package namespace.
- Frozen published-run APIs, public claims, default runtime backends, production release policy, and governed benchmark families are unchanged until promotion gates pass.
- Research artifacts use explicit experimental schema and family identifiers (`research.solver_assurance.r0`, `research.assurance_bundle.v0`, …).

## Required research questions

1. When do Moreau and independent public solvers disagree on shield outputs?
2. Which observable numerical signals predict disagreement or fallback?
3. How stable is the corrected action under perturbations to policy logits and safety parameters?
4. Where do exact, smoothed, and finite-difference sensitivities disagree?
5. Can local sensitivity identify upcoming active-set transitions?
6. Can counterfactual frontier analysis improve safety-parameter selection?
7. What evidence is sufficient to call a projection "proof-carrying" without overstating its guarantee?
8. Does differentiable training improve safety margin under distribution shift, or merely reduce intervention on the training distribution?

## Wave 1 scope (implemented)

- R0 corpus and hypotheses
- Research schemas
- Public-solver shadow harness
- Finite-difference sensitivity infrastructure
- Experiment reproducibility recording

## Wave 2–5 depth (this tree)

- R1 sampling study, disagreement taxonomy, candidate-stack promotion, formal hypothesis protocols
- R2 observatory depth, dual-pressure correlations, active-set trajectories (`r0-v0.3.0`), research KKT/smoothed adapters
- R3 frontier Pareto + local-global consistency (`batch_emulation: sequential_adapter`, watermarked)
- R4 AssuranceBundle builder / replay / migration / clean-env soak script
- R5 CBF stages 1–3 (stage 4 blocked behind checklist)
- R6 remains blocked

Native differentiation remains out of scope until Track 1 / vendor capabilities are available.
Research adapters must never be relabeled as native Moreau backend gradients.
