# scripts/llm_context/model_context.py
"""Summarize an existing dbt model for LLM consumption."""
from __future__ import annotations

import logging
import re
from typing import Any

from scripts._core.selector import determine_layer
from scripts._core.standards import load_standards_for_layer

logger = logging.getLogger(__name__)

LAYER_LABELS = {
    "staging": "Staging",
    "base": "Base",
    "integration": "Integration",
    "marts": "Mart",
    "unknown": "Unknown",
}


def _extract_sql_design_notes(raw_code: str) -> list[str]:
    """Extract block comments from raw SQL that document design decisions.

    Captures ``/* ... */`` blocks, strips leading asterisks and whitespace,
    and returns each block as a single normalised string.

    Args:
        raw_code: Raw SQL string from the manifest node.

    Returns:
        List of non-empty design-note strings.
    """
    blocks = re.findall(r"/\*(.*?)\*/", raw_code, re.DOTALL)
    notes: list[str] = []
    for block in blocks:
        # Strip leading '*' on each line (common doc-comment style)
        lines = [re.sub(r"^\s*\*\s?", "", ln) for ln in block.splitlines()]
        note = " ".join(ln.strip() for ln in lines if ln.strip())
        if note:
            notes.append(note)
    return notes


def _format_test_label(test_name: str, kwargs: dict) -> str:
    """Produce a human-readable test label with key kwargs inlined.

    Args:
        test_name: Base test name (e.g. ``"relationships"``).
        kwargs: Test metadata kwargs dict.

    Returns:
        Formatted string like ``"relationships → ref('int_parks').parks_sk"``.
    """
    if test_name == "relationships":
        to = kwargs.get("to", "")
        field = kwargs.get("field", "")
        if to and field:
            return f"relationships → {to}.{field}"
    if test_name in ("expect_table_row_count_to_be_between",):
        lo = kwargs.get("min_value", "?")
        hi = kwargs.get("max_value", "?")
        return f"row_count between {lo} and {hi}"
    if test_name == "accepted_values":
        vals = kwargs.get("values", [])
        vals_str = ", ".join(str(v) for v in vals[:8])
        suffix = "…" if len(vals) > 8 else ""
        return f"accepted_values: [{vals_str}{suffix}]"
    if test_name == "unique_combination_of_columns":
        cols = kwargs.get("combination_of_columns", [])
        return f"unique_combination_of_columns: ({', '.join(cols)})"
    return test_name


def _extract_test_coverage(
    model_unique_id: str, all_nodes: dict
) -> tuple[dict[str, list[str]], list[str]]:
    """Collect test coverage grouped by column, separated from downstream FK refs.

    A test is considered "own" if the model under review is the primary subject
    (i.e. its ``attached_node`` matches or it is the only dependency). Tests
    whose ``model`` kwarg references a *different* model are downstream FK checks
    that happen to reference this model — these are reported separately.

    Args:
        model_unique_id: The ``unique_id`` of the target model node.
        all_nodes: The full ``manifest["nodes"]`` dict.

    Returns:
        Tuple of (own_coverage, downstream_refs):
        - own_coverage: dict mapping column/``"[model-level]"`` → list of test labels
        - downstream_refs: list of strings like ``"int_work_orders.parks_sk → relationships"``
    """
    own: dict[str, list[str]] = {}
    downstream: list[str] = []

    for node in all_nodes.values():
        if node.get("resource_type") != "test":
            continue
        deps = node.get("depends_on", {}).get("nodes", [])
        if model_unique_id not in deps:
            continue

        test_meta = node.get("test_metadata") or {}
        test_name = test_meta.get("name") or node.get("name", "unknown")
        kwargs = test_meta.get("kwargs", {}) or {}
        label = _format_test_label(test_name, kwargs)

        # Determine whether this test belongs to the model or to a downstream caller.
        # The `model` kwarg references which model the test is defined on.
        model_kwarg = kwargs.get("model", "")
        attached = node.get("attached_node", "") or ""
        is_own = (
            model_unique_id == attached
            or model_unique_id in model_kwarg
            or not model_kwarg  # singular tests have no model kwarg
        )

        if is_own:
            col = node.get("column_name") or "[model-level]"
            own.setdefault(col, []).append(label)
        else:
            # Extract downstream model name from the model kwarg
            # e.g. "{{ get_where_subquery(ref('int_work_orders')) }}" → "int_work_orders"
            m = re.search(r"ref\('([^']+)'\)", model_kwarg)
            downstream_model = m.group(1) if m else "unknown"
            col = node.get("column_name") or "unknown_col"
            downstream.append(f"{downstream_model}.{col} → {label}")

    return own, downstream


