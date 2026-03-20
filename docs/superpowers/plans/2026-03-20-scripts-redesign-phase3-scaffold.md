# Phase 3: `scaffold/` — Test and Model Scaffolding — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `scaffold/` package that generates missing YAML tests, integration/mart model skeletons, and source freshness configuration — reducing boilerplate and guiding analysts toward correct patterns.

**Architecture:** Four modules behind a CLI with subcommands. `test_scaffold` analyzes a model's data and YAML to suggest missing tests with seed-driven lookup detection. `integration_scaffold` and `mart_scaffold` generate SQL + YAML skeletons from CDM metadata and intake answers. `source_freshness_scaffold` generates freshness YAML blocks with heuristic thresholds.

**Tech Stack:** Python 3.10+, sqlglot (CASE detection), `_core/selector` and `_core/connectors` (dbt/warehouse), CDM seed CSVs

**Spec:** `docs/superpowers/specs/2026-03-20-scripts-redesign-design.md` (section: "Phase 3: `scaffold/`")

**Depends on:** Phase 0 (`_core/`), Phase 1 (`grain/` — sqlglot for CASE detection), Phase 2 (`llm_context/` — CDM seeds)

---

### Task 1: Create `scaffold/` package structure and CLI

**Files:**
- Create: `scripts/scaffold/__init__.py`
- Create: `scripts/scaffold/cli.py`
- Test: `tests/scripts/test_scaffold_cli.py`

- [ ] **Step 1: Write test for CLI subcommand parsing**

```python
# tests/scripts/test_scaffold_cli.py
from scripts.scaffold.cli import parse_args


def test_parse_tests():
    args = parse_args(["tests", "--select", "stg_vistareserve__reservations"])
    assert args.subcommand == "tests"
    assert args.select == "stg_vistareserve__reservations"
    assert args.apply is False


def test_parse_tests_apply():
    args = parse_args(["tests", "--select", "stg_test", "--apply"])
    assert args.apply is True


def test_parse_integration():
    args = parse_args([
        "integration", "--entity", "Request",
        "--sources", "stg_a", "stg_b", "--key", "request_id",
    ])
    assert args.subcommand == "integration"
    assert args.entity == "Request"
    assert args.sources == ["stg_a", "stg_b"]


def test_parse_fact():
    args = parse_args([
        "fact", "--name", "fct_permits",
        "--grain", "one row per permit",
        "--dimensions", "dim_parks", "dim_customers",
    ])
    assert args.subcommand == "fact"
    assert args.name == "fct_permits"


def test_parse_freshness():
    args = parse_args(["freshness", "--select", "source:peoplefirst"])
    assert args.subcommand == "freshness"
    assert args.apply is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/scripts/test_scaffold_cli.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement CLI**

```python
# scripts/scaffold/__init__.py
```

```python
# scripts/scaffold/cli.py
"""Test and model scaffolding.

Usage:
    python -m scripts.scaffold tests --select stg_vistareserve__reservations
    python -m scripts.scaffold tests --select stg_test --apply
    python -m scripts.scaffold integration --entity Request --sources stg_a stg_b --key request_id
    python -m scripts.scaffold fact --name fct_permits --grain "one row per permit" --dimensions dim_parks
    python -m scripts.scaffold freshness --select source:peoplefirst
"""
from __future__ import annotations

