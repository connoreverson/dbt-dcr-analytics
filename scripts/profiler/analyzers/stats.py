"""Statistical analysis orchestrator using ydata-profiling."""
from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from scripts.profiler.models import AnalysisResult, SelectionTarget


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
    str_type = "STRING" if dialect == "bigquery" else "VARCHAR"
    cast_fn = "SAFE_CAST" if dialect == "bigquery" else "TRY_CAST"
    float_type = "FLOAT64" if dialect == "bigquery" else "DOUBLE"

    col_queries = []
    for col in columns:
        qcol = quote_column(col, dialect)
        col_queries.append(f"""        select
            '{col}' as column_name,
            COUNT(*) as total_count,
            COUNT(*) - count({qcol}) as null_count,
            COUNT(DISTINCT {qcol}) as distinct_count,
            cast(min({qcol}) as {str_type}) as min_val,
            cast(max({qcol}) as {str_type}) as max_val,
            avg({cast_fn}({qcol} as {float_type})) as avg_val,
            (select string_agg(cast(val as {str_type}), '|')
             from (select {qcol} as val, count(*) as cnt
                   from {schema}.{table}
                   group by {qcol}
                   order by cnt desc
                   limit 5) _top) as top_values
        from {schema}.{table}""")

    return "\nunion all\n".join(col_queries)


def parse_quick_profile_result(result_df: pd.DataFrame) -> dict:
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


def profile_dataframe(
    df: pd.DataFrame,
    target: SelectionTarget,
    full_profile: bool = False,
) -> AnalysisResult:
    """Run ydata-profiling on df and return an AnalysisResult.

    Args:
        df: The sample DataFrame to profile.
        target: The SelectionTarget this df came from.
        full_profile: If True, run full ydata-profiling (correlations, interactions).
                      If False (default), run minimal profile.

    Returns:
        AnalysisResult with profile and description populated.
        pii_columns and dbt_signals are empty (filled in by downstream analyzers).

    Note:
        progress_bar=False is set unconditionally to prevent tqdm output in
        non-interactive (CLI/subprocess) contexts where the progress bar would
        corrupt terminal output.

    Raises:
        ImportError: if ydata-profiling is not installed.
    """
    try:
        from ydata_profiling import ProfileReport
    except ImportError:
        raise ImportError(
            "ydata-profiling is required for statistical analysis: "
            "pip install 'ydata-profiling>=4.6'"
        )

    profile = ProfileReport(
        df,
        minimal=not full_profile,
        title=target.table,
        progress_bar=False,
    )
    description = profile.get_description()

    return AnalysisResult(
        target=target,
        profile=profile,
        description=description,
        sample=df,
        pii_columns=set(),
        dbt_signals=[],
    )
