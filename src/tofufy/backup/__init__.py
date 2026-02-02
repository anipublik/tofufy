"""Backup - snapshot a repo directory before writes."""

from __future__ import annotations

import shutil
import tarfile
from datetime import UTC, datetime
from pathlib import Path


def snapshot(repo_path: Path) -> Path:
    """Create a .tar.gz snapshot of repo_path next to it. Returns archive path."""
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    archive = repo_path.parent / f"{repo_path.name}.tofufy-backup.{ts}.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(repo_path, arcname=repo_path.name)
    return archive
