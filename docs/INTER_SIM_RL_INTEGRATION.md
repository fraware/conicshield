# `inter-sim-rl` integration plan

This repository is intentionally standalone. It does not vendor the external `inter-sim-rl` codebase.

## Integration seam

1. external environment produces a state object and a four-action space
2. external policy produces four Q-values or action scores
3. ConicShield consumes:
   - `q_values`
   - `action_space`
   - `context`
4. ConicShield returns a corrected action string

## Expected action space

```python
["turn_left", "turn_right", "go_straight", "turn_back"]
```

## Expected context shape

At minimum:
- `allowed_actions`
- `blocked_actions`
- `action_upper_bounds`
- `rule_choice`
- `previous_instruction`
- `hazard_score`

Optional:
- `current_heading_deg`
- `branch_bearings_deg`
- transition-bank candidate metadata

## Recommended patch surface in the external environment

- add `get_shield_context()`
- preserve the current observation contract
- let chosen action affect transitions
- expose a transition-bank export path