import argparse
import logging
import sys


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test and model scaffolding.")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # tests
    sub_tests = subparsers.add_parser("tests", help="Generate missing YAML tests")
    sub_tests.add_argument("--select", "-s", required=True, help="dbt model selector")
    sub_tests.add_argument("--apply", action="store_true", help="Write into YAML file")

    # integration
    sub_int = subparsers.add_parser("integration", help="Generate integration model skeleton")
    sub_int.add_argument("--entity", required=True, help="CDM entity name")
    sub_int.add_argument("--sources", nargs="+", required=True, help="Source model names")
    sub_int.add_argument("--key", required=True, help="Primary key column")

    # fact
    sub_fact = subparsers.add_parser("fact", help="Generate fact model skeleton")
    sub_fact.add_argument("--name", required=True, help="Model name")
    sub_fact.add_argument("--grain", required=True, help="Grain description")
    sub_fact.add_argument("--dimensions", nargs="+", default=[], help="Dimension models to join")
    sub_fact.add_argument("--measures", default="", help="Comma-separated measure columns")

    # dimension
    sub_dim = subparsers.add_parser("dimension", help="Generate dimension model skeleton")
    sub_dim.add_argument("--name", required=True, help="Model name")
    sub_dim.add_argument("--grain", required=True, help="Grain description")
    sub_dim.add_argument("--key", required=True, help="Natural key column")

    # report
    sub_rpt = subparsers.add_parser("report", help="Generate report model skeleton")
    sub_rpt.add_argument("--name", required=True, help="Model name")
    sub_rpt.add_argument("--facts", nargs="+", required=True, help="Fact models to combine")
    sub_rpt.add_argument("--grain", required=True, help="Aggregation grain")

    # freshness
    sub_fresh = subparsers.add_parser("freshness", help="Generate source freshness YAML")
    sub_fresh.add_argument("--select", "-s", required=True, help="dbt source selector")
    sub_fresh.add_argument("--apply", action="store_true", help="Write into source YAML")

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

    if args.subcommand == "tests":
        from scripts.scaffold.test_scaffold import run_test_scaffold
        return run_test_scaffold(args.select, apply_changes=args.apply)
    elif args.subcommand == "integration":
        from scripts.scaffold.integration_scaffold import run_integration_scaffold
        return run_integration_scaffold(args.entity, args.sources, args.key)
    elif args.subcommand in ("fact", "dimension", "report"):
        from scripts.scaffold.mart_scaffold import run_mart_scaffold
        return run_mart_scaffold(args)
    elif args.subcommand == "freshness":
        from scripts.scaffold.source_freshness_scaffold import run_freshness_scaffold
        return run_freshness_scaffold(args.select, apply_changes=args.apply)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/scripts/test_scaffold_cli.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/scaffold/ tests/scripts/test_scaffold_cli.py
git commit -m "feat(scaffold): create package structure and CLI with subcommands"
```

Also create `scripts/scaffold/__main__.py`:
```python
# scripts/scaffold/__main__.py
from scripts.scaffold.cli import main
import sys
sys.exit(main())
```
```bash
git add scripts/scaffold/__main__.py
git commit -m "feat(scaffold): add __main__.py for python -m scripts.scaffold"
```

---

### Task 2: Implement `test_scaffold.py` — Generate missing YAML tests

**Files:**
- Create: `scripts/scaffold/test_scaffold.py`
- Test: `tests/scripts/test_test_scaffold.py`

- [ ] **Step 1: Write test for test suggestion logic**

```python
# tests/scripts/test_test_scaffold.py
import pandas as pd
from scripts.scaffold.test_scaffold import (
    suggest_tests_for_column,
    detect_hardcoded_case,
)


def test_suggest_tests_id_column():
    """_id columns should get not_null + unique."""
    suggestions = suggest_tests_for_column(
        col_name="reservation_id",
        dtype="VARCHAR",
        series=pd.Series(["R001", "R002", "R003"]),
        existing_tests=[],
    )
    assert any(s["test"] == "not_null" for s in suggestions)
    assert any(s["test"] == "unique" for s in suggestions)


def test_suggest_tests_sk_column():
    """_sk columns should get not_null + unique."""
    suggestions = suggest_tests_for_column(
        col_name="parks_sk",
        dtype="VARCHAR",
        series=pd.Series(["sk1", "sk2", "sk3"]),
        existing_tests=[],
    )
    assert any(s["test"] == "not_null" for s in suggestions)
    assert any(s["test"] == "unique" for s in suggestions)


