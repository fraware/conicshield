from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_gitignore_blocks_secrets_and_caches() -> None:
    text = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    required = (
        ".env",
        ".pytest_cache/",
        "__pycache__/",
        ".mypy_cache/",
        ".ruff_cache/",
        "*.egg-info/",
        "dist/",
        ".coverage",
        "htmlcov/",
    )
    for line in required:
        assert line in text, f".gitignore must mention {line!r}"


def test_no_tracked_forbidden_paths() -> None:
    """If .git/index exists, ensure obvious generated/secret paths are not tracked."""
    git_dir = REPO_ROOT / ".git"
    if not git_dir.exists():
        return
    try:
        import subprocess

        out = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
        ).stdout.decode()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return
    tracked = [p for p in out.split("\0") if p]
    forbidden_substrings = (
        ".pytest_cache",
        "__pycache__",
        ".egg-info",
        "/dist/",
        "htmlcov/",
        ".coverage",
    )
    bad: list[str] = []
    for p in tracked:
        norm = p.replace("\\", "/")
        if any(s in norm for s in forbidden_substrings) or Path(p).name == ".env":
            bad.append(p)
    assert not bad, f"Unexpected tracked paths: {bad}"
