"""Rule: clean up `removed` block syntax changes between Terraform 1.8 and OpenTofu.

In Terraform 1.8.x, `removed` blocks used:
  lifecycle { destroy = true/false }

OpenTofu and Terraform 1.9+ use:
  destroy = true/false  (directly in removed block, no lifecycle wrapper)

This rule hoists the `destroy` attribute out of the `lifecycle {}` wrapper
inside `removed {}` blocks.
"""

from __future__ import annotations

import re
from pathlib import Path

from tofufy.converter.rules.base import Rule

# Find: removed { ... lifecycle { destroy = <bool> } ... }
_REMOVED_LIFECYCLE_RE = re.compile(
    r"""
    ^([ \t]*)removed\s*\{          # removed { (group 1 = indent)
    (.*?)                           # prefix body (group 2)
    ([ \t]*)lifecycle\s*\{         # lifecycle { (group 3 = lifecycle indent)
    [ \t]*\n                        # rest of line
    ([ \t]*)destroy\s*=\s*(\w+)    # destroy = bool (group 4=indent, group 5=value)
    [ \t]*\n                        # rest of line
    [ \t]*\}                        # closing lifecycle }
    (.*?)                           # suffix body (group 6)
    ^([ \t]*)\}                     # closing removed } (group 7)
    """,
    re.MULTILINE | re.VERBOSE | re.DOTALL,
)


def _hoist_destroy(m: re.Match) -> str:  # type: ignore[type-arg]
    block_indent = m.group(1)
    prefix = m.group(2)
    lifecycle_indent = m.group(3)
    destroy_indent = m.group(4)
    destroy_value = m.group(5)
    suffix = m.group(6)
    close_indent = m.group(7)

    # Rebuild without lifecycle wrapper
    return (
        f"{block_indent}removed {{"
        f"{prefix}"
        f"{lifecycle_indent}destroy = {destroy_value}\n"
        f"{suffix}"
        f"{close_indent}}}"
    )


class RemovedBlockRule(Rule):
    name = "removed-block-lifecycle"

    def apply(self, content: str, path: Path) -> str:
        if "removed" not in content or "lifecycle" not in content:
            return content

        return _REMOVED_LIFECYCLE_RE.sub(_hoist_destroy, content)
