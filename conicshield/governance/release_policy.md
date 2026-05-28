# Release policy (in-tree)

Governed release rules enforced by `release_cli`, `finalize_cli`, and `audit_cli`.

- Family `CURRENT.json` is updated only through governed tooling or an explicit maintainer PR with `make verify-reference-system` green.
- Do not hand-edit `publishable_arms` or gate fields without parity artifacts.
- Flagship authority: `host-realistic-20260525` for `conicshield-transition-bank-v1`.

Public claims: [`docs/PUBLIC_CLAIMS.md`](../../docs/PUBLIC_CLAIMS.md). Maintainer workflow: [`CONTRIBUTING.md`](../../CONTRIBUTING.md).
