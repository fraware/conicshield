from __future__ import annotations

import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


RUNBOOK_TEXT = (_repo_root() / "docs" / "MAINTAINER_RUNBOOK.md").read_text(encoding="utf-8")


def main() -> None:
    out = sys.stdout
    if hasattr(out, "reconfigure"):
        out.reconfigure(encoding="utf-8", errors="replace")
    print(RUNBOOK_TEXT, end="")


if __name__ == "__main__":
    main()
