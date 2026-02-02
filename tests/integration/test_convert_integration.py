"""Integration tests for end-to-end conversion against testdata fixtures."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from tofufy.converter.engine import ConversionEngine

FIXTURES = Path(__file__).parent.parent / "testdata" / "fixtures"


def test_full_conversion_fixture(tmp_path: Path) -> None:
    """Registry rewrite fixture: input -> expected."""
    shutil.copy(FIXTURES / "registry_input.tf", tmp_path / "main.tf")
    expected = (FIXTURES / "registry_expected.tf").read_text()

    engine = ConversionEngine(repo_path=tmp_path, ignore_patterns=[])
    result = engine.run()

    assert result.files_changed == 1
    assert result.changes[0].transformed == expected


def test_write_changes(tmp_path: Path) -> None:
    shutil.copy(FIXTURES / "registry_input.tf", tmp_path / "main.tf")

    engine = ConversionEngine(repo_path=tmp_path, ignore_patterns=[])
    result = engine.run()
    result.write()

    on_disk = (tmp_path / "main.tf").read_text()
    assert "registry.opentofu.org" in on_disk
    assert "registry.terraform.io" not in on_disk
