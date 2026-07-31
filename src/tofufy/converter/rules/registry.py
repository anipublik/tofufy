"""Rule: rewrite registry.terraform.io provider sources to registry.opentofu.org."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from tofufy.converter.rules.base import Rule

if TYPE_CHECKING:
    from pathlib import Path

_REGISTRY_RE = re.compile(r"registry\.terraform\.io", re.IGNORECASE)


class RegistryRewriteRule(Rule):
    name = "registry-rewrite"
    # Pure string substitution - safe on JSON-syntax config too.
    supports_json = True

    def apply(self, content: str, path: Path) -> str:
        return _REGISTRY_RE.sub("registry.opentofu.org", content)
