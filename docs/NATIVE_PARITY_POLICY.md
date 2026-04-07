# Native parity policy

## Purpose

Native compiled Moreau (`Backend.NATIVE_MOREAU`) must **not** be treated as equivalent to the reference shield path until it passes **parity gates** against a governed frozen reference stream.

## Single source of thresholds

Canonical numeric thresholds live in code:

- Module: `conicshield.parity.gates`
- Function: `list_default_parity_gate_violations`, `enforce_default_parity_gates`

Current defaults (see that module for live values):

- Action match rate = 1.0
- Active constraints match rate >= 0.999
- `max_corrected_linf` <= 1e-5
- `p95_corrected_linf` <= 1e-6
- `max_corrected_l2` <= 1e-5

Do not duplicate threshold numbers in documentation without pointing to `parity.gates` as authoritative.

## Protocol

1. **Frozen reference:** `tests/fixtures/parity_reference/` (episodes, config, transition bank) governed by [FIXTURE_POLICY.md](FIXTURE_POLICY.md).
2. **Replay:** `python -m conicshield.parity.cli --reference-dir ... --out-dir ...`
3. **Artifacts:** `parity_summary.json`, `parity_steps.jsonl` under the output directory.
4. **Promotion:** When replacing the fixture with a real reference run, follow [PARITY_FIXTURE_PROMOTION.md](PARITY_FIXTURE_PROMOTION.md).

## Makefile

- `make parity-native-licensed` — local parity check (requires license and native stack).

## Failure semantics

If parity gates fail, the native arm is **not** publishable for native endorsement; benchmark promotion and release flows must treat parity as red until resolved.
