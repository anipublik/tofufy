"""Tests for .tofufyignore parsing."""

from __future__ import annotations

from typing import TYPE_CHECKING

from tofufy.utils.ignore import load_ignore_patterns

if TYPE_CHECKING:
    from pathlib import Path


def test_load_ignore_patterns(tmp_path: Path) -> None:
    ignore = tmp_path / ".tofufyignore"
    ignore.write_text("# comment\nvendor/**\n.terraform/**\n\n")
    patterns = load_ignore_patterns(ignore)
    assert patterns == ["vendor/**", ".terraform/**"]


def test_load_ignore_missing(tmp_path: Path) -> None:
    assert load_ignore_patterns(tmp_path / ".tofufyignore") == []
