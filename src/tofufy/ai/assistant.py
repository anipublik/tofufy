"""AI-assisted refinement pass using litellm (BYOK)."""

from __future__ import annotations

from typing import TYPE_CHECKING

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


class AIAssistant:
    def __init__(self, provider: str, api_key: str | None) -> None:
        self.provider = provider
        self.api_key = api_key

        # Map provider names to litellm model strings
        self._model_map = {
            "anthropic": "claude-sonnet-4-6",
            "openai": "gpt-4o",
            "kimi": "moonshot/moonshot-v1-8k",
            "openrouter": "openrouter/auto",
        }

    def refine(self, result: "ConversionResult") -> "ConversionResult":
        import litellm  # type: ignore[import-untyped]

        model = self._model_map.get(self.provider, self.provider)
        extra: dict = {}
        if self.api_key:
            extra["api_key"] = self.api_key

        for change in result.changes:
            if not change.changed:
                continue

            response = litellm.completion(
                model=model,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            f"File: {change.path}\n\n```hcl\n{change.transformed}\n```"
                        ),
                    },
                ],
                **extra,
            )
            refined = response.choices[0].message.content or change.transformed
            # Strip markdown fences if the model wrapped the output
            if refined.startswith("```"):
                lines = refined.splitlines()
                refined = "\n".join(lines[1:-1]) if lines[-1] == "```" else refined

            change.transformed = refined
            if "ai-refine" not in change.rule_hits:
                change.rule_hits.append("ai-refine")

        return result
