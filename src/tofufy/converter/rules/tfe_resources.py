"""Rule: annotate TFE provider resources that need manual review.

TFE provider resources (tfe_workspace, tfe_variable, tfe_organization, etc.)
continue to work with OpenTofu via the hashicorp/tfe provider, but they
reference Terraform Enterprise/Cloud APIs. After migrating to a TACOS platform
these resources may need to be replaced with platform-native equivalents.

This rule adds a TOFUFY comment above each tfe_* resource/data block to flag
it for manual review without modifying the resource itself.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from tofufy.converter.rules.base import Rule

if TYPE_CHECKING:
    from pathlib import Path

_TFE_RESOURCE_RE = re.compile(
    r"""
    ^([ \t]*)                       # indent (group 1)
    (resource|data)\s+              # resource or data
    "(tfe_[^"]+)"                   # tfe_* type (group 3)
    \s+"\w+"                        # resource name
    \s*\{                           # opening brace
    """,
    re.MULTILINE | re.VERBOSE,
)

_ANNOTATION = (
    "# TOFUFY: This {kind} uses the TFE provider (Terraform Enterprise/Cloud API).\n"
    "# After migrating to your TACOS platform, verify whether this should be replaced\n"
    "# with a platform-native equivalent (e.g., Spacelift stack, Scalr workspace).\n"
)


def _annotate(m: re.Match[str]) -> str:
    indent = m.group(1)
    kind = m.group(2)
    annotation = _ANNOTATION.format(kind=kind)
    # Indent each annotation line
    indented = "\n".join(indent + line for line in annotation.splitlines()) + "\n"
    # Check if annotation is already present (idempotency)
    return indented + m.group(0)


class TFEResourcesRule(Rule):
    name = "tfe-resource-annotation"

    def apply(self, content: str, path: Path) -> str:
        if '"tfe_' not in content:
            return content

        # Don't double-annotate
        if "TOFUFY: This" in content:
            return content

        return _TFE_RESOURCE_RE.sub(_annotate, content)
