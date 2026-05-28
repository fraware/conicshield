from __future__ import annotations

import json
import importlib.util
from pathlib import Path


def _load_record_module():
    root = Path(__file__).resolve().parents[2]
    path = root / "scripts" / "record_reference_refresh.py"
    spec = importlib.util.spec_from_file_location("record_reference_refresh", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_record_entry_amend_last_preserves_index(tmp_path: Path) -> None:
    mod = _load_record_module()
    prov = tmp_path / "EXPORT_PROVENANCE.json"
    log = tmp_path / "REFERENCE_AUTHORITY_LOG.md"
    prov.write_text(
        json.dumps(
            {
                "refresh_history": [
                    {
                        "refresh_index": 4,
                        "completed_at_utc": "2026-01-01T00:00:00Z",
                        "trigger": "old",
                        "workflow": "live-export",
                        "export_kind": "live_upstream_dump",
                        "git_ref": "abc",
                        "authority_ok": False,
                        "notes": "partial",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    log.write_text("| 4 | old row |\n\n<!-- Append rows via: -->\n", encoding="utf-8")

    idx = mod._record_entry(
        prov_path=prov,
        log_path=log,
        trigger="calendar-cadence",
        workflow="live-export-full",
        export_kind="live_upstream_dump",
        git_ref="def",
        authority_ok=True,
        notes="full cycle",
        amend_last=True,
    )
    assert idx == 4
    data = json.loads(prov.read_text(encoding="utf-8"))
    assert len(data["refresh_history"]) == 1
    assert data["refresh_history"][0]["authority_ok"] is True
    assert "live-export-full" in log.read_text(encoding="utf-8")
