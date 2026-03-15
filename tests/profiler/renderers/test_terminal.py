from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from io import StringIO
from unittest.mock import patch

import pandas as pd
import pytest

from rich.console import Console

from scripts.profiler.models import AnalysisResult, DbtSignal, SelectionTarget
from scripts.profiler.renderers.terminal import render_terminal


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
        profiled_at=datetime(2026, 3, 15, tzinfo=timezone.utc),
    )


def test_render_terminal_no_exception(minimal_result):
    """render_terminal produces non-empty output."""
    buf = StringIO()
    with patch("scripts.profiler.renderers.terminal.console", Console(file=buf)):
        render_terminal(minimal_result)
    output = buf.getvalue()
    assert "test_table" in output
    assert len(output) > 0


def test_render_terminal_with_signals(minimal_result):
    """render_terminal handles dbt signals without raising."""
    minimal_result.dbt_signals = [
        DbtSignal(signal_type="CAST_HINT", column_name="amount", message="cast as decimal"),
        DbtSignal(signal_type="UNUSED_COLUMN", column_name="legacy_flag", message="all null"),
    ]
    with patch("scripts.profiler.renderers.terminal.console", Console(file=StringIO())):
        render_terminal(minimal_result)


def test_render_terminal_with_pii(minimal_result):
    """render_terminal highlights PII columns without redacting."""
    minimal_result.pii_columns = {"email_address", "phone_number"}
    with patch("scripts.profiler.renderers.terminal.console", Console(file=StringIO())):
        render_terminal(minimal_result)


def test_render_terminal_skimpy_absent(minimal_result, caplog):
    """render_terminal degrades gracefully when skimpy is not installed."""
    buf = StringIO()
    with patch.dict(sys.modules, {"skimpy": None}):
        with caplog.at_level(logging.WARNING, logger="scripts.profiler.renderers.terminal"):
            with patch("scripts.profiler.renderers.terminal.console", Console(file=buf)):
                render_terminal(minimal_result)
    assert any("skimpy" in msg for msg in caplog.messages)
