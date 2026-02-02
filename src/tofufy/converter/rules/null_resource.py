"""Rule: migrate null_resource to terraform_data (OpenTofu 1.6+).

Changes:
  - resource "null_resource" -> resource "terraform_data"
  - triggers = { ... }      -> triggers_replace = { ... }
  - self.triggers.*         -> self.triggers_replace.*
  - provider = null         -> (removed)
  - hashicorp/null removed from required_providers
"""

from __future__ import annotations

import re
from pathlib import Path

from tofufy.converter.rules.base import Rule

# Match the resource type declaration
_RESOURCE_TYPE_RE = re.compile(r'\bresource\s+"null_resource"')

# Match triggers = inside a resource block (indented, safe to replace globally
# since only null_resource uses this attribute name)
_TRIGGERS_RE = re.compile(r"^(\s+)triggers(\s*=)", re.MULTILINE)

# self.triggers.X -> self.triggers_replace.X
_SELF_TRIGGERS_RE = re.compile(r"\bself\.triggers\b(?!_replace)")

# Remove `provider = null` lines
_PROVIDER_NULL_RE = re.compile(r"^\s*provider\s*=\s*null\s*\n", re.MULTILINE)

# Remove the null provider from required_providers
_NULL_PROVIDER_BLOCK_RE = re.compile(
    r"""
    \bnull\s*=\s*\{       # null = {
        [^}]*              # contents
    \}\s*\n?              # closing }
    """,
    re.VERBOSE,
)


class NullResourceRule(Rule):
    name = "null-resource-to-terraform-data"

    def apply(self, content: str, path: Path) -> str:
        if "null_resource" not in content:
            return content

        content = _RESOURCE_TYPE_RE.sub('resource "terraform_data"', content)

        # Only rename triggers inside blocks that were null_resource.
        # Since only null_resource uses `triggers =`, a global rename is safe.
        content = _TRIGGERS_RE.sub(r"\1triggers_replace\2", content)

        content = _SELF_TRIGGERS_RE.sub("self.triggers_replace", content)
        content = _PROVIDER_NULL_RE.sub("", content)

        # Remove null provider from required_providers if it's now unused
        if "null_resource" not in content:
            content = _NULL_PROVIDER_BLOCK_RE.sub("", content)

        return content
