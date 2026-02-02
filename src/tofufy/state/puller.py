"""Pull TFE state to local files."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Optional

import httpx

from tofufy.state.client import TFEClient


class StatePuller:
    def __init__(self, base_url: str, token: str, out_dir: Path) -> None:
        self.client = TFEClient(base_url=base_url, token=token)
        self.out_dir = out_dir
        self._token = token
        self._base_url = base_url

    async def pull(self, org: str, workspace: Optional[str]) -> None:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        workspaces = self.client.list_workspaces(org)

        if workspace:
            workspaces = [w for w in workspaces if w.name == workspace]

        await asyncio.gather(*[self._pull_workspace(w.id, w.name) for w in workspaces])

    async def _pull_workspace(self, ws_id: str, ws_name: str) -> None:
        sv = await self.client.get_current_state_version(ws_id)
        if not sv:
            return

        download_url = sv.get("attributes", {}).get("hosted-state-download-url")
        if not download_url:
            return

        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.get(
                download_url,
                headers={"Authorization": f"Bearer {self._token}"},
            )
            r.raise_for_status()
            state_data = r.json()

        out_file = self.out_dir / f"{ws_name}.tfstate"
        out_file.write_text(json.dumps(state_data, indent=2))
