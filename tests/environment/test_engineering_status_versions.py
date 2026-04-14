from __future__ import annotations

import os
import re

from tests._repo import repo_root


def test_engineering_status_moreau_row_not_placeholder_when_required() -> None:
    if os.environ.get("REQUIRE_REAL_SOLVER_VERSIONS", "").strip() != "1":
        return
    text = (repo_root() / "docs" / "ENGINEERING_STATUS.md").read_text(encoding="utf-8")
    # Require a concrete version string in the moreau row once the vendor lane enforces it.
    assert "vendor wheel (not in `requirements-dev.txt`)" not in text
    moreau_row = re.search(r"\|\s*`moreau`\s*\|\s*([^|]+)\|", text)
    assert moreau_row is not None
    version_cell = moreau_row.group(1).strip()
    assert version_cell and version_cell != "—"
