"""Tests for scripts.profiler.analyzers.dbt_signals."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from scripts.profiler.analyzers.dbt_signals import detect_signals
from scripts.profiler.models import DbtSignal


def _make_desc(variables: dict, alerts: list = None) -> object:
    """Build a minimal description-like object."""
    return SimpleNamespace(variables=variables, alerts=alerts or [])


def _make_alert(column_name: str, alert_type: str) -> object:
    return SimpleNamespace(column_name=column_name, alert_type=alert_type)


def test_no_signals_for_clean_column():
    desc = _make_desc({"reservation_id": {"type": "Numeric", "dtype": "int64"}})
    signals = detect_signals(desc)
    assert not any(s.column_name == "reservation_id" for s in signals)


def test_rename_hint_for_camel_case():
    desc = _make_desc({"firstName": {"type": "Categorical", "dtype": "object"}})
    signals = detect_signals(desc)
    rename = [s for s in signals if s.signal_type == "RENAME_HINT" and s.column_name == "firstName"]
    assert len(rename) == 1
    assert "snake_case" in rename[0].message


def test_rename_hint_for_ambiguous_name():
    desc = _make_desc({"id": {"type": "Categorical", "dtype": "object"}})
    signals = detect_signals(desc)
    rename = [s for s in signals if s.signal_type == "RENAME_HINT" and s.column_name == "id"]
    assert len(rename) == 1
    assert "ambiguous" in rename[0].message


def test_unused_column_for_constant_alert():
    alert = _make_alert("constant_col", "CONSTANT")
    desc = _make_desc(
        {"constant_col": {"type": "Categorical", "dtype": "object"}},
        alerts=[alert],
    )
    signals = detect_signals(desc)
    unused = [s for s in signals if s.signal_type == "UNUSED_COLUMN" and s.column_name == "constant_col"]
    assert len(unused) == 1
    assert "constant" in unused[0].message


def test_unused_column_for_high_nulls_alert():
    alert = _make_alert("sparse_col", "HIGH_NULLS")
    desc = _make_desc(
        {"sparse_col": {"type": "Categorical", "dtype": "object"}},
        alerts=[alert],
    )
    signals = detect_signals(desc)
    unused = [s for s in signals if s.signal_type == "UNUSED_COLUMN" and s.column_name == "sparse_col"]
    assert len(unused) == 1


def test_empty_description_returns_empty_list():
    desc = _make_desc({})
    assert detect_signals(desc) == []


def test_description_with_none_attributes():
    desc = SimpleNamespace(variables=None, alerts=None)
    assert detect_signals(desc) == []


def test_cast_hint_for_numeric_in_object_column():
    """A column with object dtype but a mean value should get CAST_HINT."""
    desc = _make_desc({
        "amount": {"type": "Categorical", "dtype": "object", "mean": 149.99}
    })
    signals = detect_signals(desc)
    cast = [s for s in signals if s.signal_type == "CAST_HINT" and s.column_name == "amount"]
    assert len(cast) == 1
    assert "numeric" in cast[0].message
