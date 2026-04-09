import json
from pathlib import Path

from conicshield.governance.family_manifest import validate_family_manifest


def test_family_manifest_validates() -> None:
    manifest = validate_family_manifest("conicshield-transition-bank-v1")
    assert manifest["reference_arm"] == "shielded-rules-plus-geometry"
    assert manifest["native_parity_required"] is True


def test_registry_entry_matches_validated_family_manifest() -> None:
    reg = json.loads(Path("benchmarks/registry.json").read_text(encoding="utf-8"))
    for entry in reg["benchmark_families"]:
        family_id = str(entry["family_id"])
        manifest = validate_family_manifest(family_id)
        assert manifest["family_id"] == family_id