def test_suggest_tests_low_cardinality():
    """Low cardinality categorical columns get accepted_values."""
    suggestions = suggest_tests_for_column(
        col_name="status",
        dtype="VARCHAR",
        series=pd.Series(["active", "inactive", "active", "pending"]),
        existing_tests=[],
    )
    assert any(s["test"] == "accepted_values" for s in suggestions)


def test_suggest_tests_already_covered():
    """Don't suggest tests that already exist."""
    suggestions = suggest_tests_for_column(
        col_name="reservation_id",
        dtype="VARCHAR",
        series=pd.Series(["R001", "R002"]),
        existing_tests=["not_null", "unique"],
    )
    assert len(suggestions) == 0


def test_detect_hardcoded_case():
    sql = """
    select
        case when type = 'A' then 'Active'
             when type = 'I' then 'Inactive'
             when type = 'P' then 'Pending' end as status_label
    from source
    """
    cases = detect_hardcoded_case(sql)
    assert len(cases) >= 1
    assert cases[0]["column"] == "status_label"
    assert "A" in str(cases[0]["values"])


def test_detect_no_case():
    sql = "select id, name from source"
    cases = detect_hardcoded_case(sql)
    assert len(cases) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/scripts/test_test_scaffold.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement `test_scaffold.py`**

```python
# scripts/scaffold/test_scaffold.py
"""Generate missing YAML tests for a dbt model."""
from __future__ import annotations

import logging
from typing import Any

import pandas as pd
import sqlglot
from sqlglot import exp

logger = logging.getLogger(__name__)

# Max distinct values to consider "low cardinality"
LOW_CARDINALITY_THRESHOLD = 15


def suggest_tests_for_column(
    col_name: str,
    dtype: str,
    series: pd.Series,
    existing_tests: list[str],
) -> list[dict[str, Any]]:
    """Suggest tests for a column based on name patterns and data characteristics.

    Returns list of {"test": str, "config": dict, "rule_id": str, "reason": str}
    """
    suggestions: list[dict[str, Any]] = []

    # ID / SK columns → not_null + unique
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

    # Date columns → not_null where appropriate
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

    # Low cardinality categorical → accepted_values
    if dtype.upper() in ("VARCHAR", "TEXT", "STRING"):
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

    Returns list of {"column": str, "values": list, "mappings": dict}
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
            values = []
            mappings = {}

            for if_node in case_node.find_all(exp.If):
                cond = if_node.args.get("this")
                true_val = if_node.args.get("true")
                if cond and true_val:
                    # Extract literal values
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


def run_test_scaffold(
    selector: str,
    apply_changes: bool = False,
    count_only: bool = False,
) -> int:
    """Full test scaffolding pipeline.

    Args:
        selector: dbt model selector
        apply_changes: if True, write into YAML file (prints to stdout for manual paste when False)
        count_only: if True, return count of missing tests as int (for preflight)
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

        # Extract existing tests from manifest columns
        existing: dict[str, list[str]] = {}
        for col_name, col_info in node.get("columns", {}).items():
            existing[col_name] = [
                t if isinstance(t, str) else list(t.keys())[0]
                for t in col_info.get("constraints", []) + col_info.get("tests", [])
            ]

        # Query data sample for per-column analysis
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

        all_suggestions: list[dict] = []
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

        # Detect hardcoded CASE statements
        from scripts.grain.join_analysis import _find_compiled_sql
        compiled_path = _find_compiled_sql(target.table)
        case_findings: list[dict] = []
        if compiled_path:
            sql = compiled_path.read_text(encoding="utf-8")
            case_findings = detect_hardcoded_case(sql)

        print(f"\nTEST SCAFFOLD: {target.table}")
        print("=" * (16 + len(target.table)))

        if not all_suggestions and not case_findings:
            print("  ✓ No missing tests detected.")
            continue

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
            print(f"\n# ⚠ Hardcoded CASE on column '{case['column']}' — consider seed:")
            for k, v in case.get("mappings", {}).items():
                print(f"#   {k} → {v}")
            print(f"# See spec Phase 3 for seed-driven lookup suggestion template.")

    if count_only:
        return total_suggestions

    return 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/scripts/test_test_scaffold.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/scaffold/test_scaffold.py tests/scripts/test_test_scaffold.py
git commit -m "feat(scaffold): implement test_scaffold with suggestion logic and CASE detection"
```

