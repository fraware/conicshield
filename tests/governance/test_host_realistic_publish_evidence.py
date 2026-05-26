from __future__ import annotations

import json
from pathlib import Path

_HOST_REALISTIC_RUN_ID = "host-realistic-20260525"
_MINIMAL_FIXTURE = "tests/fixtures/offline_graph_export_minimal.json"


def test_host_realistic_published_run_provenance_not_minimal_fixture() -> None:
    root = Path(__file__).resolve().parents[2]
    prov_path = root / "benchmarks" / "published_runs" / _HOST_REALISTIC_RUN_ID / "RUN_PROVENANCE.json"
    assert prov_path.is_file(), f"missing {prov_path}"
    payload = json.loads(prov_path.read_text(encoding="utf-8"))
    source = str(payload.get("source_export_json", "")).replace("\\", "/")
    assert _MINIMAL_FIXTURE not in source
    assert payload.get("host_realistic_evidence") is True
    assert payload.get("minimal_fixture_export") is False
    assert payload.get("evidence_tier") == "structural_export"
    assert payload.get("projector_mode") == "passthrough"
    assert (root / "benchmarks" / "published_runs" / _HOST_REALISTIC_RUN_ID / "governance_status.json").is_file()
