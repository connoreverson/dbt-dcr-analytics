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
