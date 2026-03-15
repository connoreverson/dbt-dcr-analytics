from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from scripts.profiler.models import AnalysisResult, DbtSignal, SelectionTarget
from scripts.profiler.renderers.html import render_html, _render_signals_section


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
def mock_profile() -> MagicMock:
    """A mock ProfileReport that returns a minimal HTML document."""
    profile = MagicMock()
    profile.to_html.return_value = (
        "<!DOCTYPE html><html><head></head><body>"
        "<p>Profile content</p>"
        "</body></html>"
    )
    return profile


@pytest.fixture
def result_with_profile(sample_target, fixture_df, mock_profile) -> AnalysisResult:
    return AnalysisResult(
        target=sample_target,
        profile=mock_profile,
        description=None,
        sample=fixture_df,
        pii_columns=set(),
        dbt_signals=[],
        profiled_at=datetime(2026, 3, 15, 14, 30, 22, tzinfo=timezone.utc),
    )


def test_render_html_creates_file(result_with_profile, tmp_path, monkeypatch):
    """render_html creates a .html file in tmp/."""
    import scripts.profiler.renderers.html as html_mod
    monkeypatch.setattr(html_mod, "_TMP_DIR", tmp_path)
    out = render_html(result_with_profile)
    assert out.exists()
    assert out.suffix == ".html"


def test_render_html_injects_signals_section(result_with_profile, tmp_path, monkeypatch):
    """Signals section is injected after <body> tag."""
    import scripts.profiler.renderers.html as html_mod
    monkeypatch.setattr(html_mod, "_TMP_DIR", tmp_path)
    result_with_profile.dbt_signals = [
        DbtSignal(signal_type="CAST_HINT", column_name="amount", message="cast as decimal"),
    ]
    out = render_html(result_with_profile)
    content = out.read_text(encoding="utf-8")
    assert "profiler-signals" in content
    assert "CAST_HINT" in content
    assert "amount" in content


def test_render_html_profile_none_raises(result_with_profile, tmp_path, monkeypatch):
    """RuntimeError raised when profile is None."""
    result_with_profile.profile = None
    with pytest.raises(RuntimeError, match="result.profile is None"):
        render_html(result_with_profile)


def test_render_html_signals_section_no_signals(result_with_profile):
    """_render_signals_section returns valid HTML even with no signals."""
    html = _render_signals_section(result_with_profile)
    assert "profiler-signals" in html
    assert "No signals detected" in html
    assert "No PII columns detected" in html


def test_render_html_filename_includes_table_and_timestamp(result_with_profile, tmp_path, monkeypatch):
    """Output filename includes table name and timestamp."""
    import scripts.profiler.renderers.html as html_mod
    monkeypatch.setattr(html_mod, "_TMP_DIR", tmp_path)
    out = render_html(result_with_profile)
    assert "test_table" in out.name
    assert "20260315" in out.name


def test_render_html_sanitize_html_no_pii_logs_info(result_with_profile, tmp_path, monkeypatch, caplog):
    """When sanitize_html=True but no PII columns, logs info and renders normally."""
    import logging
    import scripts.profiler.renderers.html as html_mod
    monkeypatch.setattr(html_mod, "_TMP_DIR", tmp_path)
    result_with_profile.pii_columns = set()
    with caplog.at_level(logging.INFO, logger="scripts.profiler.renderers.html"):
        out = render_html(result_with_profile, sanitize_html=True)
    assert out.exists()
    assert any("no PII" in msg.lower() or "unsanitized" in msg.lower() for msg in caplog.messages)