def _upstream_grain_summary(parent_names: list[str], all_nodes: dict) -> list[str]:
    """Return a one-line grain summary for each upstream parent model.

    Args:
        parent_names: List of short model names (e.g. ``["stg_geoparks__parks_master"]``).
        all_nodes: The full ``manifest["nodes"]`` dict.

    Returns:
        List of strings like ``"stg_geoparks__parks_master — one row per park record"``.
    """
    summaries: list[str] = []
    for name in parent_names:
        node_key = f"model.dcr_analytics.{name}"
        parent_node = all_nodes.get(node_key)
        if parent_node is None:
            summaries.append(f"{name} — (not found in manifest)")
            continue
        desc = parent_node.get("description", "") or ""
        meta = parent_node.get("meta", {}) or {}
        grain = meta.get("grain") or _extract_grain_from_description(desc) or "grain not documented"
        summaries.append(f"{name} — {grain}")
    return summaries


def build_model_context(
    node: dict,
    manifest: dict | None = None,
    include_standards: bool = False,
) -> dict[str, Any]:
    """Extract structured context from a manifest node.

    Args:
        node: A dbt manifest node dict (from manifest.json nodes section).
        manifest: Full manifest dict. When supplied, test coverage, upstream
            grain, and SQL design notes are included in the output.

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

    all_nodes = (manifest or {}).get("nodes", {})

    # Upstream grain — one line per parent
    upstream_grain = _upstream_grain_summary(parents, all_nodes) if all_nodes else []

    # Test coverage — own tests grouped by column; downstream FK refs separated
    unique_id = node.get("unique_id", f"model.dcr_analytics.{name}")
    if all_nodes:
        test_coverage_map, downstream_refs = _extract_test_coverage(unique_id, all_nodes)
    else:
        test_coverage_map, downstream_refs = {}, []
    test_coverage_lines: list[str] = []
    for col in sorted(test_coverage_map.keys()):
        tests_str = ", ".join(test_coverage_map[col])
        test_coverage_lines.append(f"{col}: {tests_str}")

    # SQL design notes from block comments
    raw_code = node.get("raw_code", "") or ""
    design_notes = _extract_sql_design_notes(raw_code) if raw_code else []

    ctx: dict[str, Any] = {
        "Model": name,
        "Layer": layer_label,
        "Description": description or "No description",
        "CDM Entity": cdm_entity,
        "Grain": grain,
        "Parents": parents if parents else ["None"],
    }

    if upstream_grain:
        ctx["Upstream Grain"] = upstream_grain

    ctx["Key Columns"] = keys if keys else ["None identified"]
    ctx["Measures"] = measures if measures else ["None"]
    ctx["Attributes"] = attributes[:15] if attributes else ["None"]

    if test_coverage_lines:
        ctx["Test Coverage"] = test_coverage_lines
    else:
        ctx["Test Coverage"] = ["No tests found — check YAML configuration"]

    if downstream_refs:
        ctx["Referenced By (FK integrity)"] = sorted(downstream_refs)

    if design_notes:
        ctx["SQL Design Notes"] = design_notes

    if raw_code:
        ctx["SQL"] = raw_code

    if include_standards:
        try:
            manual_rules, automated_rules = load_standards_for_layer(layer)
            if manual_rules:
                ctx["Governance: Judgment Rules"] = [
                    f"{r['id']} — {r['title']}: {r['description']}"
                    for r in manual_rules
                ]
            if automated_rules:
                ctx["Governance: Automated Checks"] = [
                    f"{r['id']} — {r['title']}"
                    for r in automated_rules
                ]
        except FileNotFoundError:
            ctx["Governance"] = ["Standards JSON not found — run parse_standards first."]

    return ctx


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


def run_model_summary(selector: str, include_standards: bool = False) -> int:
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

        context = build_model_context(node, manifest=manifest, include_standards=include_standards)
        prompt = _build_suggested_prompt(context)
        output = render_llm_context(context, suggested_prompt=prompt)
        print(output)

    return 0
