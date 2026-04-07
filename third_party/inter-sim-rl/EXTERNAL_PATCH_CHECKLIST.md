# Upstream patch checklist ([inter-sim-rl](https://github.com/fraware/inter-sim-rl))

**ConicShield:** [docs/INTER_SIM_RL_INTEGRATION.md](../../docs/INTER_SIM_RL_INTEGRATION.md).

Use this when cutting a release of the upstream environment that ConicShield benchmarks against.

- [ ] `get_shield_context()` includes at least: `allowed_actions`, `blocked_actions`, `action_upper_bounds`, `rule_choice`, `previous_instruction`, `hazard_score` (see `schemas/shield_context.schema.json`).
- [ ] Transition sampling depends on the **chosen** discrete action where multiple graph branches exist; document tie-break (duration, distance, lexical) to match `ReplayGraphEnvironment._canonical_candidate_sort_key`.
- [ ] Deterministic fallback when the requested action class has no matching edge.
- [ ] DQN observation vector compatible with `InterSimKerasDQNPolicy` (1D `get_state_vector()` or array).
- [ ] Update `third_party/inter-sim-rl/REVISION` and `docs/INTER_SIM_RL_INTEGRATION.md` with the new SHA after validation.
