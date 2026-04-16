"""Config loading and validation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from pathlib import Path


class TofufyConfig(BaseModel):
    tfe_url: str = "https://app.terraform.io"
    default_backend: str = "s3"
    tacos_platform: str | None = None
    extra_rules: list[str] = Field(default_factory=list)


def load_config(path: Path | None) -> TofufyConfig:
    if path is None or not path.exists():
        return TofufyConfig()

    import yaml

    raw: dict[str, Any] = yaml.safe_load(path.read_text()) or {}
    return TofufyConfig(**raw)
