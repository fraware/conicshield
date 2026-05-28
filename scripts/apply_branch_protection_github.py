#!/usr/bin/env python3
"""Apply ``main`` branch protection from expected-branch-protection-main.json via GitHub API."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _parse_remote_owner_repo() -> tuple[str, str]:
    env = os.environ.get("GITHUB_REPOSITORY", "")
    if "/" in env:
        owner, repo = env.split("/", 1)
        return owner, repo
    try:
        url = subprocess.check_output(
            ["git", "remote", "get-url", "origin"],
            cwd=_repo_root(),
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "", ""
    m = re.search(r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/.]+)", url)
    if not m:
        return "", ""
    return m.group("owner"), m.group("repo")


def _put_protection(
    *,
    owner: str,
    repo: str,
    token: str,
    contexts: list[str],
    dry_run: bool,
) -> int:
    url = f"https://api.github.com/repos/{owner}/{repo}/branches/main/protection"
    body: dict[str, Any] = {
        "required_status_checks": {"strict": True, "contexts": contexts},
        "enforce_admins": True,
        "required_pull_request_reviews": {"required_approving_review_count": 1},
        "restrictions": None,
    }
    if dry_run:
        print("DRY RUN - would PUT", url)
        print(json.dumps(body, indent=2))
        print("\nAfter apply: make verify-branch-protection-expectations")
        print("Record evidence: docs/BRANCH_PROTECTION_RECORD.md")
        return 0
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="PUT",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            print("OK:", resp.status, url)
            return 0
    except urllib.error.HTTPError as exc:
        print(f"GitHub API {exc.code}: {exc.read().decode('utf-8', errors='replace')}", file=sys.stderr)
        return 1


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--apply",
        action="store_true",
        help="Perform PUT (default is dry-run preview).",
    )
    p.add_argument(
        "--token",
        default=os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN"),
        help="Admin-capable token (repo admin or fine-grained administration write).",
    )
    args = p.parse_args()
    root = _repo_root()
    spec = json.loads(
        (root / ".github" / "expected-branch-protection-main.json").read_text(encoding="utf-8")
    )
    contexts = list(spec["required_status_checks"])
    owner, repo = _parse_remote_owner_repo()
    if not owner:
        print("Could not resolve owner/repo; set GITHUB_REPOSITORY or fix origin remote.", file=sys.stderr)
        return 2
    if not args.apply:
        return _put_protection(owner=owner, repo=repo, token="", contexts=contexts, dry_run=True)
    if not args.token:
        print("Set GITHUB_TOKEN or GH_TOKEN with admin access, or run: gh auth login", file=sys.stderr)
        print("Alternative: python scripts/print_branch_protection_gh_recipe.py", file=sys.stderr)
        return 2
    return _put_protection(
        owner=owner,
        repo=repo,
        token=args.token,
        contexts=contexts,
        dry_run=False,
    )


if __name__ == "__main__":
    raise SystemExit(main())
