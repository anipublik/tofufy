"""Rule: remove cloud{} block and rewrite to backend "remote" {}.

The old regex approach breaks on any terraform{} block that contains
required_providers{} or other nested blocks before cloud{}, because [^}]*?
cannot cross closing braces. This version uses a brace-counting walk instead.
"""

from __future__ import annotations

import re
from pathlib import Path

from tofufy.converter.rules.base import Rule

_CLOUD_KEYWORD_RE = re.compile(r"(^[ \t]*)cloud\s*\{", re.MULTILINE)

_HOSTNAME_RE = re.compile(r'\bhostname\s*=\s*"([^"]+)"')
_ORG_RE = re.compile(r'\borganization\s*=\s*"([^"]+)"')
_WS_NAME_RE = re.compile(r'\bname\s*=\s*"([^"]+)"')
_WS_PREFIX_RE = re.compile(r'\bprefix\s*=\s*"([^"]+)"')


def _find_block_end(content: str, open_brace_pos: int) -> int:
    """Return the index just past the closing } matching the brace at open_brace_pos."""
    depth = 1
    i = open_brace_pos + 1
    while i < len(content) and depth > 0:
        c = content[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        i += 1
    return i  # points to the character after the closing }


def _build_backend_block(cloud_body: str, indent: str) -> str:
    """Convert the interior of a cloud{} block to a backend "remote"{} block."""
    inner = indent + "  "  # one level deeper than the cloud keyword

    hostname_m = _HOSTNAME_RE.search(cloud_body)
    org_m = _ORG_RE.search(cloud_body)
    ws_name_m = _WS_NAME_RE.search(cloud_body)
    ws_prefix_m = _WS_PREFIX_RE.search(cloud_body)

    hostname = hostname_m.group(1) if hostname_m else "app.terraform.io"
    org = org_m.group(1) if org_m else ""
    ws_name = ws_name_m.group(1) if ws_name_m else ""
    ws_prefix = ws_prefix_m.group(1) if ws_prefix_m else ""

    lines = [f'{indent}backend "remote" {{']
    lines.append(f'{inner}hostname     = "{hostname}"')
    if org:
        lines.append(f'{inner}organization = "{org}"')
    if ws_name or ws_prefix:
        lines.append(f"{inner}workspaces {{")
        if ws_name:
            lines.append(f'{inner}  name   = "{ws_name}"')
        if ws_prefix:
            lines.append(f'{inner}  prefix = "{ws_prefix}"')
        lines.append(f"{inner}}}")
    lines.append(f"{indent}}}")
    return "\n".join(lines)


class CloudBlockRule(Rule):
    name = "cloud-block-to-backend"

    def apply(self, content: str, path: Path) -> str:
        if "cloud" not in content:
            return content

        m = _CLOUD_KEYWORD_RE.search(content)
        if not m:
            return content

        indent = m.group(1)
        open_brace_pos = content.index("{", m.start())
        block_end = _find_block_end(content, open_brace_pos)
        cloud_body = content[open_brace_pos + 1 : block_end - 1]

        backend_block = _build_backend_block(cloud_body, indent)

        # Replace from the start of the indented "cloud" keyword to end of block
        return content[: m.start()] + backend_block + content[block_end:]
