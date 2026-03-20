# Phase 6: `profiler/` Refactor — Performance Fix and `_core/` Integration — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the profiler's migration to `_core/`, add two-tier profiling (quick SQL-based mode as default, deep ydata-profiling on request), add `llm` output mode, and remove the profiler's local connectors/renderers directories.

**Architecture:** Quick mode runs analytical SQL queries via `_core/connectors.run_query()` to compute statistics warehouse-side (no data transfer for BigQuery users). Deep mode retains the existing ydata-profiling path with `--sample` cap. All imports switch from profiler-local to `_core/`. The LLM output mode uses `_core/renderers/llm.py`.

**Tech Stack:** Python 3.10+, `_core/connectors` and `_core/renderers`, ydata-profiling (deep mode only)

**Spec:** `docs/superpowers/specs/2026-03-20-scripts-redesign-design.md` (section: "Phase 6: `profiler/` refactor")

**Depends on:** Phase 0 (`_core/` complete)

---

### Task 1: Add quick-mode SQL-based profiling to `analyzers/stats.py`

**Files:**
- Modify: `scripts/profiler/analyzers/stats.py`
- Test: `tests/scripts/test_profiler_quick_mode.py`

- [ ] **Step 1: Write test for quick-mode SQL query generation**

```python
# tests/scripts/test_profiler_quick_mode.py
from scripts.profiler.analyzers.stats import (
    build_quick_profile_sql,
    parse_quick_profile_result,
    quote_column,
)
import pandas as pd


def test_build_quick_profile_sql_duckdb():
    """Quick profile SQL should compute stats per column (DuckDB dialect)."""
    sql = build_quick_profile_sql("main", "fct_reservations", ["id", "amount", "status"], dialect="duckdb")
    assert "COUNT(*)" in sql
    assert "COUNT(DISTINCT" in sql
    assert "fct_reservations" in sql
    assert '"id"' in sql  # DuckDB uses double quotes


def test_build_quick_profile_sql_bigquery():
    """BigQuery dialect uses backtick quoting."""
    sql = build_quick_profile_sql("main", "fct_reservations", ["id", "amount"], dialect="bigquery")
    assert "`id`" in sql


def test_quote_column_duckdb():
    assert quote_column("my_col", "duckdb") == '"my_col"'


def test_quote_column_bigquery():
    assert quote_column("my_col", "bigquery") == '`my_col`'


def test_parse_quick_profile_result():
    """Parse the result DataFrame into a structured stats dict."""
    # Simulated result from the quick SQL query
    result_df = pd.DataFrame({
        "column_name": ["id", "amount", "status"],
        "total_count": [1000, 1000, 1000],
        "null_count": [0, 50, 10],
        "distinct_count": [1000, 150, 5],
        "min_val": ["1", "0.50", "active"],
        "max_val": ["1000", "500.00", "pending"],
        "avg_val": [500.5, 125.75, None],
        "top_values": ["1|2|3|4|5", "10.00|25.00|50.00", "active|pending|inactive"],
    })
    stats = parse_quick_profile_result(result_df)
    assert stats["id"]["null_rate"] == 0.0
    assert stats["id"]["distinct_count"] == 1000
    assert stats["amount"]["null_rate"] == 0.05
    assert stats["amount"]["avg"] == 125.75
    assert stats["status"]["distinct_count"] == 5
    assert "active" in stats["status"]["top_values"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/scripts/test_profiler_quick_mode.py -v`
