# tests/profiler/test_models.py
from __future__ import annotations
from scripts.profiler.models import SelectionTarget, ColumnDef, DbtSignal, AnalysisResult
import pandas as pd
from datetime import datetime


def test_selection_target_fields():
    t = SelectionTarget(
        prefix="source",
        table="reservations",
        connector_type="duckdb",
        conn_str="source_data/duckdb/dcr_rev_01_vistareserve.duckdb",
        schema="main",
        resource_type="source",
    )
    assert t.table == "reservations"
    assert t.connector_type == "duckdb"


def test_column_def_fields():
    c = ColumnDef(name="email_address", source_type="VARCHAR", nullable=True)
    assert c.nullable is True


def test_dbt_signal_fields():
    s = DbtSignal(
        signal_type="CAST_HINT",
        column_name="amount",
        message="cast(amount as decimal(10,2))",
    )
    assert s.signal_type == "CAST_HINT"


def test_analysis_result_no_sanitized_sample():
    """AnalysisResult must not carry a sanitized_sample field."""
    import dataclasses
    field_names = {f.name for f in dataclasses.fields(AnalysisResult)}
    assert "sanitized_sample" not in field_names

# Note: AnalysisResult cannot be fully instantiated here because it requires
# a live ProfileReport and BaseDescription from ydata-profiling.
# Full construction is validated end-to-end in Task 5 (test_stats.py).
