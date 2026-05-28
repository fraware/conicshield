#!/usr/bin/env python3
"""Print ``gh api`` steps to align ``main`` with expected-branch-protection-main.json."""

from __future__ import annotations

import json
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    spec = json.loads(
        (root / ".github" / "expected-branch-protection-main.json").read_text(encoding="utf-8")
    )
    contexts = spec["required_status_checks"]
    print("# Requires: gh auth login (repo admin)")
    print("# Verify after: make verify-branch-protection-expectations")
    print("# Record screenshot: docs/BRANCH_PROTECTION_RECORD.md\n")
    print("gh api -X PUT repos/:owner/:repo/branches/main/protection \\")
    print('  -f required_status_checks[strict]=true \\')
    for ctx in contexts:
        print(f'  -f required_status_checks[contexts][]={ctx} \\')
    print("  -f enforce_admins=true \\")
    print("  -f required_pull_request_reviews[required_approving_review_count]=1 \\")
    print("  -f restrictions=null")
    print("\n# Do NOT add:", ", ".join(spec["not_required_status_checks"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
