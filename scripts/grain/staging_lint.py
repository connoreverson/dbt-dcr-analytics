# scripts/grain/staging_lint.py
"""Staging model purity checker -- staging should cast, rename, and return only."""
from __future__ import annotations

import logging
import re
from typing import Any

import sqlglot
from sqlglot import exp

from scripts._core.models import SelectionTarget

logger = logging.getLogger(__name__)

# Functions allowed in staging models (cast/rename/cleanup only).
ALLOWED_FUNCTIONS = frozenset({
    "CAST", "TRY_CAST", "SAFE_CAST",
    "TRIM", "LTRIM", "RTRIM",
    "LOWER", "UPPER",
    "COALESCE", "IFNULL", "NULLIF",
    "TO_DATE", "TO_TIMESTAMP", "DATE", "TIMESTAMP",
})


def check_staging_purity(sql: str, dialect: str = "duckdb") -> list[dict[str, Any]]:
    """Check SQL for operations forbidden in staging models.

    Returns list of findings:
        {"check": str, "severity": "error"|"warning", "message": str, "detail": str}
    """
    findings: list[dict[str, Any]] = []

    # Strip Jinja template expressions before parsing.
    sql = re.sub(r"\{\{.*?\}\}", "placeholder_table", sql)
    sql = re.sub(r"\{%.*?%\}", "", sql)

    try:
        parsed = sqlglot.parse(sql, dialect=dialect)
    except sqlglot.errors.ParseError:
        findings.append({
            "check": "parse_error",
            "severity": "warning",
            "message": "sqlglot could not parse SQL",
            "detail": "Staging lint skipped -- fix syntax first.",
        })
        return findings

    for statement in parsed:
        if statement is None:
            continue

        # Check for JOINs
        for join_node in statement.find_all(exp.Join):
            findings.append({
                "check": "forbidden_join",
                "severity": "error",
                "message": f"Forbidden JOIN: {join_node.sql(dialect=dialect)[:80]}",
                "detail": "Staging models must be 1:1 with their source table. "
                          "Move join logic to an integration model.",
            })

        # Check for GROUP BY
        for group_node in statement.find_all(exp.Group):
            findings.append({
                "check": "forbidden_group_by",
                "severity": "error",
                "message": "Forbidden GROUP BY",
                "detail": "Staging should not aggregate data. "
                          "Move aggregation to integration or mart layer.",
            })

        # Check for WHERE clauses
        for select_node in statement.find_all(exp.Select):
            where = select_node.args.get("where")
            if where:
                findings.append({
                    "check": "forbidden_where",
                    "severity": "error",
                    "message": f"Forbidden WHERE: {where.sql(dialect=dialect)[:80]}",
                    "detail": "Staging should not filter rows. "
                              "Move filtering to integration or mart layer.",
                })

        # Check for subqueries in FROM
        for select_node in statement.find_all(exp.Select):
            from_clause = select_node.args.get("from")
            if from_clause:
                for _subq in from_clause.find_all(exp.Select):
                    findings.append({
                        "check": "forbidden_subquery",
                        "severity": "error",
                        "message": "Forbidden subquery in FROM clause",
                        "detail": "Staging should not contain inline subqueries. "
                                  "Extract the subquery into a CTE or separate model.",
                    })
                    break

        # Check for CASE statements
        for case_node in statement.find_all(exp.Case):
            findings.append({
                "check": "logic_beyond_cast_rename",
                "severity": "warning",
                "message": f"CASE statement: {case_node.sql(dialect=dialect)[:80]}",
                "detail": "Staging should cast and rename only. "
                          "Move business logic to integration layer.",
            })

        # Check for non-allowed function calls
        for func_node in statement.find_all(exp.Anonymous):
            func_name = func_node.name.upper() if hasattr(func_node, "name") else ""
            if func_name and func_name not in ALLOWED_FUNCTIONS:
                findings.append({
                    "check": "logic_beyond_cast_rename",
                    "severity": "warning",
                    "message": f"Function call: {func_name}",
                    "detail": f"{func_name} may introduce logic beyond cast/rename. "
                              "Review whether this belongs in staging.",
                })

    return findings


def run_staging_lint(target: SelectionTarget, output_mode: str = "terminal") -> list[dict]:
    """Run staging purity checks on a model's compiled SQL."""
    from scripts.grain.join_analysis import _find_compiled_sql

    compiled_path = _find_compiled_sql(target.table)
    if compiled_path is None:
        print(f"  No compiled SQL for {target.table} -- run `dbt compile`")
        return []

    sql = compiled_path.read_text(encoding="utf-8")
    findings = check_staging_purity(sql)

    if output_mode == "terminal":
        _render_terminal(target, findings)

    return findings


def _render_terminal(target: SelectionTarget, findings: list[dict]) -> None:
    """Print staging lint results."""
    print(f"\nSTAGING LINT: {target.table}")
    print("=" * (14 + len(target.table)))

    if not findings:
        print("  \u2713 Clean staging model \u2014 cast, rename, return only.")
        return

    for f in findings:
        icon = "\u2717" if f["severity"] == "error" else "\u26a0"
        print(f"  {icon} {f['message']}")
        print(f"    -> {f['detail']}")
