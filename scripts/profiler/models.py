"""Shared dataclasses for dbt-profiler.

AnalysisResult references ydata-profiling types under TYPE_CHECKING only
so that models.py has no hard import of ydata-profiling at module load time.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Literal

from scripts._core.models import ColumnDef, SelectionTarget  # noqa: F401 — re-export

if TYPE_CHECKING:
    import pandas as pd
    from ydata_profiling import ProfileReport
    from ydata_profiling.model.description import BaseDescription


@dataclass
class DbtSignal:
    """A single dbt-specific observation about a column or table."""

    signal_type: Literal["CAST_HINT", "RENAME_HINT", "UNUSED_COLUMN", "NULL_PATTERN"]
    column_name: str
    message: str
    """Human-readable description, e.g. 'cast(amount as decimal(10,2))'."""


@dataclass
class AnalysisResult:
    """The complete output of the analysis pipeline for one SelectionTarget.

    sanitized_sample is intentionally absent. Renderers that need redacted
    data call sanitizer.sanitize(result.sample, result.pii_columns) inline.
    """

    target: SelectionTarget
    profile: ProfileReport | None
    """Full ydata-profiling ProfileReport object. Used by html renderer."""
    description: BaseDescription | None
    """profile.get_description(). Used by markdown renderer and dbt_signals."""
    sample: pd.DataFrame
    """Raw sample — never mutated."""
    pii_columns: set[str]
    dbt_signals: list[DbtSignal]
    profiled_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