Expected: FAIL — `ImportError` (functions don't exist yet)

- [ ] **Step 3: Add quick-mode functions to `stats.py`**

Add to `scripts/profiler/analyzers/stats.py`:

```python
def quote_column(col: str, dialect: str = "duckdb") -> str:
    """Quote a column name for the target dialect."""
    if dialect == "bigquery":
        return f"`{col}`"
    return f'"{col}"'


def build_quick_profile_sql(
    schema: str,
    table: str,
    columns: list[str],
    dialect: str = "duckdb",
) -> str:
    """Build SQL that computes per-column statistics warehouse-side.

    Returns a single query that produces one row per column with:
    total_count, null_count, distinct_count, min_val, max_val, avg_val, top_values.

    Uses dialect-aware quoting (double quotes for DuckDB, backticks for BigQuery).
    """
    # BigQuery uses STRING, DuckDB uses VARCHAR
    str_type = "STRING" if dialect == "bigquery" else "VARCHAR"

    col_queries = []
    for col in columns:
        qcol = quote_column(col, dialect)
        col_queries.append(f"""
        select
            '{col}' as column_name,
            count(*) as total_count,
            count(*) - count({qcol}) as null_count,
            count(distinct {qcol}) as distinct_count,
            cast(min({qcol}) as {str_type}) as min_val,
            cast(max({qcol}) as {str_type}) as max_val,
            avg(case when safe_cast({qcol} as float64) is not null then safe_cast({qcol} as float64) end) as avg_val,
            (select string_agg(cast(val as {str_type}), '|' order by cnt desc)
             from (select {qcol} as val, count(*) as cnt
                   from {schema}.{table}
                   group by {qcol}
                   order by cnt desc
                   limit 5)) as top_values
        from {schema}.{table}""")

    return "\nunion all\n".join(col_queries)


def parse_quick_profile_result(result_df) -> dict:
    """Parse quick profile SQL result into a stats dict keyed by column name."""
    stats = {}
    for _, row in result_df.iterrows():
        col_name = row["column_name"]
        total = row["total_count"]
        top_vals_raw = row.get("top_values", "")
        top_values = top_vals_raw.split("|") if top_vals_raw else []

        stats[col_name] = {
            "total_count": total,
            "null_count": row["null_count"],
            "null_rate": round(row["null_count"] / total, 4) if total > 0 else 0,
            "distinct_count": row["distinct_count"],
            "uniqueness_ratio": round(row["distinct_count"] / total, 4) if total > 0 else 0,
            "min": row.get("min_val"),
            "max": row.get("max_val"),
            "avg": row.get("avg_val"),
            "top_values": top_values,
        }
    return stats
```

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/scripts/test_profiler_quick_mode.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/profiler/analyzers/stats.py tests/scripts/test_profiler_quick_mode.py
git commit -m "feat(profiler): add quick-mode SQL-based profiling functions"
```

---

### Task 2: Integrate quick mode into profiler CLI

**Files:**
- Modify: `scripts/profiler/cli.py`

- [ ] **Step 1: Update CLI to use quick mode as default**

Modify `profile_target()` in `scripts/profiler/cli.py`:
- When `--full-profile` is NOT passed, use quick mode: run SQL queries via `connector.run_query()`, skip ydata-profiling entirely
- When `--full-profile` IS passed, use existing deep mode
- Quick mode produces the same `AnalysisResult` structure that renderers consume
- Pass `dialect=target.connector_type` to `build_quick_profile_sql()` for correct quoting

- [ ] **Step 2: Add grain information to profile output**

At the top of every profile output (both quick and deep modes), include candidate key analysis from `grain/key_discovery`:
```python
from scripts.grain.key_discovery import find_candidate_keys

# After fetching data/stats, before rendering:
candidates = find_candidate_keys(df) if df is not None else []
if candidates:
    print(f"\nCANDIDATE KEYS:")
    for c in candidates[:3]:
        cols = ", ".join(c["columns"])
        print(f"  [{c['uniqueness_ratio']:.0%}] {cols}")
```

This ensures the spec requirement "Grain information (candidate keys) appears at the top of every profile output" is met.

- [ ] **Step 3: Add `llm` output mode to CLI**

Add `"llm"` to valid output modes in `resolve_output_modes()`. When `"llm"` is in modes, render via `scripts._core.renderers.llm.render_llm_context()`.

- [ ] **Step 3: Verify quick mode works end-to-end**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m scripts.profiler.cli --select stg_vistareserve__reservations --output terminal --sample 10`
Expected: Fast output (seconds, not minutes) with column statistics.

- [ ] **Step 4: Verify deep mode still works**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m scripts.profiler.cli --select stg_vistareserve__reservations --output terminal --sample 100 --full-profile`
Expected: Slower output with full ydata-profiling results.

- [ ] **Step 5: Commit**

```bash
git add scripts/profiler/cli.py
git commit -m "feat(profiler): quick SQL mode as default, deep mode via --full-profile"
```

---

### Task 3: Complete migration to `_core/` — remove profiler's local connectors/renderers

**Files:**
- Modify: `scripts/profiler/cli.py` — update all imports to `_core/`
- Modify: `scripts/profiler/analyzers/stats.py` — update imports
- Modify: `scripts/profiler/models.py` — import from `_core` only
- Delete: `scripts/profiler/connectors/` (entire directory)
- Delete: `scripts/profiler/renderers/` (entire directory)
- Modify: `scripts/profiler/selector.py` — delegate to `_core/selector.py`

- [ ] **Step 1: Update all profiler imports to use `_core/`**

Replace all references to `scripts.profiler.connectors` with `scripts._core.connectors`. Replace all references to `scripts.profiler.renderers` with `scripts._core.renderers`. Replace `scripts.profiler.models.SelectionTarget` and `ColumnDef` with `scripts._core.models`.

In `scripts/profiler/selector.py`, replace the body with a delegation:
```python
"""Profiler selector — delegates to _core/selector.py."""
from scripts._core.selector import resolve_selector  # noqa: F401
```

In `scripts/profiler/models.py`, keep only profiler-specific classes (`AnalysisResult`, `DbtSignal`) and import shared ones from `_core`:
```python
from scripts._core.models import SelectionTarget, ColumnDef  # noqa: F401
```

- [ ] **Step 2: Delete profiler's local connectors/ and renderers/**

Run: `rm -rf scripts/profiler/connectors/ scripts/profiler/renderers/`

- [ ] **Step 3: Verify profiler still works**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m scripts.profiler.cli --select stg_vistareserve__reservations --output terminal --sample 10`
Expected: Same output, no import errors.

- [ ] **Step 4: Verify all tests pass**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/ -v --timeout=60`
Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add -A scripts/profiler/
git commit -m "refactor(profiler): complete migration to _core, remove local connectors/renderers"
```
