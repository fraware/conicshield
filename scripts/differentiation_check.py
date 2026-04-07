#!/usr/bin/env python3
"""Layer F (optional): differentiation status; full validation deferred per policy."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _collect() -> dict[str, Any]:
    return {
        "generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "deferred",
        "message": (
            "Gradient validation is not yet a governed gate. "
            "See docs/DIFFERENTIATION_VALIDATION_POLICY.md and NativeMoreauCompiledOptions.enable_grad."
        ),
        "recommended_next_steps": [
            "Vendor confirmation of differentiable API surface for this repo",
            "Finite-difference checks on small QPs",
            "Optional PyTorch/JAX tests behind extras",
        ],
    }


def _write_md(path: Path, data: dict[str, Any]) -> None:
    lines = [
        "# Differentiation report",
        "",
        f"Generated: {data.get('generated_at_utc', '')}",
        "",
        f"**Status:** {data.get('status')}",
        "",
        data.get("message", ""),
        "",
        "## Next steps",
        "",
    ]
    for s in data.get("recommended_next_steps", []):
        lines.append(f"- {s}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser(description="Write differentiation_summary under output/.")
    p.add_argument("--out-dir", type=Path, default=None, help="Default: repo output/")
    args = p.parse_args()
    root = Path(__file__).resolve().parents[1]
    out_dir = args.out_dir or (root / "output")
    out_dir.mkdir(parents=True, exist_ok=True)
    data = _collect()
    (out_dir / "differentiation_summary.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    _write_md(out_dir / "differentiation_report.md", data)
    print(out_dir / "differentiation_summary.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
