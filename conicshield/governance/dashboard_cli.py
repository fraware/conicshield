from __future__ import annotations

import argparse
import json
from pathlib import Path

from conicshield.governance.dashboard import build_governance_dashboard, render_markdown_dashboard


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate benchmark governance dashboard.")
    parser.add_argument("--json-output", type=Path, default=None)
    parser.add_argument("--markdown-output", type=Path, default=None)
    args = parser.parse_args()

    dashboard = build_governance_dashboard()
    payload = dashboard.as_dict()
    markdown = render_markdown_dashboard(dashboard)

    if args.json_output is not None:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    else:
        print(json.dumps(payload, indent=2))

    if args.markdown_output is not None:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(markdown, encoding="utf-8")
    elif args.json_output is not None:
        print(markdown)


if __name__ == "__main__":
    main()