---

### Task 3: Implement `integration_scaffold.py` — Generate integration model skeleton

**Files:**
- Create: `scripts/scaffold/integration_scaffold.py`
- Test: `tests/scripts/test_integration_scaffold.py`

- [ ] **Step 1: Write test for integration skeleton generation**

```python
# tests/scripts/test_integration_scaffold.py
from scripts.scaffold.integration_scaffold import generate_integration_sql, generate_integration_yaml


def test_generate_integration_sql():
    sql = generate_integration_sql(
        model_name="int_grants",
        entity="Grant",
        sources=["stg_grantwatch__applications", "stg_grantwatch__amendments"],
        key_column="application_id",
    )
    assert "grants_sk" in sql
    assert "generate_surrogate_key" in sql
    assert "stg_grantwatch__applications" in sql
    assert "stg_grantwatch__amendments" in sql
    assert "union all" in sql.lower()


def test_generate_integration_sql_single_source():
    sql = generate_integration_sql(
        model_name="int_permits",
        entity="Permit",
        sources=["stg_vistareserve__permits"],
        key_column="permit_id",
    )
    assert "permits_sk" in sql
    assert "union all" not in sql.lower()


def test_generate_integration_yaml():
    yaml_str = generate_integration_yaml(
        model_name="int_grants",
        entity="Grant",
        grain="one row per grant application",
        key_column="application_id",
    )
    assert "int_grants" in yaml_str
    assert "grants_sk" in yaml_str
    assert "cdm_entity: Grant" in yaml_str
    assert "not_null" in yaml_str
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/scripts/test_integration_scaffold.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement `integration_scaffold.py`**

```python
# scripts/scaffold/integration_scaffold.py
"""Generate integration model SQL + YAML skeleton."""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def _sk_name(model_name: str) -> str:
    """Derive surrogate key column name from model name (int_parks → parks_sk)."""
    entity = model_name.removeprefix("int_")
    return f"{entity}_sk"


def generate_integration_sql(
    model_name: str,
    entity: str,
    sources: list[str],
    key_column: str,
) -> str:
    """Generate integration model SQL with CTE-per-source and surrogate key."""
    sk = _sk_name(model_name)
    lines = [f"-- Integration model: {model_name}"]
    lines.append(f"-- CDM entity: {entity}")
    lines.append(f"-- Grain: one row per {entity.lower()}")
    lines.append("")
    lines.append("with")
    lines.append("")

    cte_names = []
    for i, source in enumerate(sources):
        cte_name = source.split("__")[-1] if "__" in source else source.removeprefix("stg_")
        cte_names.append(cte_name)
        lines.append(f"{cte_name} as (")
        lines.append(f"    select")
        lines.append(f"        {key_column},")
        lines.append(f"        -- TODO: map source columns to CDM entity columns")
        lines.append(f"        '{source}' as _source_model")
        lines.append(f"    from {{{{ ref('{source}') }}}}")
        lines.append(f"),")
        lines.append("")

    if len(sources) > 1:
        lines.append("unioned as (")
        for i, cte_name in enumerate(cte_names):
            if i > 0:
                lines.append("    union all")
            lines.append(f"    select * from {cte_name}")
        lines.append("),")
        lines.append("")
        final_cte = "unioned"
    else:
        final_cte = cte_names[0]

    lines.append("final as (")
    lines.append(f"    select")
    lines.append(f"        {{{{ dbt_utils.generate_surrogate_key(['{key_column}', '_source_model']) }}}} as {sk},")
    lines.append(f"        *")
    lines.append(f"    from {final_cte}")
    lines.append(")")
    lines.append("")
    lines.append("select * from final")
    lines.append("")

    return "\n".join(lines)


