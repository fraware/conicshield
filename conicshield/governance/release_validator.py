from __future__ import annotations

from pathlib import Path

from conicshield.governance.family_manifest import validate_family_manifest


class ReleaseDirectoryError(RuntimeError):
    pass


def validate_release_directory(family_id: str) -> None:
    release_dir = Path("benchmarks") / "releases" / family_id
    required = [
        release_dir / "CURRENT.json",
        release_dir / "HISTORY.json",
        release_dir / "FAMILY_MANIFEST.json",
        release_dir / "FAMILY_MANIFEST.schema.json",
    ]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        raise ReleaseDirectoryError(f"Missing required release-directory files: {missing}")
    validate_family_manifest(family_id)
