"""Rule: rewrite registry.terraform.io provider sources to registry.opentofu.org."""

from __future__ import annotations

import re
from pathlib import Path

from tofufy.converter.rules.base import Rule

_REGISTRY_RE = re.compile(r"registry\.terraform\.io", re.IGNORECASE)


class RegistryRewriteRule(Rule):
    name = "registry-rewrite"

    def apply(self, content: str, path: Path) -> str:
        return _REGISTRY_RE.sub("registry.opentofu.org", content)
