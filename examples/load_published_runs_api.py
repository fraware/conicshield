#!/usr/bin/env python3
"""Canonical v1 walkthrough of ``conicshield.published_runs``.

Audience: researcher or tool author consuming published benchmark bundles.
Prerequisites: ``pip install -e .`` from repo root; no vendor Moreau required.
Proves: ``list_runs``, ``get_current_run``, ``load_run``, ``verify_run``, ``load_summary``,
  ``load_provenance`` on the family current bundle.
Does not prove: publish/refresh pipeline, parity replay, or performance superiority claims.
Expected: exit 0; all API steps print OK; flagship shows vendor_native + real_projector.
"""

from __future__ import annotations

from _common import FAMILY_ID, configure_stdio, repo_root, section

from conicshield.published_runs import (
    get_current_run,
    list_runs,
    load_provenance,
    load_run,
    load_summary,
    verify_run,
)


def main() -> int:
    configure_stdio()
    root = repo_root()

    section("list_runs")
    run_ids = [e.run_id for e in list_runs(repo_root=root)]
    for rid in run_ids:
        print(" ", rid)
    print(f"count: {len(run_ids)}")

    section("get_current_run")
    bundle = get_current_run(FAMILY_ID, repo_root=root)
    rid = bundle.run_id
    print("family:", FAMILY_ID)
    print("current_run_id:", rid)
    print("bundle path:", bundle.path.relative_to(root))

    section("load_run")
    loaded = load_run(rid, repo_root=root)
    print("index integrity files:", len(loaded.index_entry.integrity))
    print("has COMMUNITY_METADATA:", (loaded.path / "COMMUNITY_METADATA.json").is_file())

    section("verify_run")
    verify_run(rid, repo_root=root)
    print("integrity OK")

    section("load_summary (all arms)")
    rows = load_summary(rid, repo_root=root)
    for row in sorted(rows, key=lambda r: r.label):
        p95 = row.extra.get("solve_time_p95_ms")
        extra = f" p95_ms={p95}" if p95 is not None else ""
        print(f"  {row.label}: p50_ms={row.solve_time_p50_ms}{extra}")

    section("load_provenance")
    prov = load_provenance(rid, repo_root=root)
    print("evidence_tier:", prov.evidence_tier)
    print("projector_mode:", prov.projector_mode)
    print("host_realistic_evidence:", prov.host_realistic_evidence)
    if prov.export_source:
        print("export_source:", prov.export_source)

    if bundle.community:
        section("COMMUNITY_METADATA (scope)")
        print("export_kind:", bundle.community.export_kind)
        print("known_limitations[0]:", bundle.community.known_limitations[0])

    section("CLI equivalents")
    print("  python -m conicshield.published_runs.cli list")
    print(f"  python -m conicshield.published_runs.cli current {FAMILY_ID}")
    print(f"  python -m conicshield.published_runs.cli verify {rid}")
    print(f"  python -m conicshield.published_runs.cli summary {rid}")
    print(f"  python -m conicshield.published_runs.cli provenance {rid}")

    section("Done")
    print("Stability contract: docs/PUBLISHED_RUNS_API.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
