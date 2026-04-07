# ADR 001: `progress` and `clearance` SafetySpec kinds (deferred)

## Status

Accepted as **deferred** until a benchmark card or shield deployment requires these constraint kinds.

## Context

[`SafetySpec`](../../conicshield/specs/schema.py) may include constraint kinds `progress` and `clearance`. Today [`parse_safety_spec_for_shield`](../../conicshield/specs/shield_qp.py) raises `NotImplementedError` for them (see [`ENGINEERING_STATUS.md`](../../ENGINEERING_STATUS.md)).

## Decision

Do **not** implement projection for `progress` / `clearance` until:

1. Product defines semantics (e.g. monotone progress along a route axis vs clearance tubes in state space).
2. Engineering maps semantics to the existing QP/conic family (or documents why a different solver family is required).
3. Governance updates task contract / family rules if new kinds affect benchmark meaning.

## Consequences

- Benchmarks and shields must use implemented kinds (simplex, turn feasibility, box, rate, etc.) until this ADR is superseded.
- When implemented: add unit tests mirroring other constraint kinds, update schemas if evidence payloads change, and follow [`BENCHMARK_GOVERNANCE.md`](../../BENCHMARK_GOVERNANCE.md) for family impact.

## References

- Handoff [`ENGINEERING_HANDOFF_IMPLEMENTATION_PLAN.md`](../../ENGINEERING_HANDOFF_IMPLEMENTATION_PLAN.md) §6.2 high-touch files
- Moreau/CVXPY integration: [`docs/MOREAU_API_NOTES.md`](../MOREAU_API_NOTES.md)
