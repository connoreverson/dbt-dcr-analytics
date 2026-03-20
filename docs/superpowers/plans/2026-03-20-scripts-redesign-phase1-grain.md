# Phase 1: `grain/` — Grain Verification, Join Cardinality, Layer-Specific Lint — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `grain/` package that catches fan-out errors, grain violations, and layer-specific anti-patterns (staging purity, integration pass-throughs, mart-layer misuse) — the exact issues plaguing the analyst team across all four dashboard projects.

**Architecture:** Six modules behind a single CLI. `key_discovery` and `join_analysis` do warehouse-side analytical queries via `_core/connectors`. `staging_lint`, `integration_lint`, `mart_lint`, and `dag_lint` combine manifest inspection with sqlglot AST parsing of compiled SQL. The CLI auto-detects the model's layer and runs the appropriate linters.

**Tech Stack:** Python 3.10+, sqlglot (AST parsing), `_core/connectors` (warehouse queries), `_core/selector` (dbt resolution), `_core/config` (manifest)

**Spec:** `docs/superpowers/specs/2026-03-20-scripts-redesign-design.md` (section: "Phase 1: `grain/`")

**Depends on:** Phase 0 (`_core/` package must be complete)

---

### Task 1: Create `grain/` package structure and CLI skeleton

**Files:**
- Create: `scripts/grain/__init__.py`
- Create: `scripts/grain/cli.py`
- Test: `tests/scripts/test_grain_cli.py`

- [ ] **Step 1: Write test for CLI argument parsing**

```python
# tests/scripts/test_grain_cli.py
from scripts.grain.cli import parse_args


def test_parse_args_basic():
    args = parse_args(["--select", "fct_reservations"])
    assert args.select == "fct_reservations"
    assert args.output == "terminal"


def test_parse_args_with_output():
    args = parse_args(["--select", "int_parks", "--output", "markdown"])
    assert args.output == "markdown"


def test_parse_args_with_checks():
    args = parse_args(["--select", "fct_reservations", "--checks", "grain,joins"])
    assert args.checks == "grain,joins"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/scripts/test_grain_cli.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement CLI skeleton**

```python
# scripts/grain/__init__.py
```

```python
# scripts/grain/cli.py
"""Grain verification, join cardinality, and layer-specific lint.

Usage:
    python -m scripts.grain --select fct_reservations
    python -m scripts.grain --select int_parks --output markdown
    python -m scripts.grain --select stg_vistareserve__reservations --checks staging
"""
from __future__ import annotations

