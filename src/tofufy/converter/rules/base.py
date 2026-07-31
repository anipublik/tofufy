"""Base rule interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class Rule(ABC):
    """A single deterministic transformation rule."""

    # HCL-syntax rules assume braces/equals and must not run on .tf.json files.
    # JSON-aware rules opt in by setting this to True.
    supports_json: bool = False

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def apply(self, content: str, path: Path) -> str:
        """Return transformed content. Return original if rule doesn't apply."""
        ...
