"""LLM-optimized markdown renderer for profiler output.

Renders an AnalysisResult to a structured markdown file in tmp/ with sections
for DDL, column statistics, dbt signals, PII flags, and redacted sample rows.
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from scripts._core.models import AnalysisResult
from scripts.profiler.sanitizer import sanitize

logger = logging.getLogger(__name__)

_TMP_DIR = Path("tmp")


def render_markdown(result: AnalysisResult, sanitize_pii: bool = False) -> Path:
    """Render a profiling result to an LLM-optimized markdown file.

    Sections:
    1. Header -- table name, profiled timestamp, row count vs sample size
    2. DDL (inferred) -- CREATE TABLE with source types and cast hint comments
    3. Column statistics table -- column, type, null%, n_distinct, alerts
    4. dbt Signals -- bulleted list
    5. PII Columns -- flagged names and entity types
    6. Sample Rows -- 5 rows; PII columns show [REDACTED:...] when sanitize_pii=True

    Returns:
        Path to the written .md file.
    """
    timestamp = result.profiled_at.strftime("%Y%m%d_%H%M%S")
    out_path = _TMP_DIR / f"profile_{result.target.table}_{timestamp}.md"
    _TMP_DIR.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []

    # 1. Header
    lines.append(f"# Profile: {result.target.table}")
    lines.append("")
    lines.append(f"- **Source:** `{result.target.schema}.{result.target.table}`")
    lines.append(f"- **Profiled at:** {result.profiled_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    lines.append(f"- **Sample rows:** {len(result.sample):,}")
    lines.append(f"- **Columns:** {len(result.sample.columns)}")
    lines.append("")

    # 2. DDL (inferred)
    lines.append("## DDL (Inferred)")
    lines.append("")
    lines.append("```sql")
    lines.append(f"CREATE TABLE {result.target.schema}.{result.target.table} (")

    variables = (
        getattr(result.description, "variables", {}) or {}
        if result.description
        else {}
    )
    cast_hints = {
        s.column_name: s.message
        for s in result.dbt_signals
        if s.signal_type == "CAST_HINT"
    }

    cols = list(result.sample.columns)
    for i, col in enumerate(cols):
        stats = variables.get(col, {})
        dtype = str(stats.get("dtype", result.sample[col].dtype))
        suffix = "," if i < len(cols) - 1 else ""
        comment = f"  -- {cast_hints[col]}" if col in cast_hints else ""
        lines.append(f"    {col} {dtype}{suffix}{comment}")

    lines.append(");")
    lines.append("```")
    lines.append("")

    # 3. Column statistics table
    lines.append("## Column Statistics")
    lines.append("")
    lines.append("| Column | Type | Null % | Distinct | Alerts |")
    lines.append("|--------|------|--------|----------|--------|")

    for col in result.sample.columns:
        stats = variables.get(col, {})
        dtype = str(stats.get("dtype", result.sample[col].dtype))
        null_pct = stats.get("p_missing", 0.0)
        n_distinct = stats.get("n_unique", "\u2014")
        # Gather alerts for this column
        col_alerts = _get_column_alerts(result, col)
        alert_str = ", ".join(col_alerts) if col_alerts else "\u2014"
        lines.append(f"| `{col}` | {dtype} | {null_pct:.1%} | {n_distinct} | {alert_str} |")

    lines.append("")

    # 4. dbt Signals
    lines.append("## dbt Signals")
    lines.append("")
    if result.dbt_signals:
        for sig in result.dbt_signals:
            lines.append(f"- **[{sig.signal_type}]** `{sig.column_name}`: {sig.message}")
    else:
        lines.append("_No signals detected._")
    lines.append("")

    # 5. PII Columns
    lines.append("## PII Columns")
    lines.append("")
    if result.pii_columns:
        for col in sorted(result.pii_columns):
            lines.append(f"- `{col}`")
    else:
        lines.append("_No PII columns detected._")
    lines.append("")

    # 6. Sample Rows
    lines.append("## Sample Rows")
    lines.append("")
    sample_df = sanitize(result.sample, result.pii_columns) if sanitize_pii else result.sample
    sample_5 = sample_df.head(5)
    lines.append(_df_to_markdown_table(sample_5))
    lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Markdown profile written to %s", out_path)
    return out_path


def _get_column_alerts(result: AnalysisResult, col: str) -> list[str]:
    """Extract alert type strings for a column from the description."""
    if result.description is None:
        return []
    alerts = getattr(result.description, "alerts", []) or []
    col_alerts = []
    for alert in alerts:
        if getattr(alert, "column_name", None) == col:
            alert_type = getattr(alert, "alert_type", None)
            if alert_type:
                col_alerts.append(str(alert_type))
    return col_alerts


def _df_to_markdown_table(df: pd.DataFrame) -> str:
    """Convert a DataFrame to a markdown table string."""
    if df.empty:
        return "_No rows._"
    cols = list(df.columns)
    header = "| " + " | ".join(str(c) for c in cols) + " |"
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    rows = []
    for _, row in df.iterrows():
        cells = " | ".join(
            str(v).replace("|", "\\|") if v is not None else "NULL" for v in row
        )
        rows.append(f"| {cells} |")
    return "\n".join([header, sep] + rows)
