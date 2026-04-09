from __future__ import annotations

import json
from pathlib import Path


class FixturePolicyError(RuntimeError):
    pass


def validate_fixture_policy(reference_dir: str | Path) -> None:
    reference_dir = Path(reference_dir)

    manifest_path = reference_dir / "FIXTURE_MANIFEST.json"
    note_path = reference_dir / "REGENERATION_NOTE.md"
    config_path = reference_dir / "config.json"
    provenance_path = reference_dir / "RUN_PROVENANCE.json"

    if not manifest_path.exists():
        raise FixturePolicyError("Missing FIXTURE_MANIFEST.json")
    if not note_path.exists():
        raise FixturePolicyError("Missing REGENERATION_NOTE.md")
    if not config_path.exists():
        raise FixturePolicyError("Missing config.json")
    if not provenance_path.exists():
        raise FixturePolicyError("Missing RUN_PROVENANCE.json")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    config = json.loads(config_path.read_text(encoding="utf-8"))
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))

    if manifest.get("reference_arm_label") != "shielded-rules-plus-geometry":
        raise FixturePolicyError(
            "Fixture manifest must declare "
            "shielded-rules-plus-geometry as reference arm"
        )
    if manifest.get("reference_backend") != "cvxpy_moreau":
        raise FixturePolicyError(
            "Fixture manifest must declare cvxpy_moreau as reference backend"
        )

    arms = {arm["label"]: arm for arm in config.get("arms", [])}
    ref = arms.get("shielded-rules-plus-geometry")
    if ref is None:
        raise FixturePolicyError("config.json missing shielded-rules-plus-geometry arm")
    if ref.get("backend") != "cvxpy_moreau":
        raise FixturePolicyError(
            "Reference arm in config.json must use cvxpy_moreau backend"
        )
    if provenance.get("projector_mode") != "real_projector":
        raise FixturePolicyError(
            "RUN_PROVENANCE.json must declare projector_mode=real_projector"
        )
