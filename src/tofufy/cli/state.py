"""State subcommands - list, pull, migrate, rotate-keys."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="TFE state operations.")
console = Console()


def _require_token(token: str | None) -> str:
    if not token:
        token = typer.prompt("TFE token", hide_input=True)
    return token


@app.command("list")
def state_list(
    org: str | None = typer.Option(None, "--org", help="TFE organization"),
    token: str | None = typer.Option(None, "--token", envvar="TFE_TOKEN"),
    tfe_url: str = typer.Option("https://app.terraform.io", "--tfe-url"),
) -> None:
    """List TFE organizations and workspaces."""
    from tofufy.state.client import TFEClient

    token = _require_token(token)
    client = TFEClient(base_url=tfe_url, token=token)

    if org:
        workspaces = client.list_workspaces(org)
        table = Table(title=f"Workspaces in [bold]{org}[/bold]")
        table.add_column("Name")
        table.add_column("Terraform Version")
        table.add_column("Status")
        for ws in workspaces:
            table.add_row(ws.name, ws.terraform_version, ws.status)
        console.print(table)
    else:
        orgs = client.list_organizations()
        table = Table(title="Organizations")
        table.add_column("Name")
        table.add_column("Email")
        for o in orgs:
            table.add_row(o.name, o.email)
        console.print(table)


@app.command("pull")
def state_pull(
    org: str = typer.Option(..., "--org", help="TFE organization"),
    workspace: str | None = typer.Option(None, "--workspace", help="Single workspace name"),
    token: str | None = typer.Option(None, "--token", envvar="TFE_TOKEN"),
    tfe_url: str = typer.Option("https://app.terraform.io", "--tfe-url"),
    out_dir: str = typer.Option("./tfe-state", "--out-dir"),
) -> None:
    """Pull state for one workspace or all workspaces in an org."""
    import asyncio
    from pathlib import Path

    from tofufy.state.puller import StatePuller

    token = _require_token(token)
    puller = StatePuller(base_url=tfe_url, token=token, out_dir=Path(out_dir))

    with console.status("Pulling state..."):
        asyncio.run(puller.pull(org=org, workspace=workspace))

    console.print(f"[green]State saved to[/green] {out_dir}")


@app.command("migrate")
def state_migrate(
    org: str = typer.Option(..., "--org"),
    token: str | None = typer.Option(None, "--token", envvar="TFE_TOKEN"),
    tfe_url: str = typer.Option("https://app.terraform.io", "--tfe-url"),
    workspace: str | None = typer.Option(None, "--workspace"),
    target_backend: str = typer.Option(..., "--target-backend", help="s3 | gcs | azurerm | local"),
    backend_config: str | None = typer.Option(
        None, "--backend-config", help="Path to backend config JSON/HCL"
    ),
) -> None:
    """Pull TFE state and push to a new backend."""
    import asyncio
    from pathlib import Path

    from tofufy.state.migrator import StateMigrator

    token = _require_token(token)
    migrator = StateMigrator(
        base_url=tfe_url,
        token=token,
        target_backend=target_backend,
        backend_config_path=Path(backend_config) if backend_config else None,
    )

    with console.status(f"Migrating state to [bold]{target_backend}[/bold]..."):
        report = asyncio.run(migrator.migrate(org=org, workspace=workspace))

    console.print(f"[green]Migrated {report.workspaces_migrated} workspace(s).[/green]")
    if report.errors:
        for err in report.errors:
            console.print(f"[red]  {err}[/red]")


@app.command("rotate-keys")
def rotate_keys(
    org: str = typer.Option(..., "--org"),
    token: str | None = typer.Option(None, "--token", envvar="TFE_TOKEN"),
    tfe_url: str = typer.Option("https://app.terraform.io", "--tfe-url"),
    workspace: str | None = typer.Option(None, "--workspace"),
) -> None:
    """Rotate state encryption keys post-migration."""
    import asyncio

    from tofufy.state.client import TFEClient

    token = _require_token(token)
    client = TFEClient(base_url=tfe_url, token=token)

    with console.status("Rotating encryption keys..."):
        rotated = asyncio.run(client.rotate_keys(org=org, workspace=workspace))

    console.print(f"[green]Rotated keys for {rotated} workspace(s).[/green]")
