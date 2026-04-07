from __future__ import annotations

import builtins
from typing import Any
from unittest import mock

import pytest

import conicshield._optional as optional


def test_require_module_success_imports_stdlib() -> None:
    m = optional.require_module("json", "unit test")
    assert m.loads('{"a": 1}') == {"a": 1}


def test_require_module_import_error_message() -> None:
    real_import = builtins.__import__

    def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "definitely_missing_conicshield_module_xyz":
            raise ImportError("No module named 'definitely_missing_conicshield_module_xyz'")
        return real_import(name, *args, **kwargs)

    with (
        mock.patch("builtins.__import__", side_effect=fake_import),
        pytest.raises(optional.OptionalDependencyError) as exc_info,
    ):
        optional.require_module(
            "definitely_missing_conicshield_module_xyz",
            "testing optional import errors",
        )
    msg = str(exc_info.value)
    assert "definitely_missing_conicshield_module_xyz" in msg
    assert "testing optional import errors" in msg
    assert "solver" in msg.lower() or ".[solver]" in msg


def test_optional_dependency_error_is_import_error() -> None:
    assert issubclass(optional.OptionalDependencyError, ImportError)
