"""Tests for the statistical analysis orchestrator."""
from __future__ import annotations

import pytest

pytest.importorskip("ydata_profiling", reason="ydata-profiling not installed")

import pandas as pd

from scripts.profiler.analyzers.stats import profile_dataframe
from scripts.profiler.models import SelectionTarget


@pytest.fixture
def sample_target() -> SelectionTarget:
    return SelectionTarget(
        prefix="model",
        table="test_table",
        connector_type="duckdb",
        conn_str="dev.duckdb",
        schema="main",
        resource_type="model",
    )


def test_profile_returns_analysis_result(fixture_df, sample_target):
    """profile_dataframe returns a populated AnalysisResult."""
    result = profile_dataframe(fixture_df, sample_target)
    assert result.target is sample_target
    assert result.sample is fixture_df
    assert result.profile is not None
    assert result.description is not None
    assert result.pii_columns == set()
    assert result.dbt_signals == []


def test_profile_description_has_expected_keys(fixture_df, sample_target):
    """Description object has variables dict with one entry per column."""
    result = profile_dataframe(fixture_df, sample_target)
    desc = result.description
    variables = desc.variables if hasattr(desc, "variables") else {}
    # fixture_df has 6 columns — all should appear in the description
    assert len(variables) == len(fixture_df.columns)


def test_profile_minimal_vs_full(fixture_df, sample_target):
    """full_profile=False produces a result; full_profile=True also works."""
    result_minimal = profile_dataframe(fixture_df, sample_target, full_profile=False)
    assert result_minimal.profile is not None

    result_full = profile_dataframe(fixture_df, sample_target, full_profile=True)
    assert result_full.profile is not None


def test_missing_ydata_profiling_raises_import_error(sample_target, monkeypatch):
    """ImportError is raised with pip install hint when ydata-profiling absent."""
    import sys
    had_module = "ydata_profiling" in sys.modules
    original = sys.modules.get("ydata_profiling")
    sys.modules["ydata_profiling"] = None  # type: ignore[assignment]
    try:
        with pytest.raises(ImportError, match="ydata-profiling"):
            profile_dataframe(pd.DataFrame({"a": [1]}), sample_target)
    finally:
        if not had_module:
            del sys.modules["ydata_profiling"]
        else:
            sys.modules["ydata_profiling"] = original
