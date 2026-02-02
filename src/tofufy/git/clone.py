"""Resolve a source (local path or git URL) to a local directory."""

from __future__ import annotations

import re
import tempfile
from pathlib import Path

_GIT_URL_RE = re.compile(r"^(https?://|git@|ssh://)", re.IGNORECASE)


def resolve_source(source: str, verbose: bool = False) -> Path:
    """If source looks like a git URL, clone it to a temp dir and return the path."""
    if _GIT_URL_RE.match(source):
        return _clone(source, verbose=verbose)
    path = Path(source).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Path does not exist: {path}")
    return path


def _clone(url: str, verbose: bool = False) -> Path:
    import git  # type: ignore[import-untyped]

    tmp = tempfile.mkdtemp(prefix="tofufy-")
    dest = Path(tmp) / "repo"
    git.Repo.clone_from(url, dest, depth=1, progress=None if not verbose else _GitProgress())
    return dest


class _GitProgress:
    def __call__(self, op_code: int, cur_count: int, max_count: int = 0, message: str = "") -> None:
        print(f"  git: {message or cur_count}/{max_count}")
