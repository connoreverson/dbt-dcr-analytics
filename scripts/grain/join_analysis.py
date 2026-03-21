# scripts/grain/join_analysis.py
"""Join cardinality checker using sqlglot AST parsing."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import sqlglot
from sqlglot import exp

from scripts._core.models import SelectionTarget

logger = logging.getLogger(__name__)


def extract_joins(sql: str, dialect: str = "duckdb") -> list[dict[str, str]]:
    """Parse SQL and extract all JOIN clauses with type and ON condition.

    Returns list of:
        {"join_type": "LEFT"|"INNER"|..., "on_condition": str, "right_table": str}
    """
    joins: list[dict[str, str]] = []
    try:
        parsed = sqlglot.parse(sql, dialect=dialect)
    except sqlglot.errors.ParseError:
        logger.warning("sqlglot failed to parse SQL — skipping join analysis")
        return []

    for statement in parsed:
        if statement is None:
            continue
        for join_node in statement.find_all(exp.Join):
            # sqlglot stores LEFT/RIGHT/FULL in "side" and INNER/CROSS in "kind"
            side = join_node.args.get("side")
            kind = join_node.args.get("kind")

            if side:
                join_type = side.upper()
            elif kind:
                join_type = kind.upper()
            else:
                join_type = "JOIN"

            # Extract the ON condition
            on_expr = join_node.args.get("on")
            on_str = on_expr.sql(dialect=dialect) if on_expr else ""

            # Extract the right-side table
            right = join_node.find(exp.Table)
            right_table = right.name if right else ""

            joins.append({
                "join_type": join_type,
                "on_condition": on_str,
                "right_table": right_table,
            })

    return joins


def classify_cardinality(
    left_distinct: int,
    right_distinct: int,
    result_rows: int,
    left_rows: int,
) -> dict[str, Any]:
    """Classify join cardinality from counts.

    Returns:
        {"cardinality": "1:1"|"1:M"|"M:1"|"M:M", "fan_out": bool, "expansion_ratio": float}
    """
    expansion = result_rows / left_rows if left_rows > 0 else 0

    if left_distinct == right_distinct and expansion <= 1.05:
        card = "1:1"
    elif left_distinct > right_distinct and expansion > 1.05:
        card = "1:M"
    elif left_distinct < right_distinct and expansion <= 1.05:
        card = "M:1"
    else:
        card = "M:M"

    return {
        "cardinality": card,
        "fan_out": expansion > 1.05,
        "expansion_ratio": round(expansion, 3),
    }


def run_join_analysis(target: SelectionTarget, output_mode: str = "terminal") -> list[dict]:
    """Analyze all joins in a model's compiled SQL.

    Loads compiled SQL from target/compiled/, parses and returns all JOIN clauses.
    Cardinality classification requires additional warehouse queries (not yet implemented).
    """
    compiled_path = _find_compiled_sql(target.table)
    if compiled_path is None:
        logger.warning(f"No compiled SQL found for {target.table} — run `dbt compile`")
        return []

    sql = compiled_path.read_text(encoding="utf-8")
    joins = extract_joins(sql)

    if output_mode == "terminal":
        _render_terminal(target, joins)

    return joins


def _find_compiled_sql(model_name: str) -> Path | None:
    """Find the compiled SQL for a model in target/compiled/."""
    project_root = Path(__file__).parents[2]
    compiled_dir = project_root / "target" / "compiled"
    if not compiled_dir.exists():
        return None
    for sql_file in compiled_dir.rglob(f"{model_name}.sql"):
        return sql_file
    return None


def _render_terminal(target: SelectionTarget, joins: list[dict]) -> None:
    """Print join analysis results to terminal."""
    print(f"\nJOIN ANALYSIS: {target.table}")
    print("=" * (16 + len(target.table)))

    if not joins:
        print("  No joins found in compiled SQL.")
        return

    for i, j in enumerate(joins, 1):
        print(f"  {i}. {j['join_type']} JOIN → {j['right_table']}")
        if j["on_condition"]:
            print(f"     ON {j['on_condition']}")
