"""Parse .tofufyignore files (gitignore-style)."""

from __future__ import annotations

from pathlib import Path


def load_ignore_patterns(path: Path) -> list[str]:
    """Return a list of glob patterns from a .tofufyignore file."""
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return [l.strip() for l in lines if l.strip() and not l.strip().startswith("#")]
