"""Config loading and validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field


class TofufyConfig(BaseModel):
    tfe_url: str = "https://app.terraform.io"
    default_backend: str = "s3"
    tacos_platform: Optional[str] = None
    extra_rules: list[str] = Field(default_factory=list)


def load_config(path: Optional[Path]) -> TofufyConfig:
    if path is None or not path.exists():
        return TofufyConfig()

    import yaml  # type: ignore[import-untyped]

    raw: dict[str, Any] = yaml.safe_load(path.read_text()) or {}
    return TofufyConfig(**raw)
