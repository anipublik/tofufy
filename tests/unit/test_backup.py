"""Tests for backup snapshot."""

from __future__ import annotations

import tarfile
from typing import TYPE_CHECKING

from tofufy.backup import snapshot

if TYPE_CHECKING:
    from pathlib import Path


def test_snapshot_creates_archive(tmp_path: Path) -> None:
    repo = tmp_path / "myrepo"
    repo.mkdir()
    (repo / "main.tf").write_text("resource {}")

    archive = snapshot(repo)

    assert archive.exists()
    assert archive.suffix == ".gz"
    with tarfile.open(archive) as tar:
        names = tar.getnames()
    assert any("main.tf" in n for n in names)
