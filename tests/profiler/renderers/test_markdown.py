"""Tests for the markdown renderer."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from scripts.profiler.models import AnalysisResult, DbtSignal, SelectionTarget
from scripts.profiler.renderers.markdown import render_markdown


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


@pytest.fixture
def minimal_result(sample_target, fixture_df) -> AnalysisResult:
    return AnalysisResult(
        target=sample_target,
        profile=None,
        description=None,
        sample=fixture_df,
        pii_columns=set(),
        dbt_signals=[],
        profiled_at=datetime(2026, 3, 15, 14, 30, 22, tzinfo=timezone.utc),
    )


def test_render_markdown_creates_file(minimal_result, tmp_path, monkeypatch):
    """render_markdown creates a .md file in tmp/."""
    import scripts.profiler.renderers.markdown as md_mod
    monkeypatch.setattr(md_mod, "_TMP_DIR", tmp_path)
    out = render_markdown(minimal_result)
    assert out.exists()
    assert out.suffix == ".md"


def test_render_markdown_contains_expected_sections(minimal_result, tmp_path, monkeypatch):
    """Output contains all required sections."""
    import scripts.profiler.renderers.markdown as md_mod
    monkeypatch.setattr(md_mod, "_TMP_DIR", tmp_path)
    out = render_markdown(minimal_result)
    content = out.read_text(encoding="utf-8")
    assert "# Profile: test_table" in content
    assert "## DDL (Inferred)" in content
    assert "## Column Statistics" in content
    assert "## dbt Signals" in content
    assert "## PII Columns" in content
    assert "## Sample Rows" in content


def test_render_markdown_redacts_pii(minimal_result, tmp_path, monkeypatch):
    """PII columns in sample rows are redacted."""
    import scripts.profiler.renderers.markdown as md_mod
    monkeypatch.setattr(md_mod, "_TMP_DIR", tmp_path)
    minimal_result.pii_columns = {"email_address"}
    out = render_markdown(minimal_result)
    content = out.read_text(encoding="utf-8")
    # email_address values should be redacted
    assert "alice@example.com" not in content
    assert "REDACTED" in content


def test_render_markdown_with_signals(minimal_result, tmp_path, monkeypatch):
    """dbt signals appear in the Signals section."""
    import scripts.profiler.renderers.markdown as md_mod
    monkeypatch.setattr(md_mod, "_TMP_DIR", tmp_path)
    minimal_result.dbt_signals = [
        DbtSignal(signal_type="CAST_HINT", column_name="amount", message="cast as decimal"),
    ]
    out = render_markdown(minimal_result)
    content = out.read_text(encoding="utf-8")
    assert "CAST_HINT" in content
    assert "amount" in content


def test_render_markdown_filename_includes_table_and_timestamp(minimal_result, tmp_path, monkeypatch):
    """Output filename includes table name and timestamp."""
    import scripts.profiler.renderers.markdown as md_mod
    monkeypatch.setattr(md_mod, "_TMP_DIR", tmp_path)
    out = render_markdown(minimal_result)
    assert "test_table" in out.name
    assert "20260315" in out.name
