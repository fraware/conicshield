import json
from pathlib import Path

from conicshield.governance.family_bump import initialize_new_family, next_family_version


def test_next_family_version() -> None:
    assert next_family_version("conicshield-transition-bank-v1") == "conicshield-transition-bank-v2"


def test_initialize_new_family(tmp_path) -> None:
    bench = tmp_path / "benchmarks"
    (bench / "releases" / "fam-v1").mkdir(parents=True)
    (bench / "releases" / "fam-v1" / "FAMILY_MANIFEST.schema.json").write_text("{}", encoding="utf-8")
    (bench / "registry.json").write_text(json.dumps({"benchmark_families":[]}), encoding="utf-8")

    import os
    cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        initialize_new_family(
            current_family_id="fam-v1",
            new_family_id="fam-v2",
            task_contract_version="v2",
            fixture_version="fixture-v2",
        )
        assert (bench / "releases" / "fam-v2" / "CURRENT.json").exists()
    finally:
        os.chdir(cwd)
