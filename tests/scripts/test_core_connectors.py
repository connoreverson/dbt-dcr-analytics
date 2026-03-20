"""Tests for _core connectors: base ABC and DuckDB run_query()."""
from __future__ import annotations

import pytest
import pandas as pd

from scripts._core.connectors.base import BaseConnector
from scripts._core.models import ColumnDef, SelectionTarget


def test_base_connector_is_abstract():
    """BaseConnector cannot be instantiated directly."""
    target = SelectionTarget(
        prefix="model",
        table="test",
        connector_type="duckdb",
        conn_str="test.duckdb",
        schema="main",
        resource_type="model",
    )
    with pytest.raises(TypeError):
        BaseConnector(target)


def test_duckdb_run_query(tmp_path):
    """DuckDBConnector.run_query() executes SQL and returns a DataFrame."""
    import duckdb

    db_path = str(tmp_path / "test.duckdb")
    conn = duckdb.connect(db_path)
    conn.execute("CREATE TABLE test_table (id INTEGER, name VARCHAR)")
    conn.execute("INSERT INTO test_table VALUES (1, 'a'), (2, 'b'), (3, 'c')")
    conn.close()

    from scripts._core.connectors.duckdb import DuckDBConnector

    target = SelectionTarget(
        prefix="model",
        table="test_table",
        connector_type="duckdb",
        conn_str=db_path,
        schema="main",
        resource_type="model",
    )
    connector = DuckDBConnector(target)
    result = connector.run_query("SELECT count(*) as cnt FROM main.test_table")
    assert isinstance(result, pd.DataFrame)
    assert result["cnt"].iloc[0] == 3
    connector.close()