def generate_integration_yaml(
    model_name: str,
    entity: str,
    grain: str,
    key_column: str,
) -> str:
    """Generate YAML properties for the integration model."""
    sk = _sk_name(model_name)

    return f"""  - name: {model_name}
    description: >
      {entity} integration model. {grain}.
    meta:
      cdm_entity: {entity}
      intake_completed: true
      grain: "{grain}"
    columns:
      - name: {sk}
        description: "Surrogate key for {entity.lower()} entity"
        tests:
          - unique
          - not_null
      - name: {key_column}
        description: "Natural key from source system"
        tests:
          - not_null
"""


def run_integration_scaffold(
    entity: str,
    sources: list[str],
    key_column: str,
) -> int:
    """Generate and output integration model files."""
    model_name = f"int_{entity.lower()}s"
    sql = generate_integration_sql(model_name, entity, sources, key_column)
    yaml_str = generate_integration_yaml(model_name, entity, f"one row per {entity.lower()}", key_column)

    out_dir = Path("tmp/scaffold")
    out_dir.mkdir(parents=True, exist_ok=True)

    sql_path = out_dir / f"{model_name}.sql"
    sql_path.write_text(sql, encoding="utf-8")

    yaml_path = out_dir / f"{model_name}.yml"
    yaml_path.write_text(yaml_str, encoding="utf-8")

    print(f"Generated: {sql_path}")
    print(f"Generated: {yaml_path}")
    return 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/scripts/test_integration_scaffold.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/scaffold/integration_scaffold.py tests/scripts/test_integration_scaffold.py
git commit -m "feat(scaffold): implement integration_scaffold with SQL and YAML generation"
```

---

### Task 4: Implement `mart_scaffold.py` — Generate fact/dimension/report skeletons

**Files:**
- Create: `scripts/scaffold/mart_scaffold.py`
- Test: `tests/scripts/test_mart_scaffold.py`

- [ ] **Step 1: Write test for mart skeleton generation**

```python
# tests/scripts/test_mart_scaffold.py
from scripts.scaffold.mart_scaffold import generate_fact_sql, generate_dimension_sql, generate_report_sql


def test_generate_fact_sql():
    sql = generate_fact_sql(
        name="fct_permits",
        grain="one row per permit application",
        dimensions=["dim_parks", "dim_customers", "dim_date"],
        measures=["permit_fee", "processing_days"],
    )
    assert "parks_sk" in sql
    assert "customer" in sql.lower()
    assert "date_key" in sql
    assert "permit_fee" in sql
    # Should not have descriptive attributes
    assert "Descriptive attributes come from dimensions" in sql


def test_generate_dimension_sql():
    sql = generate_dimension_sql(
        name="dim_applicants",
        grain="one row per applicant organization",
        key="applicant_id",
    )
    assert "applicants_sk" in sql
    assert "generate_surrogate_key" in sql
    assert "applicant_id" in sql


def test_generate_report_sql():
    sql = generate_report_sql(
        name="rpt_park_revenue_summary",
        facts=["fct_reservations", "fct_pos_transactions"],
        grain="one row per park per month",
    )
    assert "fct_reservations" in sql
    assert "fct_pos_transactions" in sql
    assert "group by" in sql.lower()
    assert "combines" in sql.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/scripts/test_mart_scaffold.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement `mart_scaffold.py`**

