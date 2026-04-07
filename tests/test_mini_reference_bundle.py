from __future__ import annotations

import hashlib
import json
from pathlib import Path

import jsonschema

from conicshield.bench.transition_bank import TransitionBank


def test_mini_reference_bundle_hashes_and_schema() -> None:
    root = Path("tests/fixtures/mini_reference_bundle")
    sums = (root / "SHA256SUMS").read_text(encoding="utf-8").strip().splitlines()
    expected = {}
    for line in sums:
        parts = line.split()
        assert len(parts) == 2
        expected[parts[1]] = parts[0]
    for name, hex_digest in expected.items():
        data = (root / name).read_bytes()
        assert hashlib.sha256(data).hexdigest() == hex_digest

    bank = TransitionBank.from_json(root / "transition_bank.json")
    assert bank.root_address == "Root"
    assert "A" in bank.nodes

    schema = json.loads(Path("schemas/episodes.schema.json").read_text(encoding="utf-8"))
    episode_record_schema: dict = {"$ref": "#/$defs/episodeRecord", "$defs": schema["$defs"]}
    v = jsonschema.Draft202012Validator(episode_record_schema)
    line = (root / "episodes.jsonl").read_text(encoding="utf-8").splitlines()[0]
    v.validate(json.loads(line))
