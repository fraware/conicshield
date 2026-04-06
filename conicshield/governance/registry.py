from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_registry(path: str | Path = "benchmarks/registry.json") -> dict[str, Any]:
    return _load_json(Path(path))


def save_registry(payload: dict[str, Any], path: str | Path = "benchmarks/registry.json") -> None:
    _write_json(Path(path), payload)


def load_current(family_id: str) -> dict[str, Any]:
    return _load_json(Path("benchmarks") / "releases" / family_id / "CURRENT.json")


def save_current(family_id: str, payload: dict[str, Any]) -> None:
    _write_json(Path("benchmarks") / "releases" / family_id / "CURRENT.json", payload)


def load_history(family_id: str) -> dict[str, Any]:
    return _load_json(Path("benchmarks") / "releases" / family_id / "HISTORY.json")


def save_history(family_id: str, payload: dict[str, Any]) -> None:
    _write_json(Path("benchmarks") / "releases" / family_id / "HISTORY.json", payload)


def append_history_entry(family_id: str, entry: dict[str, Any]) -> None:
    history = load_history(family_id)
    history.setdefault("entries", []).append(entry)
    save_history(family_id, history)
