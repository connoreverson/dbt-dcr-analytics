"""Tests for scripts.profiler.sanitizer."""
from __future__ import annotations

import pandas as pd
import pytest

from scripts.profiler.sanitizer import sanitize


def test_sanitize_empty_pii_columns_returns_copy():
    df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    result = sanitize(df, set())
    assert result is not df
    pd.testing.assert_frame_equal(result, df)


def test_sanitize_redacts_flagged_column(fixture_df):
    result = sanitize(fixture_df, {"email_address"})
    for val in result["email_address"]:
        assert "REDACTED" in str(val)


def test_sanitize_does_not_mutate_original(fixture_df):
    original_email = fixture_df["email_address"].tolist()
    sanitize(fixture_df, {"email_address"})
    assert fixture_df["email_address"].tolist() == original_email


def test_sanitize_ignores_missing_column(fixture_df):
    """Passing a column name not in df should not raise."""
    result = sanitize(fixture_df, {"nonexistent_column"})
    assert result is not None


def test_sanitize_preserves_non_pii_columns(fixture_df):
    result = sanitize(fixture_df, {"email_address"})
    pd.testing.assert_series_equal(result["amount"], fixture_df["amount"])


def test_sanitize_handles_null_values():
    df = pd.DataFrame({"email": [None, "alice@example.com", None]})
    result = sanitize(df, {"email"})
    assert result["email"].iloc[0] is None or pd.isna(result["email"].iloc[0])
    assert "REDACTED" in str(result["email"].iloc[1])
