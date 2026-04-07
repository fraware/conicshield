# Patches against upstream [inter-sim-rl](https://github.com/fraware/inter-sim-rl)

## `conicshield-m2-shield-context-and-transitions.patch`

ConicShield milestone **M2** semantics:

- `get_shield_context()` aligned with ConicShield `schemas/shield_context.schema.json`
- Action-conditioned transitions with deterministic tie-break (duration, distance, destination)
- `offline_transition_graph` for API-free tests and bank export workflows
- Lazy Google Maps client import so unit tests run without `googlemaps` installed
- `RLEnvironment.step` returns `(state, reward, done, info)` with branch metadata

### Apply

From a clean clone of [fraware/inter-sim-rl](https://github.com/fraware/inter-sim-rl) at the pinned SHA in `REVISION` (or `main` if you resolve conflicts):

```bash
git apply /path/to/conicshield/third_party/inter-sim-rl/patches/conicshield-m2-shield-context-and-transitions.patch
```

Or from this repository root:

```bash
git -C /path/to/inter-sim-rl checkout <sha>
git -C /path/to/inter-sim-rl apply third_party/inter-sim-rl/patches/conicshield-m2-shield-context-and-transitions.patch
```

Upstream tests: `pytest tests/test_rl_environment_shield.py tests/test_reward.py -v`

When these changes are merged into `fraware/inter-sim-rl`, drop the patch file and update `REVISION`.
