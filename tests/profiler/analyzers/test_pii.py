from __future__ import annotations

import pandas as pd
import pytest

from scripts.profiler.analyzers.pii import _PII_NAME_PATTERNS, _spacy_available, detect_pii


def _presidio_available() -> bool:
    try:
        import presidio_analyzer  # noqa: F401
        return True
    except ImportError:
        return False


# ---------------------------------------------------------------------------
# Pass 1: name heuristic tests
# ---------------------------------------------------------------------------

def test_email_column_flagged_by_name():
    df = pd.DataFrame({"email_address": ["x@y.com"], "amount": [100]})
    result = detect_pii(df)
    assert "email_address" in result
    assert "amount" not in result


def test_ssn_column_flagged_by_name():
    df = pd.DataFrame({"ssn": ["123-45-6789"], "record_id": [1]})
    result = detect_pii(df)
    assert "ssn" in result


def test_non_pii_column_not_flagged_by_name():
    # Use non-date, non-PII values so Presidio value-scan doesn't false-positive
    df = pd.DataFrame({"confirmed_at": ["active", "pending"], "status": ["open", "closed"]})
    result = detect_pii(df)
    assert "confirmed_at" not in result
    assert "status" not in result


def test_partial_match_flags_column():
    """'first_name' pattern matches 'customer_first_name'."""
    df = pd.DataFrame({"customer_first_name": ["Alice"]})
    result = detect_pii(df)
    assert "customer_first_name" in result


def test_empty_dataframe_returns_empty_set():
    df = pd.DataFrame()
    result = detect_pii(df)
    assert result == set()


def test_all_numeric_columns_not_flagged():
    df = pd.DataFrame({"amount": [1.0, 2.0], "count": [3, 4]})
    result = detect_pii(df)
    # numeric columns can't be PII by name heuristic alone here
    assert "amount" not in result
    assert "count" not in result


# ---------------------------------------------------------------------------
# Pass 2: value-scan tests (only if presidio + spaCy available)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not _spacy_available() or not _presidio_available(),
    reason="presidio-analyzer + en_core_web_lg not available",
)
def test_value_scan_flags_obfuscated_email_column():
    """A column named 'col1' containing emails should be flagged by value scan."""
    df = pd.DataFrame({
        "col1": ["alice@example.com", "bob@example.com", "carol@example.com"],
        "col2": ["foo", "bar", "baz"],
    })
    result = detect_pii(df)
    assert "col1" in result
    assert "col2" not in result


# ---------------------------------------------------------------------------
# Integration test: fixture_df from conftest
# ---------------------------------------------------------------------------

def test_fixture_df_email_column_flagged(fixture_df):
    """fixture_df has 'email_address' -- should be flagged by name heuristic."""
    result = detect_pii(fixture_df)
    assert "email_address" in result


def test_fixture_df_constant_col_not_flagged(fixture_df):
    """'constant_col' is not a PII name and contains 'X' values -- not flagged."""
    result = detect_pii(fixture_df)
    assert "constant_col" not in result


def test_presidio_absent_falls_back_to_name_heuristic(caplog):
    """When presidio-analyzer is absent, name-heuristic results are still returned."""
    import sys
    import logging
    had = "presidio_analyzer" in sys.modules
    original = sys.modules.get("presidio_analyzer")
    sys.modules["presidio_analyzer"] = None  # type: ignore[assignment]
    try:
        df = pd.DataFrame({
            "email_address": ["x@y.com"],
            "obfuscated_col": ["x@y.com"],  # would be caught by value scan
        })
        with caplog.at_level(logging.WARNING, logger="scripts.profiler.analyzers.pii"):
            result = detect_pii(df)
        assert "email_address" in result  # name heuristic still works
        assert "obfuscated_col" not in result  # value scan skipped
        assert any("presidio-analyzer" in msg for msg in caplog.messages)
    finally:
        if not had:
            del sys.modules["presidio_analyzer"]
        else:
            sys.modules["presidio_analyzer"] = original