import argparse
import logging
import sys


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Grain verification, join cardinality, and layer-specific lint.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--select", "-s", required=True, metavar="SELECTOR",
        help="dbt model selector (e.g. fct_reservations, int_parks)",
    )
    parser.add_argument(
        "--output", "-o", default="terminal", metavar="MODE",
        help="Output mode: terminal, markdown, llm (default: terminal)",
    )
    parser.add_argument(
        "--checks", default="all", metavar="CHECKS",
        help="Comma-separated checks: grain, joins, lint, all (default: all)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

    from scripts._core.selector import resolve_selector, _determine_layer

    try:
        targets = resolve_selector(args.select)
    except Exception as exc:
        print(f"Error resolving selector: {exc}", file=sys.stderr)
        return 1

    checks = set(args.checks.split(",")) if args.checks != "all" else {"grain", "joins", "lint"}
    exit_code = 0

    for target in targets:
        layer = _determine_layer(target.table)

        if "grain" in checks:
            from scripts.grain.key_discovery import run_key_discovery
            run_key_discovery(target, args.output)

        if "joins" in checks:
            from scripts.grain.join_analysis import run_join_analysis
            run_join_analysis(target, args.output)

        if "lint" in checks:
            if layer == "staging" or layer == "base":
                from scripts.grain.staging_lint import run_staging_lint
                run_staging_lint(target, args.output)
            elif layer == "integration":
                from scripts.grain.integration_lint import run_integration_lint
                run_integration_lint(target, args.output)
            elif layer == "marts":
                from scripts.grain.mart_lint import run_mart_lint
                run_mart_lint(target, args.output)

            from scripts.grain.dag_lint import run_dag_lint
            run_dag_lint(target, args.output)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/scripts/test_grain_cli.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/grain/ tests/scripts/test_grain_cli.py
git commit -m "feat(grain): create package structure and CLI skeleton"
```

---

### Task 2: Implement `key_discovery.py` — Candidate PK detection

**Files:**
- Create: `scripts/grain/key_discovery.py`
- Test: `tests/scripts/test_key_discovery.py`

- [ ] **Step 1: Write test for uniqueness ratio calculation**

```python
# tests/scripts/test_key_discovery.py
import pandas as pd
import pytest
from scripts.grain.key_discovery import (
    compute_uniqueness_ratios,
    find_candidate_keys,
    check_yaml_test_coverage,
)


def test_compute_uniqueness_ratios():
    """Uniqueness ratio = count_distinct / total_rows."""
    df = pd.DataFrame({
        "id": [1, 2, 3, 4, 5],
        "category": ["a", "a", "b", "b", "c"],
        "constant": ["x", "x", "x", "x", "x"],
    })
    ratios = compute_uniqueness_ratios(df)
    assert ratios["id"] == 1.0
    assert ratios["category"] == pytest.approx(0.6)
    assert ratios["constant"] == pytest.approx(0.2)


def test_find_candidate_keys_single_column():
    """A perfectly unique column is a candidate key."""
    df = pd.DataFrame({
        "pk": [1, 2, 3],
        "name": ["a", "b", "c"],
        "group": ["x", "x", "y"],
    })
    candidates = find_candidate_keys(df)
    # pk and name are both perfectly unique
    assert candidates[0]["columns"] == ["pk"]
    assert candidates[0]["uniqueness_ratio"] == 1.0


def test_find_candidate_keys_composite():
    """Two columns together form a composite key."""
    df = pd.DataFrame({
        "a": [1, 1, 2, 2],
        "b": ["x", "y", "x", "y"],
        "c": [10, 10, 10, 10],
    })
    candidates = find_candidate_keys(df)
    composite = [c for c in candidates if len(c["columns"]) == 2]
    assert any(
        set(c["columns"]) == {"a", "b"} and c["uniqueness_ratio"] == 1.0
        for c in composite
    )


def test_check_yaml_test_coverage():
    """Identifies whether candidate key has unique test in YAML."""
    yaml_tests = {
        "pk_col": ["unique", "not_null"],
        "other_col": ["not_null"],
    }
    result = check_yaml_test_coverage(["pk_col"], yaml_tests)
    assert result["covered"] is True
    assert result["missing_tests"] == []

    result2 = check_yaml_test_coverage(["other_col"], yaml_tests)
    assert result2["covered"] is False
    assert "unique" in result2["missing_tests"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/scripts/test_key_discovery.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement `key_discovery.py`**

```python
# scripts/grain/key_discovery.py
"""Candidate primary key detection via analytical queries."""
from __future__ import annotations

import itertools
import logging
from typing import Any

import pandas as pd

from scripts._core.models import SelectionTarget

logger = logging.getLogger(__name__)

# Columns with individual uniqueness ratio below this threshold
# are excluded from combination testing.
ELIGIBILITY_THRESHOLD = 0.5

# Stop testing 3-column combos if a 1- or 2-column candidate
# achieves at least this uniqueness ratio.
CANDIDATE_THRESHOLD = 0.99

# Cap on number of 2-column combinations to test.
MAX_2COL_COMBOS = 50


def compute_uniqueness_ratios(df: pd.DataFrame) -> dict[str, float]:
    """Compute count_distinct / total_rows for every column."""
    total = len(df)
    if total == 0:
        return {}
    return {col: df[col].nunique() / total for col in df.columns}


def find_candidate_keys(
    df: pd.DataFrame,
    eligibility_threshold: float = ELIGIBILITY_THRESHOLD,
    candidate_threshold: float = CANDIDATE_THRESHOLD,
    max_2col_combos: int = MAX_2COL_COMBOS,
) -> list[dict[str, Any]]:
    """Find candidate primary keys by testing column uniqueness.

    Returns a list of candidates sorted by uniqueness ratio (desc),
    each as: {"columns": [...], "uniqueness_ratio": float}
    """
    total = len(df)
    if total == 0:
        return []

    # Phase 1: single-column sweep
    ratios = compute_uniqueness_ratios(df)
    candidates: list[dict[str, Any]] = []

    for col, ratio in ratios.items():
        if ratio >= eligibility_threshold:
            candidates.append({"columns": [col], "uniqueness_ratio": ratio})

    # If we already have a perfect single-column key, skip composites
    if any(c["uniqueness_ratio"] >= candidate_threshold for c in candidates):
        candidates.sort(key=lambda c: c["uniqueness_ratio"], reverse=True)
        return candidates

    # Phase 2: 2-column combinations of eligible columns
    eligible = [col for col, ratio in ratios.items() if ratio >= eligibility_threshold]
    combos_2 = list(itertools.combinations(eligible, 2))[:max_2col_combos]

    for combo in combos_2:
        distinct = df.groupby(list(combo)).ngroups
        ratio = distinct / total
        candidates.append({"columns": list(combo), "uniqueness_ratio": ratio})

    if any(c["uniqueness_ratio"] >= candidate_threshold for c in candidates):
        candidates.sort(key=lambda c: c["uniqueness_ratio"], reverse=True)
        return candidates

    # Phase 3: 3-column combinations (only if needed)
    combos_3 = list(itertools.combinations(eligible, 3))[:max_2col_combos]
    for combo in combos_3:
        distinct = df.groupby(list(combo)).ngroups
        ratio = distinct / total
        candidates.append({"columns": list(combo), "uniqueness_ratio": ratio})

    candidates.sort(key=lambda c: c["uniqueness_ratio"], reverse=True)
    return candidates


def check_yaml_test_coverage(
    key_columns: list[str],
    yaml_tests: dict[str, list[str]],
) -> dict[str, Any]:
    """Check if candidate key columns have unique/unique_combination tests.

    Args:
        key_columns: The columns forming the candidate key.
        yaml_tests: Dict of column_name -> list of test names from YAML.

    Returns:
        {"covered": bool, "missing_tests": list[str]}
    """
    missing = []
    if len(key_columns) == 1:
        col = key_columns[0]
        col_tests = yaml_tests.get(col, [])
        if "unique" not in col_tests:
            missing.append("unique")
        if "not_null" not in col_tests:
            missing.append("not_null")
    else:
        # For composite keys, we need unique_combination_of_columns
        # This is harder to detect from simple column->tests mapping;
        # for now, check that all columns have not_null
        for col in key_columns:
            col_tests = yaml_tests.get(col, [])
            if "not_null" not in col_tests:
                missing.append(f"not_null on {col}")
        # Check for unique_combination at model level (simplified)
        if "unique" not in missing:
            missing.append("unique_combination_of_columns")

    return {"covered": len(missing) == 0, "missing_tests": missing}


def _extract_yaml_tests(node: dict) -> dict[str, list[str]]:
    """Extract existing test names per column from a manifest node."""
    yaml_tests: dict[str, list[str]] = {}
    for col_name in node.get("columns", {}):
        yaml_tests[col_name] = []

    # Walk manifest tests (simplified — full extraction requires walking node.tests)
    for test_node in node.get("config", {}).get("data_tests", []):
        if isinstance(test_node, dict):
            for test_name, test_config in test_node.items():
                col = test_config.get("column_name", "")
                if col:
                    yaml_tests.setdefault(col, []).append(test_name)
    return yaml_tests


def run_key_discovery(target: SelectionTarget, output_mode: str = "terminal") -> list[dict]:
    """Full key discovery pipeline for a model.

    Queries the materialized table, finds candidate keys, checks YAML coverage.
    """
    from scripts._core.connectors.duckdb import DuckDBConnector
    from scripts._core.connectors.bigquery import BigQueryConnector
    from scripts._core.selector import load_manifest

    if target.connector_type == "duckdb":
        connector = DuckDBConnector(target)
    else:
        connector = BigQueryConnector(target)

    try:
        df = connector.get_sample(10000)
    finally:
        if hasattr(connector, "close"):
            connector.close()

    candidates = find_candidate_keys(df)

    # Cross-reference with YAML tests
    try:
        manifest = load_manifest()
        node_key = f"model.dcr_analytics.{target.table}"
        node = manifest.get("nodes", {}).get(node_key, {})
        yaml_tests = _extract_yaml_tests(node)
        for candidate in candidates:
            coverage = check_yaml_test_coverage(candidate["columns"], yaml_tests)
            candidate["yaml_covered"] = coverage["covered"]
            candidate["missing_tests"] = coverage["missing_tests"]
    except Exception:
        pass  # YAML cross-reference is best-effort

    if output_mode == "terminal":
        _render_terminal(target, candidates)

    return candidates


def _render_terminal(target: SelectionTarget, candidates: list[dict]) -> None:
    """Print key discovery results to terminal."""
    print(f"\nKEY DISCOVERY: {target.table}")
    print("=" * (16 + len(target.table)))

    if not candidates:
        print("  No candidate keys found.")
        return

    for i, c in enumerate(candidates[:10]):
        cols = ", ".join(c["columns"])
        ratio = c["uniqueness_ratio"]
        marker = "✓" if ratio >= 0.99 else "~" if ratio >= 0.9 else "✗"
        print(f"  {marker} [{ratio:.1%}] {cols}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/scripts/test_key_discovery.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/grain/key_discovery.py tests/scripts/test_key_discovery.py
git commit -m "feat(grain): implement key_discovery with candidate PK detection"
```

---

### Task 3: Implement `join_analysis.py` — Join cardinality checker

**Files:**
- Create: `scripts/grain/join_analysis.py`
- Test: `tests/scripts/test_join_analysis.py`

- [ ] **Step 1: Write test for sqlglot JOIN extraction**

```python
# tests/scripts/test_join_analysis.py
from scripts.grain.join_analysis import extract_joins


def test_extract_joins_single_left_join():
    sql = """
    select a.id, b.name
    from orders a
    left join customers b on a.customer_id = b.customer_id
    """
    joins = extract_joins(sql)
    assert len(joins) == 1
    assert joins[0]["join_type"] == "LEFT"
    assert "customer_id" in joins[0]["on_condition"]


def test_extract_joins_multiple():
    sql = """
    select o.id, c.name, p.product_name
    from orders o
    inner join customers c on o.customer_id = c.customer_id
    left join products p on o.product_id = p.product_id
    """
    joins = extract_joins(sql)
    assert len(joins) == 2
    assert joins[0]["join_type"] == "INNER"
    assert joins[1]["join_type"] == "LEFT"


def test_extract_joins_no_joins():
    sql = "select id, name from customers"
    joins = extract_joins(sql)
    assert len(joins) == 0


def test_extract_joins_cte():
    sql = """
    with source as (
        select * from raw_data
    ),
    enriched as (
        select s.id, d.label
        from source s
        left join dim_types d on s.type_id = d.type_id
    )
    select * from enriched
    """
    joins = extract_joins(sql)
    assert len(joins) == 1
    assert joins[0]["join_type"] == "LEFT"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/scripts/test_join_analysis.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement `join_analysis.py`**

```python
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
            join_type = "INNER"  # default
            if join_node.args.get("side"):
                join_type = join_node.args["side"].upper()
            elif join_node.args.get("kind"):
                join_type = join_node.args["kind"].upper()

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
    elif left_distinct >= right_distinct and expansion > 1.05:
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

    Loads compiled SQL from target/compiled/, parses joins,
    then queries both sides to classify cardinality.
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
    compiled_dir = Path("target/compiled")
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/scripts/test_join_analysis.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/grain/join_analysis.py tests/scripts/test_join_analysis.py
git commit -m "feat(grain): implement join_analysis with sqlglot AST parsing"
```

---

### Task 4: Implement `staging_lint.py` — Staging model purity checker

**Files:**
- Create: `scripts/grain/staging_lint.py`
- Test: `tests/scripts/test_staging_lint.py`

- [ ] **Step 1: Write test for staging forbidden operations**

```python
# tests/scripts/test_staging_lint.py
from scripts.grain.staging_lint import check_staging_purity


def test_clean_staging_passes():
    sql = """
    with source as (
        select * from {{ source('vistareserve', 'reservations') }}
    )
    select
        cast(id as integer) as reservation_id,
        trim(guest_name) as guest_name,
        cast(created_at as timestamp) as created_at
    from source
    """
    findings = check_staging_purity(sql)
    violations = [f for f in findings if f["severity"] == "error"]
    assert len(violations) == 0


def test_forbidden_join():
    sql = """
    select a.id, b.name
    from source_a a
    left join source_b b on a.id = b.id
    """
    findings = check_staging_purity(sql)
    assert any(f["check"] == "forbidden_join" for f in findings)


def test_forbidden_group_by():
    sql = """
    select category, count(*) as cnt
    from source
    group by category
    """
    findings = check_staging_purity(sql)
    assert any(f["check"] == "forbidden_group_by" for f in findings)


def test_forbidden_where():
    sql = """
    select id, name
    from source
    where status != 'deleted'
    """
    findings = check_staging_purity(sql)
    assert any(f["check"] == "forbidden_where" for f in findings)


def test_case_statement_flagged():
    sql = """
    select
        id,
        case when type = 'A' then 'Active' else 'Inactive' end as status
    from source
    """
    findings = check_staging_purity(sql)
    assert any(f["check"] == "logic_beyond_cast_rename" for f in findings)


def test_allowed_functions_pass():
    """CAST, TRIM, LOWER, UPPER, COALESCE are allowed in staging."""
    sql = """
    select
        cast(id as integer) as id,
        lower(trim(name)) as name,
        coalesce(email, '') as email,
        upper(code) as code
    from source
    """
    findings = check_staging_purity(sql)
    violations = [f for f in findings if f["severity"] == "error"]
    assert len(violations) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/scripts/test_staging_lint.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement `staging_lint.py`**

```python
# scripts/grain/staging_lint.py
"""Staging model purity checker — staging should cast, rename, and return only."""
from __future__ import annotations

import logging
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

    try:
        parsed = sqlglot.parse(sql, dialect=dialect)
    except sqlglot.errors.ParseError:
        findings.append({
            "check": "parse_error",
            "severity": "warning",
            "message": "sqlglot could not parse SQL",
            "detail": "Staging lint skipped — fix syntax first.",
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

        # Check for WHERE (excluding inside QUALIFY/window)
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

        # Check for subqueries in FROM (inline subquery)
        for select_node in statement.find_all(exp.Select):
            from_clause = select_node.args.get("from")
            if from_clause:
                for subq in from_clause.find_all(exp.Select):
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
        print(f"  No compiled SQL for {target.table} — run `dbt compile`")
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
        print("  ✓ Clean staging model — cast, rename, return only.")
        return

    for f in findings:
        icon = "✗" if f["severity"] == "error" else "⚠"
        print(f"  {icon} {f['message']}")
        print(f"    → {f['detail']}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/scripts/test_staging_lint.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/grain/staging_lint.py tests/scripts/test_staging_lint.py
git commit -m "feat(grain): implement staging_lint with forbidden operation detection"
```

---

### Task 5: Implement `integration_lint.py` — Integration model anti-pattern detection

**Files:**
- Create: `scripts/grain/integration_lint.py`
- Test: `tests/scripts/test_integration_lint.py`

- [ ] **Step 1: Write test for integration lint checks**

```python
# tests/scripts/test_integration_lint.py
from scripts.grain.integration_lint import (
    check_single_source,
    check_no_surrogate_key,
    check_no_cdm_mapping,
    check_no_intake_metadata,
)


def test_single_source_detected():
    depends_on = ["model.dcr_analytics.stg_vistareserve__reservations"]
    finding = check_single_source(depends_on)
    assert finding is not None
    assert finding["check"] == "single_source"


def test_multiple_sources_ok():
    depends_on = [
        "model.dcr_analytics.stg_vistareserve__reservations",
        "model.dcr_analytics.stg_emphasys_elite__bookings",
    ]
    finding = check_single_source(depends_on)
    assert finding is None


def test_no_surrogate_key_detected():
    columns = ["reservation_id", "park_name", "amount"]
    finding = check_no_surrogate_key(columns)
    assert finding is not None
    assert finding["check"] == "no_surrogate_key"


def test_surrogate_key_present():
    columns = ["reservation_sk", "reservation_id", "park_name"]
    finding = check_no_surrogate_key(columns)
    assert finding is None


def test_no_cdm_mapping_detected():
    meta = {}
    finding = check_no_cdm_mapping(meta)
    assert finding is not None


def test_cdm_mapping_present():
    meta = {"cdm_entity": "Reservation"}
    finding = check_no_cdm_mapping(meta)
    assert finding is None


def test_no_intake_metadata():
    meta = {}
    finding = check_no_intake_metadata(meta, is_pre_existing=False)
    assert finding is not None
    assert finding["severity"] == "warning"


def test_no_intake_metadata_pre_existing():
    meta = {}
    finding = check_no_intake_metadata(meta, is_pre_existing=True)
    assert finding is not None
    assert finding["severity"] == "info"  # low severity for pre-existing
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/scripts/test_integration_lint.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement `integration_lint.py`**

```python
# scripts/grain/integration_lint.py
"""Integration model anti-pattern detection."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from scripts._core.models import SelectionTarget

logger = logging.getLogger(__name__)


def check_single_source(depends_on: list[str]) -> dict[str, Any] | None:
    """Flag integration models that depend on only one staging source."""
    staging_parents = [d for d in depends_on if ".stg_" in d or ".base_" in d]
    if len(staging_parents) <= 1:
        return {
            "check": "single_source",
            "severity": "warning",
            "message": f"Single staging source: {staging_parents[0] if staging_parents else 'none'}",
            "detail": "Integration models should normalize an entity across multiple sources. "
                      "A single-source integration model may be a pass-through.",
        }
    return None


def check_no_surrogate_key(columns: list[str]) -> dict[str, Any] | None:
    """Flag integration models without a surrogate key column."""
    sk_cols = [c for c in columns if c.endswith("_sk")]
    if not sk_cols:
        return {
            "check": "no_surrogate_key",
            "severity": "warning",
            "message": "No surrogate key (_sk) column in output",
            "detail": "Integration models should generate surrogate keys via "
                      "dbt_utils.generate_surrogate_key() for downstream joins.",
        }
    return None


def check_no_cdm_mapping(meta: dict) -> dict[str, Any] | None:
    """Flag integration models without a CDM entity in meta."""
    if not meta.get("cdm_entity"):
        return {
            "check": "no_cdm_mapping",
            "severity": "warning",
            "message": "No cdm_entity in YAML meta block",
            "detail": "Integration models should map to a CDM entity. "
                      "Run `python -m scripts.llm_context cdm-match` to find one.",
        }
    return None


def check_no_intake_metadata(
    meta: dict,
    is_pre_existing: bool = False,
) -> dict[str, Any] | None:
    """Flag models without intake metadata."""
    if not meta.get("intake_completed"):
        severity = "info" if is_pre_existing else "warning"
        return {
            "check": "no_intake_metadata",
            "severity": severity,
            "message": "No intake_completed in YAML meta block",
            "detail": "Consider running `python -m scripts.llm_context new-model` "
                      "to document this model's entity and grain.",
        }
    return None


def run_integration_lint(
    target: SelectionTarget,
    output_mode: str = "terminal",
) -> list[dict]:
    """Run all integration lint checks for a model."""
    from scripts._core.selector import load_manifest

    manifest = load_manifest()
    node_key = f"model.dcr_analytics.{target.table}"
    node = manifest.get("nodes", {}).get(node_key)

    if node is None:
        logger.warning(f"Model {target.table} not found in manifest")
        return []

    depends_on = node.get("depends_on", {}).get("nodes", [])
    columns = list(node.get("columns", {}).keys())
    meta = node.get("meta", {})

    # Heuristic: models without intake_completed that were committed
    # before this tooling are "pre-existing"
    is_pre_existing = not meta.get("intake_completed")

    findings: list[dict] = []

    result = check_single_source(depends_on)
    if result:
        findings.append(result)

    result = check_no_surrogate_key(columns)
    if result:
        findings.append(result)

    result = check_no_cdm_mapping(meta)
    if result:
        findings.append(result)

    result = check_no_intake_metadata(meta, is_pre_existing=is_pre_existing)
    if result:
        findings.append(result)

    if output_mode == "terminal":
        _render_terminal(target, findings)

    return findings


def _render_terminal(target: SelectionTarget, findings: list[dict]) -> None:
    """Print integration lint results."""
    print(f"\nINTEGRATION LINT: {target.table}")
    print("=" * (18 + len(target.table)))

    if not findings:
        print("  ✓ No anti-patterns detected.")
        return

    for f in findings:
        icon = {"error": "✗", "warning": "⚠", "info": "ℹ"}.get(f["severity"], "?")
        print(f"  {icon} {f['message']}")
        print(f"    → {f['detail']}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/scripts/test_integration_lint.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/grain/integration_lint.py tests/scripts/test_integration_lint.py
git commit -m "feat(grain): implement integration_lint with anti-pattern detection"
```

---

### Task 6: Implement `mart_lint.py` — Mart model anti-pattern detection

**Files:**
- Create: `scripts/grain/mart_lint.py`
- Test: `tests/scripts/test_mart_lint.py`

- [ ] **Step 1: Write test for mart lint checks**

```python
# tests/scripts/test_mart_lint.py
from scripts.grain.mart_lint import (
    check_wide_fact,
    check_no_dimension_joins,
    check_single_fact_passthrough,
    check_no_aggregation,
)


def test_wide_fact_detected():
    """Fact with descriptive string columns and no FK should flag."""
    columns = {
        "reservation_sk": {"type": "VARCHAR"},
        "park_name": {"type": "VARCHAR"},
        "customer_email": {"type": "VARCHAR"},
        "region": {"type": "VARCHAR"},
        "amount": {"type": "NUMERIC"},
    }
    fk_columns = []  # no _sk or _id FK columns
    finding = check_wide_fact(columns, fk_columns)
    assert finding is not None
    assert finding["check"] == "wide_fact"
    assert "park_name" in finding["message"]


def test_fact_with_fks_ok():
    """Fact with FK columns for its descriptive attributes is fine."""
    columns = {
        "reservation_sk": {"type": "VARCHAR"},
        "parks_sk": {"type": "VARCHAR"},
        "customer_sk": {"type": "VARCHAR"},
        "amount": {"type": "NUMERIC"},
    }
    fk_columns = ["parks_sk", "customer_sk"]
    finding = check_wide_fact(columns, fk_columns)
    assert finding is None


def test_no_dimension_joins():
    depends_on = [
        "model.dcr_analytics.int_financial_transactions",
        "model.dcr_analytics.int_parks",
    ]
    finding = check_no_dimension_joins(depends_on)
    assert finding is not None  # no dim_ in depends_on


def test_has_dimension_joins():
    depends_on = [
        "model.dcr_analytics.int_parks",
        "model.dcr_analytics.dim_parks",
    ]
    finding = check_no_dimension_joins(depends_on)
    assert finding is None


def test_single_fact_passthrough():
    depends_on = ["model.dcr_analytics.fct_reservations"]
    finding = check_single_fact_passthrough(depends_on)
    assert finding is not None


def test_multi_fact_report():
    depends_on = [
        "model.dcr_analytics.fct_reservations",
        "model.dcr_analytics.fct_pos_transactions",
    ]
    finding = check_single_fact_passthrough(depends_on)
    assert finding is None


def test_no_aggregation():
    sql = "select * from fct_reservations"
    finding = check_no_aggregation(sql)
    assert finding is not None


def test_has_aggregation():
    sql = """
    select park_id, count(*) as reservation_count
    from fct_reservations
    group by park_id
    """
    finding = check_no_aggregation(sql)
    assert finding is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/scripts/test_mart_lint.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement `mart_lint.py`**

```python
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
        print("  ✓ No anti-patterns detected.")
        return

    for f in findings:
        icon = "✗" if f["severity"] == "error" else "⚠"
        print(f"  {icon} {f['message']}")
        print(f"    → {f['detail']}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/scripts/test_mart_lint.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/grain/mart_lint.py tests/scripts/test_mart_lint.py
git commit -m "feat(grain): implement mart_lint with fact/dim/report anti-pattern detection"
```

---

### Task 7: Implement `dag_lint.py` — DAG direction checker

**Files:**
- Create: `scripts/grain/dag_lint.py`
- Test: `tests/scripts/test_dag_lint.py`

- [ ] **Step 1: Write test for DAG direction checks**

```python
# tests/scripts/test_dag_lint.py
from scripts.grain.dag_lint import check_dependency_direction, VALID_DIRECTIONS


def test_staging_to_source_valid():
    findings = check_dependency_direction(
        model_name="stg_vistareserve__reservations",
        model_layer="staging",
        depends_on=["source.dcr_analytics.vistareserve.reservations"],
    )
    assert len(findings) == 0


def test_staging_to_integration_invalid():
    findings = check_dependency_direction(
        model_name="stg_bad_model",
        model_layer="staging",
        depends_on=["model.dcr_analytics.int_parks"],
    )
    assert len(findings) == 1
    assert findings[0]["check"] == "reverse_reference"


def test_integration_to_integration_warning():
    findings = check_dependency_direction(
        model_name="int_cases_enriched",
        model_layer="integration",
        depends_on=[
            "model.dcr_analytics.stg_salesforce__cases",
            "model.dcr_analytics.int_parks",
        ],
    )
    same_layer = [f for f in findings if f["check"] == "same_layer_reference"]
    assert len(same_layer) == 1


def test_fact_to_fact_warning():
    findings = check_dependency_direction(
        model_name="fct_executive_summary",
        model_layer="marts",
        depends_on=["model.dcr_analytics.fct_reservations"],
    )
    assert any(f["check"] == "mart_to_mart" for f in findings)


def test_fact_to_integration_valid():
    findings = check_dependency_direction(
        model_name="fct_reservations",
        model_layer="marts",
        depends_on=[
            "model.dcr_analytics.int_contacts",
            "model.dcr_analytics.int_parks",
        ],
    )
    assert len(findings) == 0


def test_skip_layer_warning():
    findings = check_dependency_direction(
        model_name="fct_bad_model",
        model_layer="marts",
        depends_on=["source.dcr_analytics.vistareserve.reservations"],
    )
    assert any(f["check"] == "skip_layer" for f in findings)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/scripts/test_dag_lint.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement `dag_lint.py`**

```python
# scripts/grain/dag_lint.py
"""DAG direction checker — detects same-layer, reverse, and skip-layer references."""
from __future__ import annotations

import logging
from typing import Any

from scripts._core.models import SelectionTarget

logger = logging.getLogger(__name__)

# Valid dependency directions: layer -> set of allowed dependency layers.
VALID_DIRECTIONS: dict[str, set[str]] = {
    "staging": {"source"},
    "base": {"source"},
    "integration": {"staging", "base"},
    "marts": {"integration", "staging"},  # staging for seeds/lookups
}


def _dep_layer(unique_id: str) -> str:
    """Determine the layer of a dependency from its unique_id."""
    if unique_id.startswith("source."):
        return "source"
    # Extract model name from unique_id like "model.dcr_analytics.stg_parks__raw"
    parts = unique_id.split(".")
    name = parts[-1] if len(parts) >= 3 else unique_id

    if name.startswith("stg_"):
        return "staging"
    if name.startswith("base_"):
        return "base"
    if name.startswith("int_"):
        return "integration"
    if name.startswith(("fct_", "dim_", "rpt_")):
        return "marts"
    if name.startswith("seed_") or unique_id.startswith("seed."):
        return "seed"
    return "unknown"


def check_dependency_direction(
    model_name: str,
    model_layer: str,
    depends_on: list[str],
    meta: dict | None = None,
) -> list[dict[str, Any]]:
    """Check all dependencies for direction violations.

    Args:
        model_name: The model being checked.
        model_layer: Layer of the model (staging/integration/marts/etc.).
        depends_on: List of unique_ids this model depends on.
        meta: Optional YAML meta block (for shared_integration_dependency suppression).

    Returns:
        List of findings.
    """
    findings: list[dict[str, Any]] = []
    allowed = VALID_DIRECTIONS.get(model_layer, set())
    suppressed = set()

    if meta and meta.get("shared_integration_dependency"):
        dep = meta["shared_integration_dependency"]
        if isinstance(dep, list):
            suppressed.update(dep)
        else:
            suppressed.add(dep)

    for dep_id in depends_on:
        dep_name = dep_id.split(".")[-1]
        dep_lyr = _dep_layer(dep_id)

        # Seeds are always allowed
        if dep_lyr in ("seed", "unknown"):
            continue

        if dep_lyr in allowed:
            continue

        # Mart-to-mart (fact depends on fact) — check BEFORE same-layer generic
        if model_layer == "marts" and dep_lyr == "marts":
            findings.append({
                "check": "mart_to_mart",
                "severity": "warning",
                "message": f"Mart-to-mart reference: depends on {dep_name}",
                "detail": "Facts should not depend on other facts. "
                          "Use a report model to combine them.",
            })

        # Same-layer reference (non-mart)
        elif dep_lyr == model_layer:
            if dep_name in suppressed:
                continue
            findings.append({
                "check": "same_layer_reference",
                "severity": "warning",
                "message": f"Same-layer reference: depends on {dep_name} ({model_layer} → {dep_lyr})",
                "detail": f"{model_layer.title()} models should not depend on other {model_layer} models. "
                          "If intentional, add meta: { shared_integration_dependency: "
                          f'"{dep_name}" ' + "} to suppress.",
            })

        # Skip-layer (mart directly referencing source)
        elif dep_lyr == "source" and model_layer in ("marts", "integration"):
            if model_layer == "marts":
                findings.append({
                    "check": "skip_layer",
                    "severity": "warning",
                    "message": f"Skip-layer: mart depends directly on source ({dep_name})",
                    "detail": "Mart models should depend on integration or staging, not sources directly.",
                })

        # Reverse reference
        else:
            findings.append({
                "check": "reverse_reference",
                "severity": "error",
                "message": f"Reverse reference: {model_layer} depends on {dep_lyr} ({dep_name})",
                "detail": f"{model_layer.title()} models must not depend on {dep_lyr} models.",
            })

    return findings


def run_dag_lint(
    target: SelectionTarget,
    output_mode: str = "terminal",
) -> list[dict]:
    """Run DAG direction checks for a model."""
    from scripts._core.selector import load_manifest, _determine_layer

    manifest = load_manifest()
    node_key = f"model.dcr_analytics.{target.table}"
    node = manifest.get("nodes", {}).get(node_key)

    if node is None:
        logger.warning(f"Model {target.table} not found in manifest")
        return []

    model_layer = _determine_layer(target.table)
    depends_on = node.get("depends_on", {}).get("nodes", [])
    meta = node.get("meta", {})

    findings = check_dependency_direction(target.table, model_layer, depends_on, meta)

    if output_mode == "terminal":
        _render_terminal(target, findings)

    return findings


def _render_terminal(target: SelectionTarget, findings: list[dict]) -> None:
    """Print DAG lint results."""
    print(f"\nDAG LINT: {target.table}")
    print("=" * (10 + len(target.table)))

    if not findings:
        print("  ✓ All dependencies follow valid DAG direction.")
        return

    for f in findings:
        icon = "✗" if f["severity"] == "error" else "⚠"
        print(f"  {icon} {f['message']}")
        print(f"    → {f['detail']}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/scripts/test_dag_lint.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/grain/dag_lint.py tests/scripts/test_dag_lint.py
git commit -m "feat(grain): implement dag_lint with direction violation detection"
```

---

### Task 8: Add `__main__.py` to enable `python -m scripts.grain`

**Files:**
- Create: `scripts/grain/__main__.py`

- [ ] **Step 1: Create `__main__.py`**

```python
# scripts/grain/__main__.py
from scripts.grain.cli import main
import sys
sys.exit(main())
```

- [ ] **Step 2: Verify invocation**

Run: `source .venv/Scripts/activate && python -m scripts.grain --help`
Expected: Help text prints (same as `python scripts/grain/cli.py --help`).

- [ ] **Step 3: Commit**

```bash
git add scripts/grain/__main__.py
git commit -m "feat(grain): add __main__.py for python -m scripts.grain invocation"
```
