"""Create pull requests on GitHub, GitLab, and Bitbucket."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import git as gitpython  # type: ignore[import-untyped]

PLATFORMS = {"github", "gitlab", "bitbucket"}


class PRCreator:
    def __init__(self, platform: str, token: str, repo_path: Path) -> None:
        if platform not in PLATFORMS:
            raise ValueError(f"Unsupported platform: {platform}")
        self.platform = platform
        self.token = token
        self.repo_path = repo_path

    def create(
        self,
        branch: str,
        title: str,
        draft: bool,
        conversion_result: Optional[object],
    ) -> str:
        repo = gitpython.Repo(self.repo_path)
        self._commit_and_push(repo, branch)

        if self.platform == "github":
            return self._github_pr(repo, branch, title, draft, conversion_result)
        elif self.platform == "gitlab":
            return self._gitlab_mr(repo, branch, title, draft)
        else:
            return self._bitbucket_pr(repo, branch, title)

    def _commit_and_push(self, repo: gitpython.Repo, branch: str) -> None:
        if repo.is_dirty(untracked_files=True):
            repo.git.checkout("-b", branch)
            repo.git.add("-A")
            repo.git.commit("-m", "chore: migrate to OpenTofu via tofufy")
            origin = repo.remote("origin")
            origin.push(branch)

    def _github_pr(
        self,
        repo: gitpython.Repo,
        branch: str,
        title: str,
        draft: bool,
        result: Optional[object],
    ) -> str:
        from github import Github  # type: ignore[import-untyped]

        remote_url = repo.remote("origin").url
        slug = _parse_github_slug(remote_url)

        gh = Github(self.token)
        gh_repo = gh.get_repo(slug)
        body = _build_pr_body(result)

        pr = gh_repo.create_pull(
            title=title,
            body=body,
            head=branch,
            base=gh_repo.default_branch,
            draft=draft,
        )
        return pr.html_url

    def _gitlab_mr(
        self, repo: gitpython.Repo, branch: str, title: str, draft: bool
    ) -> str:
        import httpx

        remote_url = repo.remote("origin").url
        project_path = _parse_gitlab_slug(remote_url)
        encoded = project_path.replace("/", "%2F")

        draft_prefix = "Draft: " if draft else ""
        with httpx.Client(timeout=30) as client:
            r = client.post(
                f"https://gitlab.com/api/v4/projects/{encoded}/merge_requests",
                headers={"PRIVATE-TOKEN": self.token},
                json={
                    "source_branch": branch,
                    "target_branch": "main",
                    "title": draft_prefix + title,
                    "description": _build_pr_body(None),
                },
            )
            r.raise_for_status()
            return r.json()["web_url"]

    def _bitbucket_pr(self, repo: gitpython.Repo, branch: str, title: str) -> str:
        import httpx

        remote_url = repo.remote("origin").url
        workspace, slug = _parse_bitbucket_slug(remote_url)

        with httpx.Client(timeout=30) as client:
            r = client.post(
                f"https://api.bitbucket.org/2.0/repositories/{workspace}/{slug}/pullrequests",
                headers={"Authorization": f"Bearer {self.token}"},
                json={
                    "title": title,
                    "source": {"branch": {"name": branch}},
                    "destination": {"branch": {"name": "main"}},
                    "description": _build_pr_body(None),
                },
            )
            r.raise_for_status()
            return r.json()["links"]["html"]["href"]


def _build_pr_body(result: Optional[object]) -> str:
    lines = [
        "## OpenTofu Migration",
        "",
        "This PR was generated automatically by [tofufy](https://github.com/anipublik/tofufy).",
        "",
        "### Changes",
    ]
    if result and hasattr(result, "changes"):
        for change in result.changes:  # type: ignore[union-attr]
            if change.changed:
                lines.append(f"- `{change.path}` (rules: {', '.join(change.rule_hits)})")
    else:
        lines.append("- See diff for full details.")
    return "\n".join(lines)


def _parse_github_slug(url: str) -> str:
    import re
    m = re.search(r"github\.com[:/](.+?)(?:\.git)?$", url)
    if not m:
        raise ValueError(f"Cannot parse GitHub slug from: {url}")
    return m.group(1)


def _parse_gitlab_slug(url: str) -> str:
    import re
    m = re.search(r"gitlab\.com[:/](.+?)(?:\.git)?$", url)
    if not m:
        raise ValueError(f"Cannot parse GitLab slug from: {url}")
    return m.group(1)


def _parse_bitbucket_slug(url: str) -> tuple[str, str]:
    import re
    m = re.search(r"bitbucket\.org[:/]([^/]+)/([^/]+?)(?:\.git)?$", url)
    if not m:
        raise ValueError(f"Cannot parse Bitbucket slug from: {url}")
    return m.group(1), m.group(2)
