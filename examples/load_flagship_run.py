#!/usr/bin/env python3
"""Minimal flagship consumer sample: verify, metadata, one episode row.

Audience: researcher who wants the shortest working API snippet.
Prerequisites: ``pip install -e .`` from repo root.
Proves: ``verify_run``, ``get_current_run``, ``load_summary``, ``load_provenance``, ``load_episodes``.
Does not prove: full index tour (see ``load_published_runs_api.py``) or governance internals.
Expected: integrity OK; 4 arms; episode count matches summary; one episode dict printed.
"""

from __future__ import annotations

from _common import FAMILY_ID, FLAGSHIP_RUN_ID, configure_stdio, repo_root, section

from conicshield.published_runs import (
    get_current_run,
    load_episodes,
    load_provenance,
    load_summary,
    verify_run,
)


def main() -> int:
    configure_stdio()
    root = repo_root()

    section("verify_run")
    verify_run(FLAGSHIP_RUN_ID, repo_root=root)
    print("integrity OK")

    section("get_current_run")
    bundle = get_current_run(FAMILY_ID, repo_root=root)
    if bundle.run_id != FLAGSHIP_RUN_ID:
        print(f"unexpected current_run_id: {bundle.run_id}")
        return 1
    print("current_run_id:", bundle.run_id)

    prov = load_provenance(FLAGSHIP_RUN_ID, repo_root=root)
    print("tier:", bundle.community.evidence_tier if bundle.community else "n/a")
    print("projector_mode:", prov.projector_mode)

    if bundle.community and bundle.community.known_limitations:
        print("limitation:", bundle.community.known_limitations[0])

    section("load_summary")
    rows = load_summary(FLAGSHIP_RUN_ID, repo_root=root)
    print("arms:", ", ".join(r.label for r in rows))

    section("load_episodes")
    episodes = load_episodes(FLAGSHIP_RUN_ID, repo_root=root)
    print("episode count:", len(episodes))
    if not episodes:
        print("no episodes in episodes.jsonl")
        return 1
    first = episodes[0]
    print("first episode keys:", ", ".join(sorted(first.keys())))
    if "episode_id" in first:
        print("first episode_id:", first["episode_id"])

    section("Done")
    print("Full API tour: python examples/load_published_runs_api.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
