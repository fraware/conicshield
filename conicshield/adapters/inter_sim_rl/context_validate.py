from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator


@lru_cache(maxsize=1)
def _shield_context_schema() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[3]
    path = root / "schemas" / "shield_context.schema.json"
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def validate_shield_context_dict(context: dict[str, Any]) -> None:
    """Raise jsonschema.ValidationError if context does not satisfy the published contract."""
    schema = _shield_context_schema()
    Draft202012Validator(schema).validate(context)
