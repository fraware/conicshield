import json
import shutil
from pathlib import Path

import pytest

from conicshield.parity.fixture_policy import (
    FixturePolicyError,
    validate_fixture_policy,
)


def test_fixture_policy_passes() -> None:
    validate_fixture_policy(Path("tests/fixtures/parity_reference"))


def _copy_fixture_skeleton(dest: Path) -> None:
    src = Path("tests/fixtures/parity_reference")
    dest.mkdir(parents=True, exist_ok=True)
    for name in (
        "FIXTURE_MANIFEST.json",
        "REGENERATION_NOTE.md",
        "config.json",
        "RUN_PROVENANCE.json",
    ):
        shutil.copy2(src / name, dest / name)


def test_fixture_policy_rejects_missing_manifest(tmp_path: Path) -> None:
    d = tmp_path / "fx"
    _copy_fixture_skeleton(d)
    (d / "FIXTURE_MANIFEST.json").unlink()
    with pytest.raises(FixturePolicyError, match="FIXTURE_MANIFEST"):
        validate_fixture_policy(d)


def test_fixture_policy_rejects_wrong_reference_backend_in_manifest(
    tmp_path: Path,
) -> None:
    d = tmp_path / "fx"
    _copy_fixture_skeleton(d)
    man = json.loads((d / "FIXTURE_MANIFEST.json").read_text(encoding="utf-8"))
    man["reference_backend"] = "native_moreau"
    (d / "FIXTURE_MANIFEST.json").write_text(json.dumps(man, indent=2), encoding="utf-8")
    with pytest.raises(FixturePolicyError, match="cvxpy_moreau"):
        validate_fixture_policy(d)


def test_fixture_policy_rejects_wrong_reference_backend_in_config(
    tmp_path: Path,
) -> None:
    d = tmp_path / "fx"
    _copy_fixture_skeleton(d)
    cfg = json.loads((d / "config.json").read_text(encoding="utf-8"))
    for arm in cfg["arms"]:
        if arm["label"] == "shielded-rules-plus-geometry":
            arm["backend"] = "native_moreau"
            break
    (d / "config.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    with pytest.raises(FixturePolicyError, match="config.json"):
        validate_fixture_policy(d)


def test_fixture_policy_rejects_passthrough_provenance(tmp_path: Path) -> None:
    d = tmp_path / "fx"
    _copy_fixture_skeleton(d)
    prov = json.loads((d / "RUN_PROVENANCE.json").read_text(encoding="utf-8"))
    prov["projector_mode"] = "passthrough"
    (d / "RUN_PROVENANCE.json").write_text(json.dumps(prov, indent=2), encoding="utf-8")
    with pytest.raises(FixturePolicyError, match="projector_mode=real_projector"):
        validate_fixture_policy(d)
