# scripts/scaffold/test_scaffold.py
"""Generate missing YAML tests for a dbt model."""
from __future__ import annotations

import logging
from typing import Any

import pandas as pd
import sqlglot
from sqlglot import exp

logger = logging.getLogger(__name__)

LOW_CARDINALITY_THRESHOLD = 15


def suggest_tests_for_column(
    col_name: str,
    dtype: str,
    series: pd.Series,
    existing_tests: list[str],
) -> list[dict[str, Any]]:
    """Suggest tests for a column based on name patterns and data characteristics.

    Args:
        col_name: Column name.
        dtype: Column data type string (e.g., "VARCHAR", "INTEGER").
        series: Sample data for the column.
        existing_tests: Tests already configured for this column.

    Returns:
        List of dicts with keys: test, config, rule_id, reason.
    """
    suggestions: list[dict[str, Any]] = []

    if col_name.endswith(("_id", "_sk", "_key")):
        if "not_null" not in existing_tests:
            suggestions.append({
                "test": "not_null",
                "config": {},
                "rule_id": "YAML-COL-02",
                "reason": f"{col_name} is a key column — must not be null",
            })
        if "unique" not in existing_tests:
            n_unique = series.nunique()
            if n_unique == len(series.dropna()):
                suggestions.append({
                    "test": "unique",
                    "config": {},
                    "rule_id": "YAML-COL-03",
                    "reason": f"{col_name} is unique in sample — candidate primary key",
                })

    if col_name.endswith(("_date", "_at", "_on")):
        if "not_null" not in existing_tests:
            null_rate = series.isna().mean()
            if null_rate < 0.1:
                suggestions.append({
                    "test": "not_null",
                    "config": {},
                    "rule_id": "YAML-COL-02",
                    "reason": f"{col_name} has <10% nulls — likely required",
                })

    is_key_column = col_name.endswith(("_id", "_sk", "_key"))
    if dtype.upper() in ("VARCHAR", "TEXT", "STRING") and not is_key_column:
        n_unique = series.nunique()
        if 1 < n_unique <= LOW_CARDINALITY_THRESHOLD:
            if "accepted_values" not in existing_tests:
                values = sorted(series.dropna().unique().tolist())
                suggestions.append({
                    "test": "accepted_values",
                    "config": {"values": values},
                    "rule_id": "YAML-COL-06",
                    "reason": f"{col_name} has {n_unique} distinct values — categorical",
                })

    return suggestions


def detect_hardcoded_case(sql: str, dialect: str = "duckdb") -> list[dict[str, Any]]:
    """Detect hardcoded CASE statements that could be replaced with seed lookups.

    Args:
        sql: SQL string to analyze.
        dialect: SQL dialect for sqlglot parsing (default "duckdb").

    Returns:
        List of dicts with keys: column, values, mappings.
    """
    cases: list[dict[str, Any]] = []
    try:
        parsed = sqlglot.parse(sql, dialect=dialect)
    except sqlglot.errors.ParseError:
        return []

    for statement in parsed:
        if statement is None:
            continue
        for alias_node in statement.find_all(exp.Alias):
            case_node = alias_node.find(exp.Case)
            if case_node is None:
                continue

            alias_name = alias_node.alias
            values: list[str] = []
            mappings: dict[str, str] = {}

            for if_node in case_node.find_all(exp.If):
                cond = if_node.args.get("this")
                true_val = if_node.args.get("true")
                if cond and true_val:
                    for lit in cond.find_all(exp.Literal):
                        val = lit.this
                        values.append(val)
                        result_lit = true_val.find(exp.Literal)
                        if result_lit:
                            mappings[val] = result_lit.this

            if values:
                cases.append({
                    "column": alias_name,
                    "values": values,
                    "mappings": mappings,
                })

    return cases