```python
# scripts/scaffold/mart_scaffold.py
"""Generate fact, dimension, and report model skeletons."""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def _dim_sk(dim_name: str) -> str:
    """Derive FK column name from dimension name (dim_parks → parks_sk)."""
    entity = dim_name.removeprefix("dim_")
    return f"{entity}_sk"


def generate_fact_sql(
    name: str,
    grain: str,
    dimensions: list[str],
    measures: list[str],
) -> str:
    """Generate fact model SQL skeleton."""
    lines = [
        f"-- Fact model: {name}",
        f"-- Grain: {grain}",
        f"-- Descriptive attributes come from dimensions, not from this table.",
        "",
        "with",
        "",
    ]

    # Source CTE placeholder
    lines.append("source as (")
    lines.append("    select")
    lines.append("        -- TODO: select from integration model(s)")
    lines.append("        *")
    lines.append("    from {{ ref('TODO_integration_model') }}")
    lines.append("),")
    lines.append("")

    # Final select with dimension FKs and measures only
    lines.append("final as (")
    lines.append("    select")

    # Dimension FK columns
    for dim in dimensions:
        if dim == "dim_date":
            lines.append("        date_key,")
        else:
            lines.append(f"        {_dim_sk(dim)},")

    # Measures
    for measure in measures:
        lines.append(f"        {measure},")

    lines.append("        -- TODO: add remaining measures")
    lines.append("    from source")

    # Dimension joins
    for dim in dimensions:
        if dim == "dim_date":
            lines.append(f"    -- TODO: join to {{{{ ref('{dim}') }}}} on date_key")
        else:
            lines.append(f"    -- TODO: join to {{{{ ref('{dim}') }}}} on {_dim_sk(dim)}")

    lines.append(")")
    lines.append("")
    lines.append("select * from final")
    lines.append("")

    return "\n".join(lines)


def generate_dimension_sql(
    name: str,
    grain: str,
    key: str,
) -> str:
    """Generate dimension model SQL skeleton."""
    sk = name.removeprefix("dim_") + "_sk"

    return f"""-- Dimension model: {name}
-- Grain: {grain}

with

source as (
    select
        -- TODO: select from integration model
        *
    from {{{{ ref('TODO_integration_model') }}}}
),

final as (
    select
        {{{{ dbt_utils.generate_surrogate_key(['{key}']) }}}} as {sk},
        {key},
        -- TODO: add descriptive attributes
        -- TODO: add derived classifications (e.g., CASE WHEN ... END as size_tier)
    from source
)

select * from final
"""


def generate_report_sql(
    name: str,
    facts: list[str],
    grain: str,
) -> str:
    """Generate report model SQL skeleton."""
    lines = [
        f"-- Report model: {name}",
        f"-- Grain: {grain}",
        f"-- This report combines {len(facts)} fact table(s) at the {grain} grain.",
        f"-- If consuming a single fact without aggregation, consider connecting",
        f"-- your BI tool directly.",
        "",
        "with",
        "",
    ]

    # One CTE per fact with aggregation
    for fact in facts:
        cte_name = fact.removeprefix("fct_")
        lines.append(f"{cte_name} as (")
        lines.append(f"    select")
        lines.append(f"        -- TODO: group by columns for {grain} grain")
        lines.append(f"        -- TODO: aggregate measures (sum, count, avg)")
        lines.append(f"    from {{{{ ref('{fact}') }}}}")
        lines.append(f"    group by")
        lines.append(f"        -- TODO: group by keys")
        lines.append(f"        1")
        lines.append(f"),")
        lines.append("")

    # Final join
    cte_names = [f.removeprefix("fct_") for f in facts]
    lines.append("final as (")
    lines.append(f"    select *")
    lines.append(f"    from {cte_names[0]}")
    for cte in cte_names[1:]:
        lines.append(f"    -- TODO: join {cte} on shared grain columns")
        lines.append(f"    left join {cte} using (/* TODO: grain columns */)")
    lines.append(")")
    lines.append("")
    lines.append("select * from final")
    lines.append("")

    return "\n".join(lines)


def generate_mart_yaml(name: str, grain: str, model_type: str) -> str:
    """Generate YAML properties for a mart model."""
    sk = name.removeprefix("fct_").removeprefix("dim_").removeprefix("rpt_") + "_sk"
    return f"""  - name: {name}
    description: >
      {model_type.title()} model. {grain}.
    meta:
      model_type: {model_type}
      grain: "{grain}"
      intake_completed: true
    columns:
      - name: {sk}
        description: "Surrogate key"
        tests:
          - unique
          - not_null
"""


def run_mart_scaffold(args: argparse.Namespace) -> int:
    """Generate mart model SQL + YAML skeleton based on subcommand."""
    out_dir = Path("tmp/scaffold")
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.subcommand == "fact":
        measures = [m.strip() for m in args.measures.split(",") if m.strip()] if args.measures else []
        sql = generate_fact_sql(args.name, args.grain, args.dimensions, measures)
        yaml_str = generate_mart_yaml(args.name, args.grain, "fact")
    elif args.subcommand == "dimension":
        sql = generate_dimension_sql(args.name, args.grain, args.key)
        yaml_str = generate_mart_yaml(args.name, args.grain, "dimension")
    elif args.subcommand == "report":
        sql = generate_report_sql(args.name, args.facts, args.grain)
        yaml_str = generate_mart_yaml(args.name, args.grain, "report")
    else:
        return 1

    sql_path = out_dir / f"{args.name}.sql"
    sql_path.write_text(sql, encoding="utf-8")
    print(f"Generated SQL: {sql_path}")

    yaml_path = out_dir / f"{args.name}.yml"
    yaml_path.write_text(yaml_str, encoding="utf-8")
    print(f"Generated YAML: {yaml_path}")
    return 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/scripts/test_mart_scaffold.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/scaffold/mart_scaffold.py tests/scripts/test_mart_scaffold.py
git commit -m "feat(scaffold): implement mart_scaffold with fact/dimension/report generators"
```

