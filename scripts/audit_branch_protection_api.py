#!/usr/bin/env python3
"""Compare GitHub branch protection on main with expected-branch-protection-main.json."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _github_repo() -> tuple[str, str]:
    env = os.environ.get("GITHUB_REPOSITORY", "")
    if "/" in env:
        owner, repo = env.split("/", 1)
        return owner, repo
    return "", ""


def _fetch_protection(*, owner: str, repo: str, token: str) -> dict[str, Any] | None:
    url = f"https://api.github.com/repos/{owner}/{repo}/branches/main/protection"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        body = exc.read().decode("utf-8", errors="replace")
        print(f"GitHub API {exc.code}: {body}", file=sys.stderr)
        return None


def _required_contexts(protection: dict[str, Any]) -> set[str]:
    checks = protection.get("required_status_checks") or {}
    contexts = checks.get("contexts")
    if isinstance(contexts, list) and contexts:
        if isinstance(contexts[0], dict):
            return {str(c.get("context", c.get("name", ""))) for c in contexts}
        return {str(c) for c in contexts}
    return set()


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--token",
        default=os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN"),
        help="GitHub token with administration:read (Actions GITHUB_TOKEN on same repo).",
    )
    p.add_argument(
        "--warn-only",
        action="store_true",
        help="Print mismatches but exit 0 (for fork PRs without admin token).",
    )
    args = p.parse_args()

    root = _repo_root()
    spec = json.loads(
        (root / ".github" / "expected-branch-protection-main.json").read_text(encoding="utf-8")
    )
    expected = set(spec["required_status_checks"])
    forbidden = set(spec.get("not_required_status_checks") or [])

    if not args.token:
        print("No GITHUB_TOKEN; skipping remote branch protection audit.", file=sys.stderr)
        return 0

    owner, repo = _github_repo()
    if not owner:
        print("GITHUB_REPOSITORY not set; skipping remote audit.", file=sys.stderr)
        return 0

    protection = _fetch_protection(owner=owner, repo=repo, token=args.token)
    if protection is None:
        print("Branch protection not configured or token lacks access.", file=sys.stderr)
        return 0 if args.warn_only else 2

    remote = _required_contexts(protection)
    missing = expected - remote
    extra = remote - expected
    wrongly = forbidden & remote
    errors: list[str] = []
    if missing:
        errors.append(f"missing required checks: {sorted(missing)}")
    if extra:
        errors.append(f"unexpected required checks: {sorted(extra)}")
    if wrongly:
        errors.append(f"forbidden checks enabled: {sorted(wrongly)}")

    print("Remote required contexts:", ", ".join(sorted(remote)) or "(none)")
    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        return 0 if args.warn_only else 1
    print("Branch protection matches expected required checks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
