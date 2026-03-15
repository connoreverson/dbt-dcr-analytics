from __future__ import annotations

import logging
from pathlib import Path

from scripts.profiler.models import AnalysisResult
from scripts.profiler.sanitizer import sanitize

logger = logging.getLogger(__name__)

_TMP_DIR = Path("tmp")


def render_html(result: AnalysisResult, sanitize_html: bool = False) -> Path:
    """Render a profiling result to an interactive ydata-profiling HTML report.

    Prepends a custom signals and PII section as the first child of <body>.

    When sanitize_html=True, builds a second ProfileReport from the sanitized
    DataFrame before rendering. This is intentionally more expensive and is
    intended for LLM-safe sharing, not routine use.

    Args:
        result: The AnalysisResult to render.
        sanitize_html: If True, redact PII in sample rows before rendering.

    Returns:
        Path to the written .html file.

    Raises:
        ImportError: if ydata-profiling is not installed.
        RuntimeError: if result.profile is None (no profiling was run).
    """
    if result.profile is None:
        raise RuntimeError(
            "result.profile is None — HTML renderer requires a ydata-profiling "
            "ProfileReport. Run with --output html after profiling."
        )

    timestamp = result.profiled_at.strftime("%Y%m%d_%H%M%S")
    out_path = _TMP_DIR / f"profile_{result.target.table}_{timestamp}.html"
    _TMP_DIR.mkdir(parents=True, exist_ok=True)

    if sanitize_html and result.pii_columns:
        # Build a second ProfileReport from the sanitized frame
        try:
            from ydata_profiling import ProfileReport
        except ImportError:
            raise ImportError(
                "ydata-profiling is required for HTML output: "
                "pip install 'ydata-profiling>=4.6'"
            )
        sanitized_df = sanitize(result.sample, result.pii_columns)
        profile_to_render = ProfileReport(
            sanitized_df,
            minimal=True,
            title=result.target.table,
            progress_bar=False,
        )
    elif sanitize_html and not result.pii_columns:
        logger.info("--sanitize-html requested but no PII columns detected; rendering unsanitized.")
        profile_to_render = result.profile
    else:
        profile_to_render = result.profile

    report_html: str = profile_to_render.to_html()

    # Build signals section HTML
    signals_div = _render_signals_section(result)

    # Inject signals <div> immediately after <body> opening tag
    if "<body>" in report_html:
        combined = report_html.replace("<body>", "<body>" + signals_div, 1)
    else:
        # Fallback: prepend signals before the HTML (malformed but usable)
        logger.warning("Could not find <body> tag in HTML report; prepending signals block.")
        combined = signals_div + report_html

    out_path.write_text(combined, encoding="utf-8")
    logger.info("HTML profile written to %s", out_path)
    return out_path


def _render_signals_section(result: AnalysisResult) -> str:
    """Build a self-contained <div> with dbt signals and PII column list."""
    parts = [
        '<div id="profiler-signals" style="font-family:monospace;padding:16px;'
        'background:#1e1e2e;color:#cdd6f4;margin-bottom:16px;">'
    ]

    parts.append("<h2>dbt Signals</h2>")
    if result.dbt_signals:
        parts.append("<ul>")
        for sig in result.dbt_signals:
            color = {
                "CAST_HINT": "#89b4fa",
                "RENAME_HINT": "#f9e2af",
                "UNUSED_COLUMN": "#f38ba8",
                "NULL_PATTERN": "#cba6f7",
            }.get(sig.signal_type, "#cdd6f4")
            parts.append(
                f'<li><span style="color:{color};font-weight:bold">[{sig.signal_type}]</span> '
                f"<code>{sig.column_name}</code>: {sig.message}</li>"
            )
        parts.append("</ul>")
    else:
        parts.append("<p><em>No signals detected.</em></p>")

    parts.append("<h2>PII Columns</h2>")
    if result.pii_columns:
        parts.append("<ul>")
        for col in sorted(result.pii_columns):
            parts.append(f'<li><code style="color:#f9e2af">{col}</code></li>')
        parts.append("</ul>")
    else:
        parts.append("<p><em>No PII columns detected.</em></p>")

    parts.append("</div>")
    return "".join(parts)
