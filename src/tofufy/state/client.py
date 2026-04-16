"""TFE API client."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

import httpx


@dataclass
class Organization:
    name: str
    email: str


@dataclass
class Workspace:
    name: str
    id: str
    terraform_version: str
    status: str


class TFEClient:
    def __init__(self, base_url: str, token: str) -> None:
        self.base_url = base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/vnd.api+json",
        }

    def _get(self, path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        with httpx.Client(base_url=self.base_url, headers=self._headers, timeout=30) as client:
            r = client.get(path, params=params)
            r.raise_for_status()
            return cast("dict[str, Any]", r.json())

    async def _aget(self, path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        async with httpx.AsyncClient(
            base_url=self.base_url, headers=self._headers, timeout=30
        ) as client:
            r = await client.get(path, params=params)
            r.raise_for_status()
            return cast("dict[str, Any]", r.json())

    def list_organizations(self) -> list[Organization]:
        data = self._get("/api/v2/organizations")
        return [
            Organization(
                name=o["attributes"]["name"],
                email=o["attributes"].get("email", ""),
            )
            for o in data.get("data", [])
        ]

    def list_workspaces(self, org: str) -> list[Workspace]:
        data = self._get(f"/api/v2/organizations/{org}/workspaces", {"page[size]": "100"})
        return [
            Workspace(
                name=w["attributes"]["name"],
                id=w["id"],
                terraform_version=w["attributes"].get("terraform-version", ""),
                status=w["attributes"].get("resource-count", "?"),
            )
            for w in data.get("data", [])
        ]

    async def get_current_state_version(self, workspace_id: str) -> dict[str, Any] | None:
        try:
            data = await self._aget(f"/api/v2/workspaces/{workspace_id}/current-state-version")
            return data.get("data")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise

    async def rotate_keys(self, org: str, workspace: str | None) -> int:
        """Placeholder: key rotation via TFE API. Returns count of rotated workspaces."""
        # TFE does not expose a direct key-rotation API endpoint; this is typically
        # handled by re-encrypting state via the state push API after pulling.
        workspaces = self.list_workspaces(org)
        if workspace:
            workspaces = [w for w in workspaces if w.name == workspace]
        # In a real implementation: pull state, re-encrypt, push back.
        return len(workspaces)
