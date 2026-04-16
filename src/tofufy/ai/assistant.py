"""AI-assisted refinement pass using litellm (BYOK)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tofufy.converter.engine import ConversionResult

_SYSTEM_PROMPT = """\
You are an expert Terraform/OpenTofu engineer. The user will give you a single \
Terraform HCL file that has already undergone rule-based conversion to OpenTofu. \
Your job is to:
1. Identify any remaining Terraform-specific patterns that need updating.
2. Rewrite only those sections to be idiomatic OpenTofu.
3. Return ONLY the full file content with no commentary.
"""

# Map provider aliases to litellm model strings.
PROVIDER_MODELS: dict[str, str] = {
    "anthropic": "claude-sonnet-4-6",
    "openai": "gpt-4o",
    "kimi": "moonshot/moonshot-v1-8k",
    "openrouter": "openrouter/auto",
}


class AIAssistantError(RuntimeError):
    """Raised when the AI pass cannot run (missing extras, invalid provider, etc.)."""


def _require_litellm() -> Any:
    try:
        import litellm
    except ImportError as err:  # pragma: no cover - exercised only when extra missing
        raise AIAssistantError(
            'litellm is required for --ai. Install the extra: pip install "tofufy[ai]"'
        ) from err
    return litellm


def resolve_model(provider: str) -> str:
    """Return the litellm model string for the given provider alias."""
    return PROVIDER_MODELS.get(provider, provider)


class AIAssistant:
    def __init__(self, provider: str, api_key: str | None) -> None:
        self.provider = provider
        self.api_key = api_key
        self.model = resolve_model(provider)

    def refine(self, result: ConversionResult) -> ConversionResult:
        litellm = _require_litellm()
        extra: dict[str, Any] = {}
        if self.api_key:
            extra["api_key"] = self.api_key

        for change in result.changes:
            if not change.changed:
                continue

            response = litellm.completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": (f"File: {change.path}\n\n```hcl\n{change.transformed}\n```"),
                    },
                ],
                **extra,
            )
            refined = response.choices[0].message.content or change.transformed
            refined = _strip_code_fences(refined)

            change.transformed = refined
            if "ai-refine" not in change.rule_hits:
                change.rule_hits.append("ai-refine")

        return result


def _strip_code_fences(text: str) -> str:
    """Strip a leading ```lang fence and trailing ``` if the model wrapped the output."""
    stripped = text.strip()
    if not stripped.startswith("```"):
        return text
    lines = stripped.splitlines()
    if len(lines) < 2:
        return text
    body = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
    return "\n".join(body)
