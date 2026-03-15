from __future__ import annotations

import logging
import warnings

import pandas as pd

logger = logging.getLogger(__name__)

# Column name patterns that indicate PII (case-insensitive substring match)
_PII_NAME_PATTERNS = frozenset([
    "email", "ssn", "phone", "dob", "birth",
    "first_name", "last_name", "surname", "address",
    "ip_address", "ip_addr", "passport", "license",
    "credit_card", "card_number", "routing",
    "social_security", "taxpayer", "national_id",
])

# Ambiguous names that need value-scan to confirm (not auto-flagged by name alone)
_AMBIGUOUS_NAMES = frozenset([
    "name", "id", "code", "number", "num",
])


def _spacy_available() -> bool:
    """Return True if spaCy and en_core_web_lg model are both available."""
    try:
        import spacy  # noqa: F401
        spacy.load("en_core_web_lg")
        return True
    except Exception:
        return False


def detect_pii(df: pd.DataFrame) -> set[str]:
    """Detect PII columns using a two-pass heuristic + Presidio scan.

    Pass 1: Flag columns whose names match known PII patterns.
    Pass 2: Value-scan remaining string columns via Presidio (up to 100 values each).

    Falls back to name-heuristic only if presidio-analyzer is absent or
    if the spaCy en_core_web_lg model is missing.

    Returns:
        Set of column names detected as containing PII.
    """
    flagged: set[str] = set()

    # Pass 1: name heuristic
    for col in df.columns:
        col_lower = col.lower()
        for pattern in _PII_NAME_PATTERNS:
            if pattern in col_lower:
                flagged.add(col)
                break

    # Pass 2: Presidio value scan on unflagged string columns
    unflagged_str_cols = [
        col for col in df.columns
        if col not in flagged and _is_string_column(df[col])
    ]

    if not unflagged_str_cols:
        return flagged

    try:
        from presidio_analyzer import AnalyzerEngine
    except ImportError:
        logger.warning(
            "presidio-analyzer not installed; skipping value-scan PII detection. "
            "Install with: pip install 'presidio-analyzer>=2.2'"
        )
        return flagged

    if not _spacy_available():
        logger.warning(
            "spaCy model 'en_core_web_lg' not found; skipping value-scan PII detection. "
            "Install with: python -m spacy download en_core_web_lg"
        )
        return flagged

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            analyzer = AnalyzerEngine()

        for col in unflagged_str_cols:
            sample_values = (
                df[col]
                .dropna()
                .astype(str)
                .head(100)
                .tolist()
            )
            for value in sample_values:
                results = analyzer.analyze(text=value, language="en")
                if results:
                    flagged.add(col)
                    break  # one hit is enough for this column
    except Exception as exc:
        logger.warning(
            "PII value-scan failed (%s); proceeding with name-heuristic results only.",
            exc,
        )

    return flagged


def _is_string_column(series: pd.Series) -> bool:
    """Return True if the series contains string/object data."""
    return pd.api.types.is_string_dtype(series)
