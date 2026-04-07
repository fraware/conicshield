#!/usr/bin/env python3
"""Aggregate verification JSON artifacts into trust_dashboard.{html,md}."""

from __future__ import annotations

import argparse
import html
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load(path: Path) -> Any | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _section(title: str, data: Any) -> str:
    if data is None:
        return f'<h2>{html.escape(title)}</h2><p class="muted">No artifact.</p>'
    body = html.escape(json.dumps(data, indent=2)[:12000])
    return f"<h2>{html.escape(title)}</h2><pre>{body}</pre>"


def main() -> int:
    p = argparse.ArgumentParser(description="Aggregate verification JSON into trust_dashboard HTML/MD.")
    p.add_argument(
        "--artifact-dir",
        type=Path,
        default=None,
        help="Directory containing verification JSON files (default: repo output/).",
    )
    p.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Where to write trust_dashboard.html and .md (default: same as --artifact-dir).",
    )
    args = p.parse_args()

    artifact_dir = args.artifact_dir or (_repo_root() / "output")
    artifact_dir.mkdir(parents=True, exist_ok=True)
    out_dir = args.out_dir or artifact_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    env = _load(artifact_dir / "environment_check.json")
    smoke = _load(artifact_dir / "smoke_check.json")
    refc = _load(artifact_dir / "reference_correctness_summary.json")
    parity = _load(artifact_dir / "native_parity_local" / "parity_summary.json")
    if parity is None:
        parity = _load(artifact_dir / "parity_summary.json")
    perf = _load(artifact_dir / "performance_summary.json")
    gov = _load(artifact_dir / "governance_dashboard.json")
    diff = _load(artifact_dir / "differentiation_summary.json")

    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    dir_label = str(artifact_dir)

    md_parts = [
        "# Trust dashboard",
        "",
        f"Generated: {now}",
        "",
        f"Artifact directory: `{dir_label}`",
        "",
        "Aggregates JSON artifacts from verification scripts. ",
        "Re-run individual scripts to refresh each section.",
        "",
    ]
    for title, path, data in [
        ("Environment", "environment_check.json", env),
        ("Smoke", "smoke_check.json", smoke),
        ("Reference correctness (minimal)", "reference_correctness_summary.json", refc),
        ("Native parity", "native_parity_local/parity_summary.json or parity_summary.json", parity),
        ("Performance", "performance_summary.json", perf),
        ("Governance dashboard", "governance_dashboard.json", gov),
        ("Differentiation", "differentiation_summary.json", diff),
    ]:
        md_parts.append(f"## {title}")
        md_parts.append("")
        if data is None:
            md_parts.append(f"_(Missing `{path}`)_")
        else:
            md_parts.append("```json")
            md_parts.append(json.dumps(data, indent=2)[:8000])
            md_parts.append("```")
        md_parts.append("")

    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>ConicShield trust dashboard</title>
  <style>
    body {{ font-family: system-ui, Segoe UI, sans-serif; margin: 2rem; background: #0f1419; color: #e6edf3; }}
    h1 {{ font-size: 1.35rem; }}
    h2 {{ font-size: 1.1rem; margin-top: 2rem; color: #8b949e; }}
    pre {{ background: #161b22; padding: 1rem; overflow: auto; max-height: 28rem; font-size: 0.8rem; }}
    .muted {{ color: #6e7681; }}
    .meta {{ color: #8b949e; font-size: 0.9rem; }}
  </style>
</head>
<body>
  <h1>Trust dashboard</h1>
  <p class="meta">Generated {html.escape(now)} · artifacts from <code>{html.escape(dir_label)}</code></p>
  {_section("Environment", env)}
  {_section("Smoke", smoke)}
  {_section("Reference correctness", refc)}
  {_section("Native parity", parity)}
  {_section("Performance", perf)}
  {_section("Governance", gov)}
  {_section("Differentiation", diff)}
</body>
</html>
"""

    (out_dir / "trust_dashboard.md").write_text("\n".join(md_parts), encoding="utf-8")
    (out_dir / "trust_dashboard.html").write_text(html_doc, encoding="utf-8")
    print(out_dir / "trust_dashboard.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
