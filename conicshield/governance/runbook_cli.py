from __future__ import annotations

from pathlib import Path

RUNBOOK_TEXT = Path("MAINTAINER_RUNBOOK.md").read_text(encoding="utf-8")


def main() -> None:
    print(RUNBOOK_TEXT)


if __name__ == "__main__":
    main()
