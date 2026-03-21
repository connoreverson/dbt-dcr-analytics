"""LLM-optimized renderer: structured markdown for pasting into Gemini or other LLMs."""
from __future__ import annotations


def render_llm_context(
    sections: dict[str, str | list[str]],
    suggested_prompt: str | None = None,
) -> str:
    """Render sections as clean markdown optimized for LLM consumption.

    Args:
        sections: Ordered dict of section_name -> content.
            Content can be a string or list of strings (rendered as bullets).
        suggested_prompt: Optional pre-written prompt for the analyst to paste.
            An empty string is treated as absent (falsy check).

    Returns:
        Markdown string with no decorative formatting.
    """
    lines: list[str] = []
    for heading, content in sections.items():
        lines.append(f"## {heading}")
        if isinstance(content, list):
            for item in content:
                lines.append(f"- {item}")
        else:
            lines.append(str(content))
        lines.append("")

    if suggested_prompt:
        lines.append("## Suggested Prompt")
        lines.append(suggested_prompt)
        lines.append("")

    return "\n".join(lines)
