#!/usr/bin/env python3
"""Build HTML + Markdown summaries from pytest JUnit XML files in output/."""

from __future__ import annotations

import html
import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass
class SuiteStats:
    label: str
    path: str
    tests: int
    failures: int
    errors: int
    skipped: int
    time_sec: float

    @property
    def passed(self) -> int:
        return self.tests - self.failures - self.errors - self.skipped

    @property
    def pass_rate(self) -> float:
        if self.tests <= 0:
            return 0.0
        return 100.0 * self.passed / self.tests


def parse_junit(path: Path) -> SuiteStats | None:
    if not path.is_file():
        return None
    tree = ET.parse(path)
    root = tree.getroot()
    # pytest may emit <testsuites> wrapper or single <testsuite>
    ts = root.find("testsuite") if root.tag == "testsuites" else root
    if ts is None:
        return None
    return SuiteStats(
        label=path.stem,
        path=str(path.relative_to(path.parents[1]) if len(path.parts) > 1 else path),
        tests=int(ts.attrib.get("tests", 0)),
        failures=int(ts.attrib.get("failures", 0)),
        errors=int(ts.attrib.get("errors", 0)),
        skipped=int(ts.attrib.get("skipped", 0)),
        time_sec=float(ts.attrib.get("time", 0.0)),
    )


def bar_row(label: str, rate: float, note: str = "") -> str:
    rate = max(0.0, min(100.0, rate))
    color = "#2d7a3e" if rate >= 99.0 else "#b8860b" if rate >= 90 else "#a33"
    bar_style = f"width:{rate:.1f}%;background:{color}"
    return f"""
    <tr>
      <td class="lbl">{html.escape(label)}</td>
      <td class="barcell"><div class="bar" style="{bar_style}"></div><span class="pct">{rate:.1f}%</span></td>
      <td class="note">{html.escape(note)}</td>
    </tr>"""


