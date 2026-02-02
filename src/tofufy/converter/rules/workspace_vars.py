"""Rule: annotate terraform.workspace usage for cloud/TFE migrations.

When migrating from TFE's cloud{} block (which uses workspace prefixes),
`terraform.workspace` returns only the short name. In TACOS platforms this
still works, but the workspace naming convention may have changed.

This rule adds a one-time advisory comment near the first terraform.workspace
usage to flag that workspace names should be verified post-migration.
"""

from __future__ import annotations

import re
from pathlib import Path

from tofufy.converter.rules.base import Rule

_TF_WORKSPACE_RE = re.compile(r"\bterraform\.workspace\b")

_FIRST_USAGE_RE = re.compile(
    r"^([ \t]*.*?\bterraform\.workspace\b)",
    re.MULTILINE,
)

_COMMENT = (
    "# TOFUFY: terraform.workspace returns the full workspace name in OpenTofu.\n"
    "# If you used TFE workspace prefixes (e.g., 'prod' from 'myapp-prod'),\n"
    "# verify workspace names match after migration.\n"
)


class WorkspaceVarsRule(Rule):
    name = "workspace-name-annotation"

    def apply(self, content: str, path: Path) -> str:
        if "terraform.workspace" not in content:
            return content

        if "TOFUFY: terraform.workspace" in content:
            return content  # already annotated

        def _annotate_first(m: re.Match) -> str:  # type: ignore[type-arg]
            indent = re.match(r"^([ \t]*)", m.group(1))
            ind = indent.group(1) if indent else ""
            comment = "\n".join(ind + l for l in _COMMENT.splitlines()) + "\n"
            return comment + m.group(0)

        return _FIRST_USAGE_RE.sub(_annotate_first, content, count=1)
