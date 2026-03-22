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
        dtype = col_info.get("data_type") or "—"
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

    # Extract the dbt source name from the selector (e.g. "peoplefirst" from
    # "source:peoplefirst.employees"). resolve_selector returns the database
    # schema (e.g. "raw_peoplefirst") which differs from the dbt source name.
    dbt_source_name: str | None = None
    if selector.startswith("source:"):
        parts = selector[len("source:"):].split(".", 1)
        dbt_source_name = parts[0]

    targets = resolve_selector(selector)
    manifest = load_manifest()

    for target in targets:
        # Try key using dbt source name first, then fall back to schema
        source_key = (
            f"source.dcr_analytics.{dbt_source_name}.{target.table}"
            if dbt_source_name
            else f"source.dcr_analytics.{target.schema}.{target.table}"
        )
        node = manifest.get("sources", {}).get(source_key)

        if node is None:
            # Fallback: match by table name AND source_name to avoid ambiguity
            for val in manifest.get("sources", {}).values():
                if val.get("name") == target.table:
                    if dbt_source_name is None or val.get("source_name") == dbt_source_name:
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
