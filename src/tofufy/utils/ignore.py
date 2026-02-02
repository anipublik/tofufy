"""Parse .tofufyignore files (gitignore-style)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def load_ignore_patterns(path: Path) -> list[str]:
    """Return a list of glob patterns from a .tofufyignore file."""
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]
