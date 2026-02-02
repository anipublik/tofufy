"""HCL/Tofu file scanner and reader."""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class ParsedFile:
    path: Path
    content: str

    def with_content(self, new_content: str) -> ParsedFile:
        return ParsedFile(path=self.path, content=new_content)


def parse_file(path: Path) -> ParsedFile:
    return ParsedFile(path=path, content=path.read_text(encoding="utf-8"))


def find_tf_files(repo_path: Path, ignore_patterns: list[str]) -> list[Path]:
    """Recursively find .tf, .tofu, .tfvars, and Terragrunt HCL files.

    OpenTofu 1.8+ supports .tofu files. When a directory has both foo.tf and
    foo.tofu, OpenTofu loads only foo.tofu. We convert both so the output is
    consistent, but we flag .tofu files separately so the user knows.

    Terragrunt files (terragrunt.hcl, root.hcl) are included so the
    terraform_binary rule can update them.
    """
    globs = ["*.tf", "*.tofu", "*.tfvars", "terragrunt.hcl", "root.hcl"]
    seen: set[Path] = set()
    results: list[Path] = []

    for pattern in globs:
        for p in sorted(repo_path.rglob(pattern)):
            if p in seen:
                continue
            rel = p.relative_to(repo_path).as_posix()
            if any(fnmatch.fnmatch(rel, pat) for pat in ignore_patterns):
                continue
            # Skip .terraform directories (cached provider code)
            if ".terraform" in p.parts:
                continue
            seen.add(p)
            results.append(p)

    return sorted(results)
