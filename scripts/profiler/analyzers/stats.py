"""Statistical analysis orchestrator using ydata-profiling."""
from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from scripts.profiler.models import AnalysisResult, SelectionTarget


def profile_dataframe(
    df: pd.DataFrame,
    target: SelectionTarget,
    full_profile: bool = False,
) -> AnalysisResult:
    """Run ydata-profiling on df and return an AnalysisResult.

    Args:
        df: The sample DataFrame to profile.
        target: The SelectionTarget this df came from.
        full_profile: If True, run full ydata-profiling (correlations, interactions).
                      If False (default), run minimal profile.

    Returns:
        AnalysisResult with profile and description populated.
        pii_columns and dbt_signals are empty (filled in by downstream analyzers).

    Raises:
        ImportError: if ydata-profiling is not installed.
    """
    try:
        from ydata_profiling import ProfileReport
    except ImportError:
        raise ImportError(
            "ydata-profiling is required for statistical analysis: "
            "pip install 'ydata-profiling>=4.6'"
        )

    profile = ProfileReport(
        df,
        minimal=not full_profile,
        title=target.table,
        progress_bar=False,
    )
    description = profile.get_description()

    return AnalysisResult(
        target=target,
        profile=profile,
        description=description,
        sample=df,
        pii_columns=set(),
        dbt_signals=[],
    )
