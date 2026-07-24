"""Generate and commit the versioned R0 research corpus."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, cast

import numpy as np

from conicshield.experimental.corpus.families import generate_family_scenarios
from conicshield.experimental.corpus.paths import (
    CORPUS_FAMILY_ID,
    CORPUS_ROOT,
    CORPUS_VERSION,
    MANIFEST_PATH,
    SCENARIO_FAMILIES,
    SCENARIOS_DIR,
    VERSION_PATH,
)


def _generation_commit_token() -> str:
    """Stable token derived from generator identity + corpus version (not git HEAD)."""

    payload = f"{CORPUS_VERSION}|{CORPUS_FAMILY_ID}|{','.join(SCENARIO_FAMILIES)}|families.py:v4"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def generate_corpus(*, root: Path | None = None) -> dict[str, Any]:
    """Generate all family scenarios and write JSON files + manifest."""

    corpus_root = root or CORPUS_ROOT
    scenarios_dir = corpus_root / "scenarios"
    scenarios_dir.mkdir(parents=True, exist_ok=True)
    # Clear prior scenario JSON files for deterministic regeneration
    for path in scenarios_dir.glob("*.json"):
        path.unlink()

    gen_commit = _generation_commit_token()
    rng = np.random.default_rng(0)
    all_scenarios: list[dict[str, Any]] = []
    for family in SCENARIO_FAMILIES:
        all_scenarios.extend(generate_family_scenarios(family=family, generation_commit=gen_commit, rng=rng))

    by_family: dict[str, list[str]] = {f: [] for f in SCENARIO_FAMILIES}
    for scenario in all_scenarios:
        sid = str(scenario["scenario_id"])
        safe_name = sid.replace("/", "__") + ".json"
        path = scenarios_dir / safe_name
        path.write_text(json.dumps(scenario, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        by_family[str(scenario["family"])].append(sid)

    manifest: dict[str, Any] = {
        "corpus_version": CORPUS_VERSION,
        "corpus_family_id": CORPUS_FAMILY_ID,
        "generation_commit": gen_commit,
        "scenario_count": len(all_scenarios),
        "families": {k: sorted(v) for k, v in by_family.items()},
        "schema": "research/solver-assurance-and-gradients/schemas/scenario.schema.json",
        "notes": (
            "Versioned R0 research corpus. Seeds and generation code reproduce every case. "
            "Includes failure and disagreement regimes."
        ),
    }
    (corpus_root / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (corpus_root / "VERSION").write_text(CORPUS_VERSION + "\n", encoding="utf-8")
    return manifest


def load_manifest(*, root: Path | None = None) -> dict[str, Any]:
    path = (root / "manifest.json") if root is not None else MANIFEST_PATH
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise TypeError(f"manifest must be an object: {path}")
    return cast(dict[str, Any], raw)


def load_all_scenarios(*, root: Path | None = None) -> list[dict[str, Any]]:
    scenarios_dir = (root / "scenarios") if root is not None else SCENARIOS_DIR
    scenarios: list[dict[str, Any]] = []
    for path in sorted(scenarios_dir.glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise TypeError(f"scenario must be an object: {path}")
        scenarios.append(cast(dict[str, Any], raw))
    return scenarios


def main() -> None:
    manifest = generate_corpus()
    print(f"Wrote corpus {manifest['corpus_version']} with {manifest['scenario_count']} scenarios")
    print(f"generation_commit={manifest['generation_commit']}")
    print(f"manifest={MANIFEST_PATH}")
    print(f"version={VERSION_PATH}")


if __name__ == "__main__":
    main()
