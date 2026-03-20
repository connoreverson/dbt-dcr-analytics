"""Tests for scripts._core.models shared dataclasses."""
from scripts._core.models import ColumnDef, SelectionTarget


def test_selection_target_creation():
    target = SelectionTarget(
        prefix="model",
        table="fct_reservations",
        connector_type="duckdb",
        conn_str="target/dcr_analytics.duckdb",
        schema="main",
        resource_type="model",
    )
    assert target.prefix == "model"
    assert target.table == "fct_reservations"
    assert target.connector_type == "duckdb"
    assert target.conn_str == "target/dcr_analytics.duckdb"
    assert target.schema == "main"
    assert target.resource_type == "model"
    assert target.database == ""  # default for model nodes


def test_column_def_creation():
    col = ColumnDef(name="reservation_id", source_type="VARCHAR", nullable=False)
    assert col.name == "reservation_id"
    assert col.source_type == "VARCHAR"
    assert col.nullable is False
