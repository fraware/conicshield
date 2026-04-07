from __future__ import annotations

import json
from pathlib import Path

from conicshield.bench.bank_payloads import transition_bank_payload
from conicshield.bench.transition_bank import TransitionBank


def test_transition_bank_payload_matches_fixture_shape() -> None:
    path = Path("tests/fixtures/parity_reference/transition_bank.json")
    raw = json.loads(path.read_text(encoding="utf-8"))
    bank = TransitionBank.from_json(path)
    payload = transition_bank_payload(bank, bank_id="custom_id")

    assert payload["bank_id"] == "custom_id"
    assert payload["root_address"] == raw["root_address"]
    assert set(payload["nodes"]) == set(raw["nodes"])

    root = bank.nodes[bank.root_address]
    root_payload = payload["nodes"][bank.root_address]
    assert root_payload["allowed_actions"] == root.allowed_actions()
    assert len(root_payload["candidates"]) == 1
    c0 = root_payload["candidates"][0]
    raw_c0 = raw["nodes"]["Root"]["candidates"][0]
    assert c0["destination_address"] == raw_c0["destination_address"]
    assert c0["action_class"] == raw_c0["action_class"]
    assert c0["duration_sec"] == raw_c0["duration_sec"]
    assert c0["distance_m"] == raw_c0["distance_m"]
