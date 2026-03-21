# scripts/grain/mart_lint.py
"""Mart model anti-pattern detection (facts, dimensions, reports)."""
from __future__ import annotations

import logging
from typing import Any

import sqlglot
from sqlglot import exp

from scripts._core.models import SelectionTarget

logger = logging.getLogger(__name__)

# Column name patterns that suggest descriptive attributes (should be in dimensions).
DESCRIPTIVE_PATTERNS = (
    "_name", "_email", "_address", "_description", "_region",
    "_type", "_category", "_status", "_phone", "_city", "_state",
)


def check_wide_fact(
    columns: dict[str, dict],
    fk_columns: list[str],
) -> dict[str, Any] | None:
    """Flag facts with embedded descriptive attributes and no corresponding FKs."""
    embedded = []
    for col_name, col_info in columns.items():
        if col_name.endswith("_sk"):
            continue
        if any(col_name.endswith(p) for p in DESCRIPTIVE_PATTERNS):
            # Check if there's a corresponding FK
            entity = col_name.rsplit("_", 1)[0]
            has_fk = any(entity in fk for fk in fk_columns)
            if not has_fk:
                embedded.append(col_name)

    if len(embedded) >= 2:
        return {
            "check": "wide_fact",
            "severity": "warning",
            "message": f"Descriptive columns without dimension FKs: {', '.join(embedded[:5])}",
            "detail": "These columns should live in dimension tables. "
                      "Join via surrogate keys instead of embedding attributes.",
        }
    return None


def check_no_dimension_joins(depends_on: list[str]) -> dict[str, Any] | None:
    """Flag facts that don't join to any dimension model."""
    dim_parents = [d for d in depends_on if ".dim_" in d]
    if not dim_parents:
        return {
            "check": "no_dimension_joins",
            "severity": "warning",
            "message": "Fact does not join to any dim_ model",
            "detail": "Fact models should join to dimensions for descriptive attributes, "
                      "not carry them inline.",
        }
    return None


def check_missing_date_dimension(columns: dict, depends_on: list[str]) -> dict[str, Any] | None:
    """Flag facts with date columns but no dim_date join."""
    date_cols = [c for c in columns if c.endswith(("_date", "_at", "_on", "_key")) and "date" in c]
    dim_date_joined = any(".dim_date" in d for d in depends_on)
    if date_cols and not dim_date_joined:
        return {
            "check": "missing_date_dimension",
            "severity": "warning",
            "message": f"Date columns present ({', '.join(date_cols[:3])}) but no join to dim_date",
            "detail": "Add date_key and join to dim_date for calendar and fiscal attributes.",
        }
    return None


def check_dim_not_referenced(dim_name: str, all_nodes: dict) -> dict[str, Any] | None:
    """Flag dimensions not referenced by any fact or report."""
    for node in all_nodes.values():
        if not isinstance(node, dict):
            continue
        deps = node.get("depends_on", {}).get("nodes", [])
        if any(f".{dim_name}" in d for d in deps):
            return None  # referenced
    return {
        "check": "dim_not_referenced",
        "severity": "warning",
        "message": f"Dimension {dim_name} is not referenced by any fact or report model",
        "detail": "Unused dimensions may indicate a structural gap — facts may be embedding "
                  "attributes that should join to this dimension.",
    }


def check_single_fact_passthrough(depends_on: list[str]) -> dict[str, Any] | None:
    """Flag report models that consume only one fact."""
    fact_parents = [d for d in depends_on if ".fct_" in d]
    if len(fact_parents) == 1:
        return {
            "check": "single_fact_passthrough",
            "severity": "warning",
            "message": f"Report consumes only one fact: {fact_parents[0].split('.')[-1]}",
            "detail": "A report model earns its place when it combines multiple facts "
                      "or aggregates to a different grain. Consider whether your BI tool "
                      "can join the fact to its dimensions directly.",
        }
    return None


def check_no_aggregation(sql: str, dialect: str = "duckdb") -> dict[str, Any] | None:
    """Flag report models with no GROUP BY (no grain change)."""
    try:
        parsed = sqlglot.parse(sql, dialect=dialect)
    except sqlglot.errors.ParseError:
        return None

    for statement in parsed:
        if statement is None:
            continue
        if statement.find(exp.Group):
            return None

    return {
        "check": "no_aggregation",
        "severity": "warning",
        "message": "No GROUP BY clause — report passes data through without changing grain",
        "detail": "Report models should aggregate to a different grain than their source facts.",
    }


def run_mart_lint(
    target: SelectionTarget,
    output_mode: str = "terminal",
) -> list[dict]:
    """Run mart-specific lint checks based on model prefix."""
    from scripts._core.selector import load_manifest
    from scripts.grain.join_analysis import _find_compiled_sql

    manifest = load_manifest()
    node_key = f"model.dcr_analytics.{target.table}"
    node = manifest.get("nodes", {}).get(node_key)

    if node is None:
        logger.warning(f"Model {target.table} not found in manifest")
        return []

    depends_on = node.get("depends_on", {}).get("nodes", [])
    columns = node.get("columns", {})
    findings: list[dict] = []

    if target.table.startswith("fct_"):
        fk_cols = [c for c in columns if c.endswith("_sk") or c.endswith("_id")]
        r = check_wide_fact(columns, fk_cols)
        if r:
            findings.append(r)
        r = check_no_dimension_joins(depends_on)
        if r:
            findings.append(r)
        r = check_missing_date_dimension(columns, depends_on)
        if r:
            findings.append(r)

    elif target.table.startswith("rpt_"):
        r = check_single_fact_passthrough(depends_on)
        if r:
            findings.append(r)

        compiled_path = _find_compiled_sql(target.table)
        if compiled_path:
            sql = compiled_path.read_text(encoding="utf-8")
            r = check_no_aggregation(sql)
            if r:
                findings.append(r)

    elif target.table.startswith("dim_"):
        sk_cols = [c for c in columns if c.endswith("_sk")]
        if not sk_cols:
            findings.append({
                "check": "missing_surrogate_key",
                "severity": "warning",
                "message": "Dimension has no _sk column",
                "detail": "Dimensions should have a surrogate key for downstream joins.",
            })
        r = check_dim_not_referenced(target.table, manifest.get("nodes", {}))
        if r:
            findings.append(r)

    if output_mode == "terminal":
        _render_terminal(target, findings)

    return findings


def _render_terminal(target: SelectionTarget, findings: list[dict]) -> None:
    """Print mart lint results."""
    prefix_label = {
        "fct_": "FACT", "dim_": "DIMENSION", "rpt_": "REPORT"
    }
    label = next((v for k, v in prefix_label.items() if target.table.startswith(k)), "MART")
    print(f"\n{label} LINT: {target.table}")
    print("=" * (len(label) + 7 + len(target.table)))

    if not findings:
        print("  OK No anti-patterns detected.")
        return

    for f in findings:
        icon = "X" if f["severity"] == "error" else "!"
        print(f"  {icon} {f['message']}")
        print(f"    -> {f['detail']}")
