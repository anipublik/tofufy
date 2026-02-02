"""Rule: update Terragrunt HCL for OpenTofu.

Changes in terragrunt.hcl files:
  - terraform_binary = "terraform" -> terraform_binary = "tofu"
  - Add terraform_binary = "tofu" if not already set (in terraform {} blocks)
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from tofufy.converter.rules.base import Rule

if TYPE_CHECKING:
    from pathlib import Path

_BINARY_SET_RE = re.compile(
    r"""
    (terraform_binary\s*=\s*")  # key =  "
    terraform                    # old value
    (")                          # closing quote
    """,
    re.VERBOSE,
)

# Detect if the file is a terragrunt file and has a terraform {} block without binary set
_TF_BLOCK_RE = re.compile(r"^(terraform\s*\{)", re.MULTILINE)
_BINARY_ALREADY_SET_RE = re.compile(r"terraform_binary\s*=")

_TERRAGRUNT_FILES = {".hcl"}


class TerragruntRule(Rule):
    name = "terragrunt-binary"

    def apply(self, content: str, path: Path) -> str:
        if path.suffix not in _TERRAGRUNT_FILES:
            return content

        # Only apply to terragrunt.hcl files (or root.hcl, etc.)
        # Skip plain Terraform .tf.hcl files that aren't terragrunt configs
        is_terragrunt = (
            "terragrunt" in path.name.lower()
            or "terragrunt" in content[:500]
            or "terraform_binary" in content
            or "inputs" in content  # terragrunt-specific keyword
            or "remote_state" in content  # terragrunt-specific block
        )
        if not is_terragrunt:
            return content

        # Replace explicit terraform binary setting
        if _BINARY_SET_RE.search(content):
            content = _BINARY_SET_RE.sub(r'\1tofu\2', content)
            return content

        # If there's a terraform {} block without terraform_binary, inject it
        if _TF_BLOCK_RE.search(content) and not _BINARY_ALREADY_SET_RE.search(content):
            content = _TF_BLOCK_RE.sub(
                r'\1\n  terraform_binary = "tofu"',
                content,
                count=1,
            )

        return content
