from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator


class FamilyManifestError(RuntimeError):
    pass


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def family_release_dir(family_id: str) -> Path:
    return Path("benchmarks") / "releases" / family_id


def family_manifest_path(family_id: str) -> Path:
    return family_release_dir(family_id) / "FAMILY_MANIFEST.json"


def family_manifest_schema_path(family_id: str) -> Path:
    return family_release_dir(family_id) / "FAMILY_MANIFEST.schema.json"


def load_family_manifest(family_id: str) -> dict[str, Any]:
    path = family_manifest_path(family_id)
    if not path.exists():
        raise FamilyManifestError(f"Missing family manifest: {path}")
    return cast(dict[str, Any], _load_json(path))


def load_family_manifest_schema(family_id: str) -> dict[str, Any]:
    path = family_manifest_schema_path(family_id)
    if not path.exists():
        raise FamilyManifestError(f"Missing family manifest schema: {path}")
    return cast(dict[str, Any], _load_json(path))


def validate_family_manifest(family_id: str) -> dict[str, Any]:
    manifest = load_family_manifest(family_id)
    schema = load_family_manifest_schema(family_id)

    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(manifest), key=lambda e: list(e.path))
    if errors:
        rendered: list[str] = []
        for err in errors[:20]:
            path = ".".join(str(x) for x in err.absolute_path) or "<root>"
            rendered.append(f"{path}: {err.message}")
        raise FamilyManifestError("Invalid family manifest:\n" + "\n".join(rendered))

    if manifest["reference_arm"] not in manifest["required_arms"]:
        raise FamilyManifestError("reference_arm must be included in required_arms")

    if manifest["fixture_lineage"]["reference_arm_label"] != manifest["reference_arm"]:
        raise FamilyManifestError("fixture_lineage.reference_arm_label must match reference_arm")

    return manifest
