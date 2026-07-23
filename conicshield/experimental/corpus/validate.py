"""Validate R0 corpus integrity against schema and generator reproduction."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator

from conicshield.experimental.corpus.generate import generate_corpus, load_all_scenarios, load_manifest
from conicshield.experimental.corpus.paths import (
    CORPUS_ROOT,
    CORPUS_VERSION,
    SCENARIO_FAMILIES,
    SCENARIO_SCHEMA_PATH,
)

REQUIRED_SCENARIO_KEYS = (
    "scenario_id",
    "family",
    "seed",
    "spec",
    "proposed_action",
    "previous_action",
    "reference_action",
    "weights",
    "expected_regime",
    "generation_commit",
    "notes",
)


def load_scenario_schema(*, schema_path: Path | None = None) -> dict[str, Any]:
    path = schema_path or SCENARIO_SCHEMA_PATH
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise TypeError(f"scenario schema must be an object: {path}")
    return cast(dict[str, Any], raw)


def validate_scenario_dict(scenario: dict[str, Any], *, schema: dict[str, Any] | None = None) -> list[str]:
    errors: list[str] = []
    for key in REQUIRED_SCENARIO_KEYS:
        if key not in scenario:
            errors.append(f"missing key: {key}")
    sch = schema or load_scenario_schema()
    validator = Draft202012Validator(sch)
    for err in sorted(validator.iter_errors(scenario), key=lambda e: list(e.path)):
        errors.append(f"{list(err.path)}: {err.message}")
    return errors


def validate_corpus(*, root: Path | None = None, regenerate_check: bool = True) -> list[str]:
    """Return a list of integrity errors (empty means OK)."""

    corpus_root = root or CORPUS_ROOT
    errors: list[str] = []
    version_path = corpus_root / "VERSION"
    if not version_path.is_file():
        return [f"missing VERSION at {version_path}"]
    version = version_path.read_text(encoding="utf-8").strip()
    if version != CORPUS_VERSION:
        errors.append(f"VERSION mismatch: file={version!r} expected={CORPUS_VERSION!r}")

    try:
        manifest = load_manifest(root=corpus_root)
    except FileNotFoundError:
        return [f"missing manifest at {corpus_root / 'manifest.json'}"]

    if manifest.get("corpus_version") != CORPUS_VERSION:
        errors.append("manifest corpus_version mismatch")

    scenarios = load_all_scenarios(root=corpus_root)
    if not scenarios:
        errors.append("no scenario JSON files found")

    schema = load_scenario_schema()
    seen_ids: set[str] = set()
    families_seen: set[str] = set()
    for scenario in scenarios:
        sid = str(scenario.get("scenario_id", ""))
        if sid in seen_ids:
            errors.append(f"duplicate scenario_id: {sid}")
        seen_ids.add(sid)
        families_seen.add(str(scenario.get("family", "")))
        for err in validate_scenario_dict(scenario, schema=schema):
            errors.append(f"{sid}: {err}")

    missing_families = set(SCENARIO_FAMILIES) - families_seen
    if missing_families:
        errors.append(f"missing families: {sorted(missing_families)}")

    manifest_ids = {sid for ids in manifest.get("families", {}).values() for sid in ids}
    if manifest_ids != seen_ids:
        errors.append("manifest scenario ids do not match on-disk scenarios")

    if regenerate_check:
        # Reproduce into a temp sibling directory conceptually by regenerating in-memory compare
        # Actual write: regenerate and compare generation_commit + scenario set
        before = {(s["scenario_id"], json.dumps(s, sort_keys=True)) for s in scenarios}
        generate_corpus(root=corpus_root)
        after_scenarios = load_all_scenarios(root=corpus_root)
        after = {(s["scenario_id"], json.dumps(s, sort_keys=True)) for s in after_scenarios}
        if before != after:
            errors.append("corpus regeneration is not bit-stable relative to committed scenarios")

    return errors


def main() -> None:
    errs = validate_corpus()
    if errs:
        print("CORPUS INTEGRITY FAILURES:")
        for e in errs:
            print(f"  - {e}")
        raise SystemExit(1)
    print(f"Corpus {CORPUS_VERSION} OK ({len(load_all_scenarios())} scenarios)")


if __name__ == "__main__":
    main()
