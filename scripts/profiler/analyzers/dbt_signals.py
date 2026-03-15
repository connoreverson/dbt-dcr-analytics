"""Detect dbt-relevant signals from a ydata-profiling description.

Pure interpretation layer — no statistical computation. Reads the description
dict produced by ProfileReport.get_description() and emits DbtSignal objects
for downstream renderers.
"""
from __future__ import annotations

import re

from scripts.profiler.models import DbtSignal

# Column names that should trigger RENAME_HINT
_CAMEL_CASE_PATTERN = re.compile(r"[a-z][A-Z]")
_HUNGARIAN_PATTERN = re.compile(r"^(str|int|flt|bln|dbl|arr|obj)[A-Z_]")
_AMBIGUOUS_NAMES = frozenset(["id", "code", "flag", "type", "status", "name", "value", "data"])


def detect_signals(description: object) -> list[DbtSignal]:
    """Detect dbt-relevant signals from a ydata-profiling BaseDescription.

    Args:
        description: The result of ProfileReport.get_description(). Must have
                     a .variables attribute (dict of column_name -> variable stats dict)
                     and an .alerts attribute (list of alert objects with .column_name
                     and .alert_type attributes).

    Returns:
        List of DbtSignal objects (may be empty).
    """
    signals: list[DbtSignal] = []

    variables: dict = getattr(description, "variables", {}) or {}
    alerts: list = getattr(description, "alerts", []) or []

    # Build a set of columns with CONSTANT or HIGH_NULLS alerts (for UNUSED_COLUMN)
    alert_cols: dict[str, set[str]] = {}
    for alert in alerts:
        col = getattr(alert, "column_name", None)
        alert_type = getattr(alert, "alert_type", None)
        if col and alert_type:
            alert_cols.setdefault(col, set()).add(str(alert_type))

    for col_name, stats in variables.items():
        col_type = stats.get("type", "")  # e.g. "Categorical", "Numeric", "Text"
        pandas_type = str(stats.get("dtype", ""))

        # CAST_HINT: VARCHAR column with numeric or date inferred type
        if "object" in pandas_type.lower() or col_type in ("Categorical", "Text"):
            mean = stats.get("mean", None)
            if mean is not None:
                signals.append(DbtSignal(
                    signal_type="CAST_HINT",
                    column_name=col_name,
                    message=f"cast({col_name} as numeric) — column stores numeric values as text",
                ))
            elif _looks_like_date_column(col_name, stats):
                signals.append(DbtSignal(
                    signal_type="CAST_HINT",
                    column_name=col_name,
                    message=f"cast({col_name} as date) — column name suggests date/time data",
                ))

        # RENAME_HINT: camelCase, Hungarian notation, or ambiguous names
        if _CAMEL_CASE_PATTERN.search(col_name):
            signals.append(DbtSignal(
                signal_type="RENAME_HINT",
                column_name=col_name,
                message=f"rename to snake_case: {_to_snake_case(col_name)}",
            ))
        elif _HUNGARIAN_PATTERN.match(col_name):
            signals.append(DbtSignal(
                signal_type="RENAME_HINT",
                column_name=col_name,
                message=f"remove Hungarian notation prefix from: {col_name}",
            ))
        elif col_name.lower() in _AMBIGUOUS_NAMES:
            signals.append(DbtSignal(
                signal_type="RENAME_HINT",
                column_name=col_name,
                message=f"ambiguous column name '{col_name}' — prefix with entity context",
            ))

        # UNUSED_COLUMN: CONSTANT or HIGH_NULLS alerts
        col_alerts = alert_cols.get(col_name, set())
        if "CONSTANT" in col_alerts:
            signals.append(DbtSignal(
                signal_type="UNUSED_COLUMN",
                column_name=col_name,
                message="constant value — consider dropping in staging",
            ))
        elif "HIGH_NULLS" in col_alerts:
            signals.append(DbtSignal(
                signal_type="UNUSED_COLUMN",
                column_name=col_name,
                message="high null rate — consider dropping or documenting sparse population",
            ))

    return signals


def _looks_like_date_column(col_name: str, stats: dict) -> bool:
    """Heuristic: does the column name contain date/time keywords?

    Match whole words or common date suffixes — avoid 'at' matching 'category'
    by using underscore-prefixed variants (_at, _on).
    """
    date_keywords = ("date", "time", "_at", "_on", "created", "updated", "modified", "_ts", "timestamp")
    name_lower = col_name.lower()
    return any(kw in name_lower for kw in date_keywords)


def _to_snake_case(name: str) -> str:
    """Convert camelCase to snake_case."""
    s1 = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    return s1.lower()
