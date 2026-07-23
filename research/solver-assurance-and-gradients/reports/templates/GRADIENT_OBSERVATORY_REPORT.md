# Safety-Gradient Observatory report template

## Questions to answer

- Where gradients are stable
- Where gradients become ambiguous
- Which smoothing settings improve stability
- What accuracy cost smoothing introduces
- Which evidence fields are required to communicate gradient confidence

## Modes (keep distinct)

- `exact_backend_gradient` (native/vendor — experimental `CompiledSolver.backward`)
- `smoothed_backend_gradient` (experimental softplus Moreau-QP softening; ε recorded)
- `exact_research_kkt` (public-QP KKT research adapter — not native Moreau)
- `smoothed_research_projection` (epsilon-smoothed public projection research adapter)
- `central_finite_difference`
- `one_sided_finite_difference`

## Status

FD modes implemented with active-set / residual / runtime / failure fields. Native exact/smoothed are experimental implementations (`AVAILABLE` / `UNAVAILABLE`, never stub placeholders). Research KKT/smoothed adapters are labeled distinctly and never alias native modes. Fill the machine-readable sections from observatory JSON artifacts via `render_observatory_report_markdown`.
