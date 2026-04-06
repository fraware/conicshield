# Release Orchestration Policy

The release orchestrator has exactly two legal outputs:
1. same-family publication
2. new-family fork and publication

## Same-family publication

Allowed only when:
- the run is already review-locked
- artifact gate is green
- promotion gate is green
- parity gate is green where required
- family compatibility check says the task contract is still the same family

## New-family fork and publication

Required when:
- the run is promotable, but
- the candidate task contract is not compatible with the current published family

A family bump requires:
- `--allow-family-bump`
- `FAMILY_BUMP_NOTE.md` in the run directory