def load_moreau_metrics(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def moreau_metrics_md(data: dict[str, Any]) -> str:
    env = data.get("environment", {})
    sm = data.get("summary", {})
    cp = sm.get("call_phase", {})
    gen = data.get("generated_at_utc", "—")
    pver = data.get("pytest_version", "—")
    ex = data.get("pytest_exitstatus", "—")
    mi = env.get("moreau_importable", "—")
    reg = env.get("cvxpy_moreau_registered", "—")
    coll = sm.get("collected_moreau_related", "—")
    exe = sm.get("executed_moreau_related", "—")
    lines = [
        "## Moreau metrics (last pytest run)",
        "",
        f"- Generated: `{gen}` · pytest `{pver}` · exit `{ex}`",
        f"- `moreau` importable: **{mi}** · `cp.MOREAU` registered: **{reg}**",
        f"- Collected (Moreau-related): **{coll}** · Executed with traces: **{exe}**",
        (
            f"- Call phase: `passed={cp.get('passed')}` `skipped={cp.get('skipped')}` "
            f"`failed={cp.get('failed')}` `setup_failed={cp.get('setup_failed')}`"
        ),
        (
            f"- Call time (s): total **{cp.get('total_call_time_sec')}** · mean "
            f"**{cp.get('mean_call_time_sec')}** · max **{cp.get('max_call_time_sec')}** "
            f"(`n={cp.get('call_samples')}`)"
        ),
        "",
        "Per-test detail is in `output/moreau_metrics.json` (`per_test`).",
        "",
    ]
    return "\n".join(lines)


def moreau_metrics_html(data: dict[str, Any]) -> str:
    env = data.get("environment", {})
    sm = data.get("summary", {})
    cp = sm.get("call_phase", {})
    g = str(data.get("generated_at_utc", "—"))
    pv = str(data.get("pytest_version", "—"))
    ex = data.get("pytest_exitstatus", "—")
    meta = f"Generated {html.escape(g)} · pytest {html.escape(pv)} · exit {ex}"
    rows: list[tuple[str, str]] = [
        ("moreau importable", str(env.get("moreau_importable"))),
        ("cp.MOREAU registered", str(env.get("cvxpy_moreau_registered"))),
        ("Collected Moreau-related", str(sm.get("collected_moreau_related"))),
        ("Executed (traced)", str(sm.get("executed_moreau_related"))),
        (
            "Call phase",
            (
                f"passed {cp.get('passed')} · skipped {cp.get('skipped')} · "
                f"failed {cp.get('failed')} · setup_failed {cp.get('setup_failed')}"
            ),
        ),
        (
            "Call time (s)",
            (
                f"total {cp.get('total_call_time_sec')} · mean {cp.get('mean_call_time_sec')} · "
                f"max {cp.get('max_call_time_sec')} (n={cp.get('call_samples')})"
            ),
        ),
    ]
    body = []
    for lbl, val in rows:
        body.append(
            f'      <tr><td class="lbl">{html.escape(lbl)}</td>' f'<td colspan="2">{html.escape(val)}</td></tr>'
        )
    return (
        "\n"
        "  <h2>Moreau metrics (last pytest run)</h2>\n"
        f'  <p class="meta">{meta}</p>\n'
        "  <table>\n"
        "    <tbody>\n" + "\n".join(body) + "\n"
        "    </tbody>\n"
        "  </table>\n"
        '  <p class="meta">Full per-test phases: <code>output/moreau_metrics.json</code></p>\n'
    )


def moreau_metrics_missing_md() -> str:
    return "## Moreau metrics\n\n" "_(No `output/moreau_metrics.json` — run pytest once to generate.)_\n\n"


def moreau_metrics_missing_html() -> str:
    return (
        "  <h2>Moreau metrics</h2>\n"
        '  <p class="muted">No output/moreau_metrics.json — run pytest once to generate.</p>\n'
    )


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    out = repo / "output"
    out.mkdir(parents=True, exist_ok=True)

    suites: list[tuple[str, Path]] = [
        ("Windows — full pytest (all markers)", out / "pytest_windows.xml"),
        ("WSL Ubuntu — full pytest (scripts/run_full_pytest.py)", out / "pytest_wsl_full.xml"),
        ("WSL Ubuntu — vendor Moreau subset", out / "pytest_wsl_vendor.xml"),
    ]

    rows_html: list[str] = []
    rows_md: list[str] = []
    for label, p in suites:
        st = parse_junit(p)
        if st is None:
            rows_html.append(f'<tr><td colspan="3" class="muted">No data: {html.escape(str(p))}</td></tr>')
            rows_md.append(f"| {label} | — | — | (missing {p.name}) |")
            continue
        note = f"{st.passed}/{st.tests} passed, {st.skipped} skipped, {st.failures}F {st.errors}E, {st.time_sec:.1f}s"
        rows_html.append(bar_row(label, st.pass_rate, note))
        rows_md.append(f"| {label} | {st.pass_rate:.1f}% | {st.passed}/{st.tests} | {st.skipped} skipped |")

    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    moreau_path = out / "moreau_metrics.json"
    moreau_data = load_moreau_metrics(moreau_path)
    moreau_md_block = moreau_metrics_md(moreau_data) if moreau_data else moreau_metrics_missing_md()

    md = f"""# ConicShield test run snapshot

Generated: {now}

## Summary matrix

| Track | Pass rate | Passed / total | Skipped |
|-------|-----------|------------------|---------|
{chr(10).join(rows_md)}

{moreau_md_block}
## How to read

- **Windows full pytest**: broad suite on host Python; vendor Moreau tests may skip without Gemfury + license.
- **WSL full pytest**: same selection with vendor stack installed (see `.venv-wsl` + `scripts/run_full_pytest.py`).
- **WSL vendor subset**: `vendor_moreau` + `requires_moreau` only.

Open `output/test_visual_report.html` in a browser for bar charts.
Moreau timing and outcomes are written to `output/moreau_metrics.json` during pytest runs (see `tests/conftest.py`).

```mermaid
flowchart LR
  A[Static checks] --> B[Unit + integration + slow + inter_sim]
  B --> C{{vendor stack?}}
  C -->|WSL + license| D[Moreau E2E smoke + parity + vendor tests]
  C -->|no| E[Skip or structured errors]
```

"""

    moreau_html_block = moreau_metrics_html(moreau_data) if moreau_data else moreau_metrics_missing_html()

    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>ConicShield test visualization</title>
  <style>
    body {{ font-family: system-ui, Segoe UI, sans-serif; margin: 2rem; background: #0f1419; color: #e6edf3; }}
    h1 {{ font-size: 1.35rem; }}
    h2 {{ font-size: 1.1rem; margin-top: 2rem; color: #8b949e; }}
    table {{ border-collapse: collapse; width: 100%; max-width: 720px; }}
    td {{ padding: 0.5rem 0.75rem; border-bottom: 1px solid #2d333b; vertical-align: middle; }}
    .lbl {{ width: 38%; }}
    .barcell {{ position: relative; width: 52%; }}
    .bar {{ height: 22px; border-radius: 4px; min-width: 4px; }}
    .pct {{ position: absolute; right: 0; top: 0; font-size: 0.85rem; color: #8b949e; }}
    .note {{ font-size: 0.8rem; color: #8b949e; }}
    .muted {{ color: #6e7681; font-style: italic; }}
    .meta {{ color: #8b949e; font-size: 0.9rem; margin-bottom: 1.5rem; }}
    a {{ color: #58a6ff; }}
  </style>
</head>
<body>
  <h1>ConicShield test visualization</h1>
  <p class="meta">Generated {html.escape(now)} · JUnit sources under <code>output/</code></p>
  <p>Pass-rate bars: <strong>passed / (tests − failures − errors)</strong>; skipped counts in the denominator.</p>
  <table>
    <tbody>
{''.join(rows_html)}
    </tbody>
  </table>
{moreau_html_block}
  <h2>Related artifacts</h2>
  <ul>
    <li><code>output/trust_dashboard.html</code> — aggregated verification JSON (run <code>scripts/generate_trust_dashboard.py</code>)</li>
    <li><code>output/moreau_metrics.json</code> — per-test Moreau-related metrics (pytest hook)</li>
    <li><code>output/governance_dashboard.md</code> — governance dashboard</li>
    <li><code>output/governance_dashboard.json</code> — machine-readable dashboard</li>
    <li><code>output/cov_gates.log</code> — coverage-gated run log</li>
    <li><code>output/pytest_windows.log</code> — Windows full pytest log</li>
    <li><code>output/pytest_wsl_full.log</code> — WSL full pytest log</li>
  </ul>
</body>
</html>
"""

    (out / "test_visual_report.md").write_text(md, encoding="utf-8")
    (out / "test_visual_report.html").write_text(html_doc, encoding="utf-8")
    print(f"Wrote {out / 'test_visual_report.html'} and {out / 'test_visual_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
