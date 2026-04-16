"""Migrate TFE state to a new backend."""

from __future__ import annotations

import asyncio
import json
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

from tofufy.state.client import TFEClient
from tofufy.state.puller import StatePuller

SUPPORTED_BACKENDS = {"s3", "gcs", "azurerm", "local"}


@dataclass
class MigrationReport:
    workspaces_migrated: int = 0
    errors: list[str] = field(default_factory=list)


class StateMigrator:
    def __init__(
        self,
        base_url: str,
        token: str,
        target_backend: str,
        backend_config_path: Path | None,
    ) -> None:
        if target_backend not in SUPPORTED_BACKENDS:
            raise ValueError(
                f"Unsupported backend: {target_backend}. Supported: {', '.join(SUPPORTED_BACKENDS)}"
            )
        self.client = TFEClient(base_url=base_url, token=token)
        self.target_backend = target_backend
        self.backend_config_path = backend_config_path
        self._base_url = base_url
        self._token = token

    async def migrate(self, org: str, workspace: str | None) -> MigrationReport:
        report = MigrationReport()

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            puller = StatePuller(base_url=self._base_url, token=self._token, out_dir=tmp_path)
            await puller.pull(org=org, workspace=workspace)

            for state_file in tmp_path.glob("*.tfstate"):
                try:
                    await self._push_to_backend(state_file)
                    report.workspaces_migrated += 1
                except Exception as exc:
                    report.errors.append(f"{state_file.stem}: {exc}")

        return report

    async def _push_to_backend(self, state_file: Path) -> None:
        """Push a .tfstate file to the configured backend."""
        backend = self.target_backend

        if backend == "local":
            dest = Path("./migrated-state") / state_file.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(state_file.read_bytes())
            return

        if backend == "s3":
            await self._push_s3(state_file)
        elif backend == "gcs":
            await self._push_gcs(state_file)
        elif backend == "azurerm":
            await self._push_azurerm(state_file)

    async def _push_s3(self, state_file: Path) -> None:
        try:
            import boto3
        except ImportError as err:
            raise RuntimeError('boto3 required for S3 backend. pip install "tofufy[s3]"') from err

        cfg = self._load_backend_config()
        bucket = cfg.get("bucket", "")
        key = cfg.get("key_prefix", "tofufy") + f"/{state_file.name}"
        region = cfg.get("region", "us-east-1")

        # boto3 is sync; run it off the event loop so concurrent uploads
        # actually run concurrently instead of serialising the loop.
        def _upload() -> None:
            s3 = boto3.client("s3", region_name=region)
            s3.upload_file(str(state_file), bucket, key)

        await asyncio.to_thread(_upload)

    async def _push_gcs(self, state_file: Path) -> None:
        try:
            from google.cloud import storage
        except ImportError as err:
            raise RuntimeError(
                'google-cloud-storage required for GCS backend. pip install "tofufy[gcs]"'
            ) from err
        cfg = self._load_backend_config()
        bucket_name = cfg.get("bucket", "")
        prefix = cfg.get("prefix", "tofufy")

        def _upload() -> None:
            client = storage.Client()
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(f"{prefix}/{state_file.name}")
            blob.upload_from_filename(str(state_file))

        await asyncio.to_thread(_upload)

    async def _push_azurerm(self, state_file: Path) -> None:
        raise NotImplementedError("AzureRM backend push not yet implemented.")

    def _load_backend_config(self) -> dict[str, str]:
        if not self.backend_config_path or not self.backend_config_path.exists():
            return {}
        text = self.backend_config_path.read_text()
        if self.backend_config_path.suffix == ".json":
            return cast("dict[str, str]", json.loads(text))
        # Basic HCL key=value parsing
        cfg: dict[str, str] = {}
        for line in text.splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                cfg[k.strip()] = v.strip().strip('"')
        return cfg
