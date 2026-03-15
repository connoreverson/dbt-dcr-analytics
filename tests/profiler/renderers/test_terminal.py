from __future__ import annotations

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


def test_render_terminal_no_exception(minimal_result, capsys):
    """render_terminal completes without raising."""
    # Patch skimpy.skim to avoid actual dependency
    with patch("scripts.profiler.renderers.terminal.console", Console(file=StringIO())):
        render_terminal(minimal_result)


def test_render_terminal_with_signals(minimal_result, capsys):
    """render_terminal handles dbt signals without raising."""
    minimal_result.dbt_signals = [
        DbtSignal(signal_type="CAST_HINT", column_name="amount", message="cast as decimal"),
        DbtSignal(signal_type="UNUSED_COLUMN", column_name="legacy_flag", message="all null"),
    ]
    with patch("scripts.profiler.renderers.terminal.console", Console(file=StringIO())):
        render_terminal(minimal_result)


def test_render_terminal_with_pii(minimal_result, capsys):
    """render_terminal highlights PII columns without redacting."""
    minimal_result.pii_columns = {"email_address", "phone_number"}
    with patch("scripts.profiler.renderers.terminal.console", Console(file=StringIO())):
        render_terminal(minimal_result)


def test_render_terminal_skimpy_absent(minimal_result):
    """render_terminal degrades gracefully when skimpy is not installed."""
    import sys
    had = "skimpy" in sys.modules
    original = sys.modules.get("skimpy")
    sys.modules["skimpy"] = None  # type: ignore[assignment]
    try:
        with patch("scripts.profiler.renderers.terminal.console", Console(file=StringIO())):
            render_terminal(minimal_result)  # must not raise
    finally:
        if not had:
            del sys.modules["skimpy"]
        else:
            sys.modules["skimpy"] = original
