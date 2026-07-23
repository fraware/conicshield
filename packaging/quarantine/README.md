# Quarantined solver stack candidates

Candidate dependency upgrades live here so scheduled qualification can exercise
them **without** changing production defaults under `packaging/constraints/`.

Promotion requires a maintainer PR that:

1. Moves an attested pin into `packaging/constraints/`
2. Updates `packaging/solver_stack_policy.json` production defaults
3. Clears or archives the quarantine candidate entry
