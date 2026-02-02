"""Rule: replace deprecated Terraform built-in functions.

  list(a, b, c)        ->  [a, b, c]
  map("k", v)          ->  { k = v }  (single-pair only; complex maps flagged)
  template_file data   ->  templatefile() function (annotate with TODO)
  encode_tfvars(x)     ->  jsonencode(x)
  decode_tfvars(x)     ->  jsondecode(x)
"""

from __future__ import annotations

import re
from pathlib import Path

from tofufy.converter.rules.base import Rule

# encode_tfvars / decode_tfvars - removed in OpenTofu
_ENCODE_TFVARS_RE = re.compile(r"\bencode_tfvars\s*\(")
_DECODE_TFVARS_RE = re.compile(r"\bdecode_tfvars\s*\(")

# list(a, b, c) -> [a, b, c]
# Only handles simple single-level calls (no nested list() calls).
_LIST_FUNC_RE = re.compile(
    r"""
    \blist\(              # list(
    ([^()]+)              # args - no nested parens
    \)                    # )
    """,
    re.VERBOSE,
)

# map("key", value) -> { key = value } - single pair only
_MAP_FUNC_RE = re.compile(
    r"""
    \bmap\(
    \s*"([^"]+)"\s*,\s*   # "key",
    ([^()]+?)             # value (no nested parens)
    \s*\)
    """,
    re.VERBOSE,
)

# data "template_file" usage - flag with TODO comment
_TEMPLATE_FILE_DATA_RE = re.compile(
    r"""
    ^([ \t]*)             # indent
    data\s+"template_file"\s+"(\w+)"\s*\{
    """,
    re.MULTILINE | re.VERBOSE,
)

_TEMPLATE_FILE_RESOURCE_REF_RE = re.compile(
    r'\bdata\.template_file\.(\w+)\.rendered\b'
)


def _list_replace(m: re.Match) -> str:  # type: ignore[type-arg]
    args = m.group(1)
    return f"[{args}]"


def _map_replace(m: re.Match) -> str:  # type: ignore[type-arg]
    key, value = m.group(1), m.group(2).strip()
    return "{ " + f'{key} = {value}' + " }"


def _template_file_flag(m: re.Match) -> str:  # type: ignore[type-arg]
    indent, name = m.group(1), m.group(2)
    todo = (
        f'{indent}# TOFUFY: Replace this data "template_file" block with the '
        f'templatefile() function.\n'
        f'{indent}# Example: templatefile("${{path.module}}/tmpl.tftpl", var.vars)\n'
        f'{indent}# Then remove the null provider and this data source entirely.\n'
    )
    return todo + m.group(0)


class DeprecatedFunctionsRule(Rule):
    name = "deprecated-functions"

    def apply(self, content: str, path: Path) -> str:
        content = _ENCODE_TFVARS_RE.sub("jsonencode(", content)
        content = _DECODE_TFVARS_RE.sub("jsondecode(", content)
        content = _LIST_FUNC_RE.sub(_list_replace, content)
        content = _MAP_FUNC_RE.sub(_map_replace, content)

        if 'data "template_file"' in content:
            content = _TEMPLATE_FILE_DATA_RE.sub(_template_file_flag, content)

        return content
