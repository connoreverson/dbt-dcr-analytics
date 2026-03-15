"""Integration tests -- require a real DuckDB file from source_data/duckdb/."""
from __future__ import annotations

import duckdb
import pandas as pd
import pytest

from scripts.profiler.connectors.duckdb import DuckDBConnector
from scripts.profiler.models import ColumnDef, SelectionTarget


@pytest.fixture
def vistareserve_target(fixture_duckdb_path) -> SelectionTarget:
    """Build a SelectionTarget pointing at the first table in the fixture DB."""
    con = duckdb.connect(str(fixture_duckdb_path), read_only=True)
    table = con.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'main' LIMIT 1"
    ).fetchone()
    con.close()
    if table is None:
        pytest.skip("No tables found in main schema of test DuckDB fixture")
    table = table[0]
    return SelectionTarget(
        prefix="source",
        table=table,
        connector_type="duckdb",
        conn_str=str(fixture_duckdb_path),
        schema="main",
        resource_type="source",
    )


@pytest.fixture
def duckdb_connector(vistareserve_target):
    """Create a DuckDBConnector and close it after the test."""
    conn = DuckDBConnector(vistareserve_target)
    yield conn
    conn.close()


def test_get_schema_returns_column_defs(duckdb_connector):
    schema = duckdb_connector.get_schema()
    assert len(schema) > 0
    assert all(isinstance(c, ColumnDef) for c in schema)
    assert all(isinstance(c.name, str) for c in schema)
    assert all(isinstance(c.source_type, str) for c in schema)


def test_get_sample_returns_dataframe(duckdb_connector):
    df = duckdb_connector.get_sample(n_rows=10)
    assert isinstance(df, pd.DataFrame)
    assert len(df) <= 10
    assert len(df.columns) > 0


def test_get_sample_respects_row_limit(duckdb_connector):
    df = duckdb_connector.get_sample(n_rows=5)
    assert len(df) <= 5


def test_connector_raises_on_bad_table(fixture_duckdb_path):
    target = SelectionTarget(
        prefix="source",
        table="nonexistent_table_xyz",
        connector_type="duckdb",
        conn_str=str(fixture_duckdb_path),
        schema="main",
        resource_type="source",
    )
    conn = DuckDBConnector(target)
    try:
        with pytest.raises(duckdb.CatalogException):
            conn.get_sample(n_rows=10)
    finally:
        conn.close()
