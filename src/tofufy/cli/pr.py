"""PR creation command."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

app = typer.Typer(help="Create a pull request from the converted diff.")
console = Console()


@app.command("create")
def pr_create(
    repo_path: Annotated[Path, typer.Option("--path")] = Path("."),
    token: str | None = typer.Option(None, "--token", envvar="GITHUB_TOKEN"),
    platform: str = typer.Option("github", "--platform", help="github | gitlab | bitbucket"),
    branch: str = typer.Option("tofufy/opentofu-migration", "--branch"),
    title: str = typer.Option("chore: migrate to OpenTofu", "--title"),
    draft: bool = typer.Option(False, "--draft"),
) -> None:
    """Create a PR from the current diff against the base branch."""
    _do_create(
        repo_path=repo_path,
        result=None,
        token=token,
        platform=platform,
        branch=branch,
        title=title,
        draft=draft,
    )


def _do_create(
    repo_path: Path,
    result: object,
    token: str | None,
    platform: str,
    branch: str = "tofufy/opentofu-migration",
    title: str = "chore: migrate to OpenTofu",
    draft: bool = False,
) -> None:
    from tofufy.git.pr import PRCreator

    if not token:
        token = typer.prompt(f"{platform.capitalize()} token", hide_input=True)

    creator = PRCreator(platform=platform, token=token, repo_path=repo_path)

    with console.status("Creating pull request..."):
        url = creator.create(branch=branch, title=title, draft=draft, conversion_result=result)

    console.print(f"\n[bold green]PR created:[/bold green] {url}")
