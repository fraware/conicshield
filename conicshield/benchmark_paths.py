"""Where benchmark run bundles live on disk.

Published, auditable bundles should be committed under ``benchmarks/published_runs/<run_id>/``.
Ephemeral local rehearsal bundles use ``benchmarks/runs/<run_id>/`` (gitignored by default).
"""

from __future__ import annotations

from pathlib import Path


def resolve_run_directory(run_id: str) -> Path:
    """Return the directory for ``run_id``, preferring a committed published bundle.

    Resolution order:

    1. ``benchmarks/published_runs/<run_id>/`` if it exists (canonical, auditable).
    2. ``benchmarks/runs/<run_id>/`` (local / CI rehearsal).
    """
    rid = str(run_id).strip()
    published = Path("benchmarks") / "published_runs" / rid
    if published.is_dir():
        return published
    return Path("benchmarks") / "runs" / rid
