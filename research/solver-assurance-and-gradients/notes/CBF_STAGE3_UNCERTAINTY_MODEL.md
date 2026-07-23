# CBF stage 3 — uncertainty model notes

## Model id

`bounded_l2_position_observation_noise.v1`

## Justification

Stage 3 implements an uncertainty-aware SOC robust margin only under an explicit
observation-noise model. We do **not** claim robustness to unspecified plant
mismatch or adversarial dynamics.

Assumed model:

- True position \(p^\star\), observed position \(p = p^\star + \delta\).
- Hard bound \(\|\delta\|_2 \le \varepsilon\).
- Single-integrator kinematics \(\dot p = u\).
- Circular obstacle barrier \(h(p) = \|p - c\|^2 - r^2\).

## Robust CBF requirement

\[
\inf_{\|\delta\|_2\le\varepsilon}
\Big(2(p+\delta-c)\cdot u + \alpha\, h(p+\delta)\Big) \ge 0.
\]

## Conservative SOC sufficient condition

Using \(\|2\delta\cdot u\| \le 2\varepsilon\|u\|\) and
\(h(p+\delta) \ge h(p) - 2\varepsilon\|p-c\| - \varepsilon^2\) (lower bound used
conservatively on the required inequality), a sufficient condition is:

\[
2(p-c)\cdot u + \alpha h(p)
\ge 2\varepsilon\|u\| + \alpha\big(2\varepsilon\|p-c\| + \varepsilon^2\big).
\]

Encoded with slack \(t\):

\[
a\cdot u - t \ge b_{\mathrm{rob}},\qquad t \ge 2\varepsilon\|u\|_2,
\]

which is second-order-cone representable.

## Non-claims

- Not a certificate against model error beyond bounded observation noise.
- Stage 4 receding horizon remains blocked until the validation checklist in
  `stage4_gate_status` is fully satisfied.
- Moreau / vendor differentiable filters remain fail-closed on the public path when unavailable.
