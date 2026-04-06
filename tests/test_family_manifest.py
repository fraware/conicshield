from conicshield.governance.family_manifest import validate_family_manifest


def test_family_manifest_validates() -> None:
    manifest = validate_family_manifest("conicshield-transition-bank-v1")
    assert manifest["reference_arm"] == "shielded-rules-plus-geometry"
    assert manifest["native_parity_required"] is True
