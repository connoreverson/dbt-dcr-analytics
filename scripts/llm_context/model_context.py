# scripts/llm_context/model_context.py
"""Summarize an existing dbt model for LLM consumption."""
from __future__ import annotations

import logging
import re
from typing import Any

from scripts._core.selector import determine_layer

logger = logging.getLogger(__name__)

LAYER_LABELS = {
    "staging": "Staging",
    "base": "Base",
    "integration": "Integration",
    "marts": "Mart",
    "unknown": "Unknown",
}


def build_model_context(node: dict) -> dict[str, Any]:
    """Extract structured context from a manifest node.

    Args:
        node: A dbt manifest node dict (from manifest.json nodes section).

    Returns:
        Ordered dict of section_name -> content suitable for rendering.
    """
    name = node.get("name", "")
    layer = determine_layer(name)
    layer_label = LAYER_LABELS.get(layer, "Unknown")

    if layer == "marts":
        if name.startswith("fct_"):
            layer_label = "Mart (fact)"
        elif name.startswith("dim_"):
            layer_label = "Mart (dimension)"
        elif name.startswith("rpt_"):
            layer_label = "Mart (report)"

    meta = node.get("meta", {})
    depends_on = node.get("depends_on", {}).get("nodes", [])
    parents = [d.split(".")[-1] for d in depends_on]
    columns = node.get("columns", {})

    keys = [c for c in columns if c.endswith("_sk") or c.endswith("_id") or c.endswith("_key")]
    measures = [
        c for c in columns
        if any(c.endswith(s) for s in ("_amount", "_count", "_total", "_sum", "_avg", "_rate"))
    ]
    attributes = [c for c in columns if c not in keys and c not in measures]

    description = node.get("description", "") or ""

    # Grain: prefer structured meta field; fall back to extracting from description
    grain = meta.get("grain") or _extract_grain_from_description(description) or "Not documented"

    # CDM entity: prefer structured meta field; fall back to description mention
    cdm_entity = meta.get("cdm_entity") or _extract_cdm_entity_from_description(description) or "Not specified"

    return {
        "Model": name,
        "Layer": layer_label,
        "Description": description or "No description",
        "CDM Entity": cdm_entity,
        "Grain": grain,
        "Parents": parents if parents else ["None"],
        "Key Columns": keys if keys else ["None identified"],
        "Measures": measures if measures else ["None"],
        "Attributes": attributes[:15] if attributes else ["None"],
    }


def _extract_grain_from_description(description: str) -> str | None:
    """Try to extract a grain statement from the model description text.

    Looks for patterns like "Grain: one row per..." embedded in the description.

    Args:
        description: The model's description string.

    Returns:
        Extracted grain text, or None if not found.
    """
    match = re.search(r"\bGrain[:\s]+([^.]+)\.", description, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


def _extract_cdm_entity_from_description(description: str) -> str | None:
    """Try to extract a CDM entity mention from the model description text.

    Looks for patterns like "CDM X entity" or "CDM entity X" in the description.

    Args:
        description: The model's description string.

    Returns:
        Extracted CDM entity name, or None if not found.
    """
    # Matches "CDM Park entity", "CDM Employee entity", etc.
    match = re.search(r"\bCDM\s+(\w+)\s+entity\b", description, re.IGNORECASE)
    if match:
        return match.group(1)
    # Matches "custom CDM X entity"
    match = re.search(r"\bcustom\s+CDM\s+(\w+)\s+entity\b", description, re.IGNORECASE)
    if match:
        return match.group(1)
    return None


def _build_suggested_prompt(context: dict) -> str:
    """Generate a suggested LLM prompt pre-filled with model context.

    Args:
        context: Output of build_model_context.

    Returns:
        Prompt string suitable for pasting into an LLM.
    """
    parents_str = ", ".join(context.get("Parents", []))
    return (
        f"I have a dbt {context['Layer'].lower()} model called {context['Model']}.\n"
        f"It consumes: {parents_str}.\n"
        f"CDM entity: {context.get('CDM Entity', 'unknown')}.\n\n"
        f"How should I improve this model's design? "
        f"Consider: grain clarity, join cardinality, test coverage, "
        f"and whether the column classification is correct."
    )


def run_model_summary(selector: str) -> int:
    """Resolve a model selector and print its LLM-friendly context.

    Args:
        selector: dbt model selector string (e.g., "int_parks").

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    from scripts._core.selector import resolve_selector, load_manifest
    from scripts._core.renderers.llm import render_llm_context

    targets = resolve_selector(selector)
    manifest = load_manifest()

    for target in targets:
        node_key = f"model.dcr_analytics.{target.table}"
        node = manifest.get("nodes", {}).get(node_key)
        if node is None:
            print(f"Model {target.table} not found in manifest.")
            continue

        context = build_model_context(node)
        prompt = _build_suggested_prompt(context)
        output = render_llm_context(context, suggested_prompt=prompt)
        print(output)

    return 0
