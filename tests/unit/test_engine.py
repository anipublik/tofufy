"""Tests for ConversionEngine."""

from __future__ import annotations

import textwrap
from typing import TYPE_CHECKING

from tofufy.converter.engine import ConversionEngine

if TYPE_CHECKING:
    from pathlib import Path


def _make_repo(tmp_path: Path, files: dict[str, str]) -> Path:
    for name, content in files.items():
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    return tmp_path


def test_engine_detects_registry_change(tmp_path: Path) -> None:
    content = textwrap.dedent("""\
        terraform {
          required_providers {
            aws = {
              source  = "registry.terraform.io/hashicorp/aws"
              version = "~> 5.0"
            }
          }
        }
    """)
    repo = _make_repo(tmp_path, {"main.tf": content})
    engine = ConversionEngine(repo_path=repo, ignore_patterns=[])
    result = engine.run()

    assert result.files_changed == 1
    change = result.changes[0]
    assert "registry-rewrite" in change.rule_hits
    assert "registry.opentofu.org" in change.transformed


def test_engine_respects_ignore_patterns(tmp_path: Path) -> None:
    content = 'source = "registry.terraform.io/hashicorp/aws"\n'
    repo = _make_repo(
        tmp_path,
        {
            "main.tf": content,
            "vendor/module/main.tf": content,
        },
    )
    engine = ConversionEngine(repo_path=repo, ignore_patterns=["vendor/**"])
    result = engine.run()

    changed_paths = [str(c.path.relative_to(repo)) for c in result.changes if c.changed]
    assert "main.tf" in changed_paths
    # vendor file should be ignored entirely (not in result)
    assert not any("vendor" in p for p in changed_paths)


def test_engine_no_changes_when_already_converted(tmp_path: Path) -> None:
    content = textwrap.dedent("""\
        terraform {
          required_providers {
            aws = {
              source  = "registry.opentofu.org/hashicorp/aws"
              version = "~> 5.0"
            }
          }
        }
    """)
    repo = _make_repo(tmp_path, {"main.tf": content})
    engine = ConversionEngine(repo_path=repo, ignore_patterns=[])
    result = engine.run()
    assert result.files_changed == 0


def test_conversion_result_patch(tmp_path: Path) -> None:
    content = 'source = "registry.terraform.io/hashicorp/aws"\n'
    repo = _make_repo(tmp_path, {"main.tf": content})
    engine = ConversionEngine(repo_path=repo, ignore_patterns=[])
    result = engine.run()
    patch = result.as_patch()
    assert "---" in patch
    assert "+++" in patch


def test_engine_finds_tofu_files(tmp_path: Path) -> None:
    """Engine should also convert .tofu files (OpenTofu 1.8+ extension)."""
    content = 'source = "registry.terraform.io/hashicorp/aws"\n'
    repo = _make_repo(tmp_path, {"override.tofu": content})
    engine = ConversionEngine(repo_path=repo, ignore_patterns=[])
    result = engine.run()
    assert result.files_changed == 1
    assert "registry.opentofu.org" in result.changes[0].transformed


def test_engine_skips_dot_terraform_dir(tmp_path: Path) -> None:
    """Cached provider code in .terraform/ must never be touched."""
    content = 'source = "registry.terraform.io/hashicorp/aws"\n'
    repo = _make_repo(
        tmp_path,
        {
            "main.tf": content,
            ".terraform/plugins/main.tf": content,
        },
    )
    engine = ConversionEngine(repo_path=repo, ignore_patterns=[])
    result = engine.run()
    changed_paths = [str(c.path.relative_to(repo)) for c in result.changes if c.changed]
    assert "main.tf" in changed_paths
    assert not any(".terraform" in p for p in changed_paths)
