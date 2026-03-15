"""PII sanitizer for profiler output.

Called by renderers that need PII redaction. Returns a new DataFrame — never
mutates the original.
"""
from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def sanitize(df: pd.DataFrame, pii_columns: set[str]) -> pd.DataFrame:
    """Return a copy of df with PII column values replaced by redaction tokens.

    Calls presidio-anonymizer to produce typed redaction tokens like
    [REDACTED:EMAIL_ADDRESS]. Falls back to [REDACTED] if presidio-anonymizer
    is absent or fails.

    Args:
        df: The source DataFrame (never mutated).
        pii_columns: Set of column names to redact.

    Returns:
        A new DataFrame with PII columns redacted.
    """
    if not pii_columns:
        return df.copy()

    result = df.copy()

    try:
        from presidio_analyzer import AnalyzerEngine
        from presidio_anonymizer import AnonymizerEngine
        from presidio_anonymizer.entities import OperatorConfig

        analyzer = AnalyzerEngine()
        anonymizer = AnonymizerEngine()

        for col in pii_columns:
            if col not in result.columns:
                continue
            redacted_values = []
            for val in result[col]:
                if val is None or (isinstance(val, float) and pd.isna(val)):
                    redacted_values.append(val)
                    continue
                text = str(val)
                analysis = analyzer.analyze(text=text, language="en")
                if analysis:
                    # Use the entity type from the first (highest-score) result
                    entity_type = analysis[0].entity_type
                    anonymized = anonymizer.anonymize(
                        text=text,
                        analyzer_results=analysis,
                        operators={"DEFAULT": OperatorConfig(
                            "replace",
                            {"new_value": f"[REDACTED:{entity_type}]"}
                        )},
                    )
                    redacted_values.append(anonymized.text)
                else:
                    # Presidio found no entities — use generic redaction
                    redacted_values.append("[REDACTED]")
            result[col] = redacted_values

    except ImportError:
        logger.warning(
            "presidio-anonymizer not installed; using generic [REDACTED] tokens. "
            "Install with: pip install 'presidio-anonymizer>=2.2'"
        )
        for col in pii_columns:
            if col in result.columns:
                result[col] = result[col].apply(
                    lambda v: "[REDACTED]" if v is not None else v
                )

    except Exception as exc:
        logger.warning(
            "Presidio anonymization failed (%s); using generic [REDACTED] tokens.", exc
        )
        for col in pii_columns:
            if col in result.columns:
                result[col] = result[col].apply(
                    lambda v: "[REDACTED]" if v is not None else v
                )

    return result