---

### Task 5: Implement `source_freshness_scaffold.py` — Generate freshness YAML

**Files:**
- Create: `scripts/scaffold/source_freshness_scaffold.py`
- Test: `tests/scripts/test_freshness_scaffold.py`

- [ ] **Step 1: Write test for freshness heuristics**

```python
# tests/scripts/test_freshness_scaffold.py
from scripts.scaffold.source_freshness_scaffold import (
    classify_table_type,
    suggest_loaded_at_field,
    generate_freshness_block,
)


def test_classify_transactional():
    assert classify_table_type("transactions") == "transactional"
    assert classify_table_type("event_logs") == "transactional"
    assert classify_table_type("orders") == "transactional"


def test_classify_reference():
    assert classify_table_type("status_codes") == "reference"
    assert classify_table_type("type_mappings") == "reference"
    assert classify_table_type("categories") == "reference"


def test_classify_default():
    assert classify_table_type("employees") == "standard"
    assert classify_table_type("reservations") == "standard"


def test_suggest_loaded_at_field():
    columns = ["id", "name", "updated_at", "created_at"]
    field = suggest_loaded_at_field(columns)
    assert field == "updated_at"


def test_suggest_loaded_at_field_modified():
    columns = ["id", "modified_date", "status"]
    field = suggest_loaded_at_field(columns)
    assert field == "modified_date"


def test_suggest_loaded_at_field_none():
    columns = ["id", "name", "status"]
    field = suggest_loaded_at_field(columns)
    assert field is None


def test_generate_freshness_block():
    block = generate_freshness_block(
        table_name="employees",
        loaded_at_field="updated_at",
        table_type="standard",
    )
    assert "updated_at" in block
    assert "warn_after" in block
    assert "error_after" in block
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/scripts/test_freshness_scaffold.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement `source_freshness_scaffold.py`**

```python
# scripts/scaffold/source_freshness_scaffold.py
"""Generate source freshness YAML configuration."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Column name patterns that indicate a loaded_at timestamp.
LOADED_AT_PATTERNS = [
    "_loaded_at", "_updated_at", "_modified_at", "_created_at",
    "updated_date", "modified_date", "last_modified", "load_timestamp",
    "updated_at", "created_at", "modified_at",
]

# Table name keywords for classification.
TRANSACTIONAL_KEYWORDS = ("transaction", "event", "log", "order", "payment", "sale", "booking")
REFERENCE_KEYWORDS = ("type", "code", "category", "mapping", "lookup", "status_code")


def classify_table_type(table_name: str) -> str:
    """Classify a table as transactional, reference, or standard."""
    name_lower = table_name.lower()
    if any(kw in name_lower for kw in TRANSACTIONAL_KEYWORDS):
        return "transactional"
    if any(kw in name_lower for kw in REFERENCE_KEYWORDS):
        return "reference"
    return "standard"


def suggest_loaded_at_field(columns: list[str]) -> str | None:
    """Find the best candidate loaded_at_field from column names."""
    for pattern in LOADED_AT_PATTERNS:
        for col in columns:
            if col.lower().endswith(pattern) or col.lower() == pattern:
                return col
    return None


def generate_freshness_block(
    table_name: str,
    loaded_at_field: str,
    table_type: str = "standard",
) -> str:
    """Generate a YAML freshness block for one table."""
    thresholds = {
        "transactional": ("12", "hour", "24", "hour"),
        "reference": ("7", "day", "14", "day"),
        "standard": ("24", "hour", "48", "hour"),
    }
    warn_count, warn_period, error_count, error_period = thresholds.get(
        table_type, thresholds["standard"]
    )

    comment = ""
    if table_type == "reference":
        comment = "  # reference table — infrequent updates"
    elif table_type == "transactional":
        comment = "  # transactional — tighter threshold"

    return f"""      - name: {table_name}
        loaded_at_field: {loaded_at_field}
        freshness:
          warn_after: {{count: {warn_count}, period: {warn_period}}}{comment}
          error_after: {{count: {error_count}, period: {error_period}}}
          # Adjust based on this source's actual sync cadence"""


