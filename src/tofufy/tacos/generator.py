"""Generate TACOS platform configuration files."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003

# Built-in templates keyed by platform name
_TEMPLATES: dict[str, dict[str, str]] = {
    "atlantis": {
        "atlantis.yaml": """\
version: 3
automerge: true
projects:
{%- for ws in workspaces %}
  - name: {{ ws }}
    dir: {{ ws }}
    workflow: opentofu
    autoplan:
      when_modified: ["*.tf", "*.tfvars"]
      enabled: true
{%- endfor %}
workflows:
  opentofu:
    plan:
      steps:
        - init
        - plan
    apply:
      steps:
        - apply
""",
    },
    "spacelift": {
        ".spacelift/config.yml": """\
version: "1"
stacks:
{%- for ws in workspaces %}
  - name: {{ ws }}
    project_root: {{ ws }}
    terraform_version: "1.6"
    iac_type: opentofu
{%- endfor %}
""",
    },
    "env0": {
        "env0.yml": """\
templates:
{%- for ws in workspaces %}
  - name: {{ ws }}
    path: {{ ws }}
    type: opentofu
    opentofu_version: "1.6"
{%- endfor %}
""",
    },
    "scalr": {
        ".scalr-run-triggers.json": """\
{
  "version": 1,
  "workspaces": [
{%- for ws in workspaces %}
    {"name": "{{ ws }}", "directory": "{{ ws }}"}{% if not loop.last %},{% endif %}
{%- endfor %}
  ]
}
""",
    },
    "digger": {
        "digger.yml": """\
projects:
{%- for ws in workspaces %}
  - name: {{ ws }}
    dir: {{ ws }}
    workflow: default
{%- endfor %}
workflows:
  default:
    plan:
      steps:
        - init
        - plan
    apply:
      steps:
        - apply
""",
    },
}


class TACOSGenerator:
    def __init__(
        self,
        platform: str,
        repo_path: Path,
        out_path: Path,
        template_dir: Path | None = None,
    ) -> None:
        self.platform = platform
        self.repo_path = repo_path
        self.out_path = out_path
        self.template_dir = template_dir

    def _discover_workspaces(self) -> list[str]:
        """Find directories that contain .tf files - treat each as a workspace."""
        workspaces: list[str] = []
        for p in sorted(self.repo_path.rglob("*.tf")):
            rel = p.parent.relative_to(self.repo_path).as_posix()
            if rel not in workspaces and rel != ".":
                workspaces.append(rel)
        return workspaces or ["."]

    def _render(self, template: str, workspaces: list[str]) -> str:
        try:
            from jinja2 import Environment

            env = Environment(trim_blocks=True, lstrip_blocks=True)
            tmpl = env.from_string(template)
            return tmpl.render(workspaces=workspaces)
        except ImportError:
            # Fallback: basic substitution without jinja2
            return template.replace("{%- for ws in workspaces %}", "").replace("{%- endfor %}", "")

    def generate(self, dry_run: bool = False) -> list[Path]:
        templates = self._load_templates()
        workspaces = self._discover_workspaces()
        written = []

        for rel_path, template in templates.items():
            content = self._render(template, workspaces)
            out_file = self.out_path / rel_path

            if not dry_run:
                out_file.parent.mkdir(parents=True, exist_ok=True)
                out_file.write_text(content, encoding="utf-8")

            written.append(out_file)

        return written

    def _load_templates(self) -> dict[str, str]:
        # User custom templates override built-ins
        if self.template_dir and self.template_dir.exists():
            return {f.name: f.read_text() for f in self.template_dir.iterdir() if f.is_file()}
        return _TEMPLATES.get(self.platform, {})
