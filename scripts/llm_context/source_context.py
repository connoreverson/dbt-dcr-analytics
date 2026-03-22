# scripts/llm_context/source_context.py
"""Summarize a dbt source table for LLM consumption."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def build_source_context(node: dict) -> dict[str, Any]:
    """Extract structured context from a manifest source node.

    Args:
        node: A dbt manifest source node dict (from manifest.json sources section).

    Returns:
        Dict of section_name -> content suitable for rendering.
    """
    columns = node.get("columns", {})
    col_list = []
    for col_name, col_info in columns.items():
        dtype = col_info.get("data_type", "unknown")
        col_list.append(f"{col_name} ({dtype})")

    return {
        "Source System": node.get("source_name", "unknown"),
        "Table": node.get("name", ""),
        "Schema": node.get("schema", ""),
        "Description": node.get("description", "") or "No description",
        "Columns": col_list if col_list else ["No column metadata in manifest"],
    }


def _build_suggested_prompt(context: dict) -> str:
    """Generate a Gemini prompt pre-filled with source context.

    Args:
        context: Output of build_source_context.

    Returns:
        Prompt string suitable for pasting into an LLM.
    """
    cols_str = ", ".join(context.get("Columns", [])[:10])
    return (
        f"I have a source table '{context['Table']}' from the "
        f"'{context['Source System']}' system.\n"
        f"Columns: {cols_str}\n\n"
        f"What business entity does this table represent? "
        f"What is the likely grain (what does each row represent)? "
        f"Which columns are candidate primary keys? "
        f"What CDM entity should I map this to in the integration layer?"
    )


def run_source_summary(selector: str) -> int:
    """Resolve a source selector and print its LLM-friendly context.

    Args:
        selector: dbt source selector string (e.g., "source:peoplefirst.employees").

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    from scripts._core.selector import resolve_selector, load_manifest
    from scripts._core.renderers.llm import render_llm_context

    targets = resolve_selector(selector)
    manifest = load_manifest()

    for target in targets:
        source_key = f"source.dcr_analytics.{target.schema}.{target.table}"
        node = manifest.get("sources", {}).get(source_key)
        if node is None:
            for val in manifest.get("sources", {}).values():
                if val.get("name") == target.table:
                    node = val
                    break

        if node is None:
            print(f"Source {target.table} not found in manifest.")
            continue

        context = build_source_context(node)
        prompt = _build_suggested_prompt(context)
        output = render_llm_context(context, suggested_prompt=prompt)
        print(output)

    return 0