def run_freshness_scaffold(selector: str, apply_changes: bool = False) -> int:
    """Generate freshness YAML for a source.

    In dry-run mode (default): prints YAML to stdout.
    In --apply mode: finds the source YAML file and inserts the freshness blocks.
    """
    from scripts._core.selector import resolve_selector, load_manifest

    targets = resolve_selector(selector)
    manifest = load_manifest()
    generated_blocks: list[tuple[str, str]] = []  # (table_name, block)

    for target in targets:
        for key, node in manifest.get("sources", {}).items():
            if node.get("name") == target.table:
                columns = list(node.get("columns", {}).keys())
                loaded_at = suggest_loaded_at_field(columns)

                if loaded_at is None:
                    logger.warning(f"{target.table}: no candidate loaded_at_field found")
                    continue

                table_type = classify_table_type(target.table)
                block = generate_freshness_block(target.table, loaded_at, table_type)
                generated_blocks.append((target.table, block))

    if not apply_changes:
        print("# Suggested freshness configuration")
        print("# Generated by scaffold — review thresholds before committing\n")
        for _, block in generated_blocks:
            print(block)
            print()
        return 0

    # --apply mode: find and update source YAML files
    from pathlib import Path
    import re

    models_dir = Path("models")
    for table_name, block in generated_blocks:
        # Find the source YAML file containing this table
        yaml_files = list(models_dir.rglob("*.yml")) + list(models_dir.rglob("*.yaml"))
        for yaml_path in yaml_files:
            content = yaml_path.read_text(encoding="utf-8")
            if f"name: {table_name}" in content:
                # Inject freshness block after "name: <table_name>"
                pattern = rf"(      - name: {re.escape(table_name)}\n)"
                replacement = r"\1" + "\n".join(
                    f"        {line}" if line.strip() else line
                    for line in block.strip().split("\n")[1:]  # skip "- name: X" (already in file)
                ) + "\n"
                updated = re.sub(pattern, replacement, content, count=1)
                if updated != content:
                    yaml_path.write_text(updated, encoding="utf-8")
                    print(f"  Updated: {yaml_path}")
                    break
        else:
            print(f"  ⚠ No source YAML found for {table_name} — output to stdout:")
            print(block)

    return 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/scripts/test_freshness_scaffold.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/scaffold/source_freshness_scaffold.py tests/scripts/test_freshness_scaffold.py
git commit -m "feat(scaffold): implement source_freshness_scaffold with heuristic thresholds"
```
