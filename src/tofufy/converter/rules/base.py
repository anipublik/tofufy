"""Base rule interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class Rule(ABC):
    """A single deterministic transformation rule."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def apply(self, content: str, path: Path) -> str:
        """Return transformed content. Return original if rule doesn't apply."""
        ...