def _apply_suggestions(
    node: dict,
    model_name: str,
    suggestions: list[dict[str, Any]],
) -> int:
    """Write test suggestions into the model's YAML properties file.

    Args:
        node: Manifest node for the model.
        model_name: Model name (used to find the entry in the YAML models list).
        suggestions: List of suggestion dicts from suggest_tests_for_column.

    Returns:
        Number of tests written.
    """
    import yaml
    from pathlib import Path

    patch_path = node.get("patch_path", "")
    if not patch_path or "://" not in patch_path:
        return 0

    # Strip the project prefix (e.g. "dcr_analytics://")
    rel_path = patch_path.split("://", 1)[1].replace("\\", "/")
    yaml_path = Path(rel_path)
    if not yaml_path.exists():
        return 0

    content = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    if not content or "models" not in content:
        return 0

    # Find the model entry by name
    model_entry = next(
        (m for m in content["models"] if m.get("name") == model_name), None
    )
    if model_entry is None:
        return 0

    if "columns" not in model_entry or model_entry["columns"] is None:
        model_entry["columns"] = []

    columns_list: list[dict] = model_entry["columns"]

    applied = 0
    for suggestion in suggestions:
        col_name = _find_col_name_for_suggestion(suggestion, suggestions)
        if col_name is None:
            continue

        # Find or create column entry
        col_entry = next((c for c in columns_list if c.get("name") == col_name), None)
        if col_entry is None:
            col_entry = {"name": col_name}
            columns_list.append(col_entry)

        if "tests" not in col_entry or col_entry["tests"] is None:
            col_entry["tests"] = []

        test_name = suggestion["test"]
        existing_test_names = [
            t if isinstance(t, str) else next(iter(t), "")
            for t in col_entry["tests"]
        ]

        if test_name in existing_test_names:
            continue

        if suggestion["config"]:
            col_entry["tests"].append({test_name: suggestion["config"]})
        else:
            col_entry["tests"].append(test_name)
        applied += 1

    if applied > 0:
        yaml_path.write_text(
            yaml.dump(content, default_flow_style=False, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )

    return applied


def _find_col_name_for_suggestion(
    suggestion: dict[str, Any],
    all_suggestions: list[dict[str, Any]],
) -> str | None:
    """Extract the column name a suggestion refers to from its reason text."""
    # The reason always starts with the column name followed by a space or " is"
    reason = suggestion.get("reason", "")
    # Reason format: "<col_name> is a key column..." or "<col_name> has ..."
    if " " in reason:
        return reason.split(" ", 1)[0]
    return None


def run_test_scaffold(
    selector: str,
    apply_changes: bool = False,
    count_only: bool = False,
) -> int:
    """Full test scaffolding pipeline.

    Args:
        selector: dbt model selector.
        apply_changes: If True, write suggestions into YAML file.
        count_only: If True, return count of missing tests (for preflight use).

    Returns:
        Exit code (0 for success), or suggestion count when count_only=True.
    """
    from scripts._core.selector import resolve_selector, load_manifest

    targets = resolve_selector(selector)
    manifest = load_manifest()
    total_suggestions = 0

    for target in targets:
        node_key = f"model.dcr_analytics.{target.table}"
        node = manifest.get("nodes", {}).get(node_key)
        if node is None:
            continue

        # Build existing tests lookup: {col_name: [test_names]}
        existing: dict[str, list[str]] = {}
        for key, test_node in manifest.get("nodes", {}).items():
            if not key.startswith("test."):
                continue
            # Check this test is attached to the current model
            depends = test_node.get("depends_on", {}).get("nodes", [])
            if node_key not in depends:
                continue
            test_meta = test_node.get("test_metadata", {})
            test_name = test_meta.get("name", "")
            col_name = test_meta.get("kwargs", {}).get("column_name", "")
            if col_name and test_name:
                existing.setdefault(col_name, []).append(test_name)

        try:
            if target.connector_type == "duckdb":
                from scripts._core.connectors.duckdb import DuckDBConnector

                connector = DuckDBConnector(target)
            else:
                from scripts._core.connectors.bigquery import BigQueryConnector

                connector = BigQueryConnector(target)
            df = connector.get_sample(1000)
            if hasattr(connector, "close"):
                connector.close()
        except Exception:
            df = None

        all_suggestions: list[dict[str, Any]] = []
        if df is not None:
            for col_name in df.columns:
                dtype = str(df[col_name].dtype)
                col_existing = existing.get(col_name, [])
                suggestions = suggest_tests_for_column(
                    col_name=col_name,
                    dtype=dtype,
                    series=df[col_name],
                    existing_tests=col_existing,
                )
                all_suggestions.extend(suggestions)

        total_suggestions += len(all_suggestions)
        if count_only:
            continue

        from scripts.grain.join_analysis import _find_compiled_sql

        compiled_path = _find_compiled_sql(target.table)
        case_findings: list[dict[str, Any]] = []
        if compiled_path:
            sql = compiled_path.read_text(encoding="utf-8")
            case_findings = detect_hardcoded_case(sql)

        applied_count = 0
        if apply_changes and all_suggestions:
            applied_count = _apply_suggestions(node, target.table, all_suggestions)

        print(f"\nTEST SCAFFOLD: {target.table}")
        print("=" * (16 + len(target.table)))

        if not all_suggestions and not case_findings:
            print("  \u2713 No missing tests detected.")
            continue

        if apply_changes and all_suggestions:
            if applied_count > 0:
                print(f"  \u2713 Applied {applied_count} test(s) to YAML.")
            else:
                print("  \u26a0 Could not apply tests — YAML file not found or model entry missing.")
            if case_findings:
                print()
        else:
            print("\n# Suggested tests (add to your model's YAML columns section):")
            for s in all_suggestions:
                print(f"\n# Rule {s['rule_id']}: {s['reason']}")
                if s["test"] == "accepted_values":
                    values_str = ", ".join(f"'{v}'" for v in s["config"]["values"][:10])
                    print(f"      - accepted_values:")
                    print(f"          values: [{values_str}]")
                else:
                    print(f"      - {s['test']}")

        for case in case_findings:
            print(
                f"\n# \u26a0 Hardcoded CASE on column '{case['column']}'"
                " — consider seed:"
            )
            for k, v in case.get("mappings", {}).items():
                print(f"#   {k} \u2192 {v}")
            print("# See spec Phase 3 for seed-driven lookup suggestion template.")

    if count_only:
        return total_suggestions

    return 0
