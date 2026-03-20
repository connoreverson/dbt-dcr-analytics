from __future__ import annotations

import logging

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from scripts._core.models import AnalysisResult

logger = logging.getLogger(__name__)

console = Console()


def render_terminal(result: AnalysisResult) -> None:
    """Render a profiling result to the terminal using skimpy + rich.

    PII-flagged columns are highlighted in yellow but NOT redacted —
    terminal output is a local surface.

    On Windows/Git Bash, prefix invocation with PYTHONUTF8=1 to avoid
    cp1252 encoding errors on skimpy's rich console output.
    """
    try:
        from skimpy import skim
    except ImportError:
        logger.warning(
            "skimpy not installed; skipping compact stats table. "
            "Install with: pip install 'skimpy>=0.0.12'"
        )
        skim = None

    console.rule(f"[bold blue]Profile: {result.target.table}[/bold blue]")
    console.print(
        f"[dim]Profiled at: {result.profiled_at.strftime('%Y-%m-%d %H:%M:%S UTC')} | "
        f"Sample: {len(result.sample):,} rows | "
        f"Columns: {len(result.sample.columns)}[/dim]"
    )

    if skim is not None:
        try:
            console.print()
            skim(result.sample)
        except Exception as exc:
            logger.warning("skimpy.skim() failed: %s", exc)

    # Signals panel
    if result.dbt_signals:
        signal_text = Text()
        for sig in result.dbt_signals:
            color = {
                "CAST_HINT": "cyan",
                "RENAME_HINT": "yellow",
                "UNUSED_COLUMN": "red",
                "NULL_PATTERN": "magenta",
            }.get(sig.signal_type, "white")
            signal_text.append(f"[{sig.signal_type}] ", style=f"bold {color}")
            signal_text.append(f"{sig.column_name}: {sig.message}\n")
        console.print(Panel(signal_text, title="dbt Signals", border_style="blue"))
    else:
        console.print(Panel("[dim]No signals detected.[/dim]", title="dbt Signals", border_style="dim"))

    # PII panel
    if result.pii_columns:
        pii_text = Text()
        for col in sorted(result.pii_columns):
            pii_text.append(f"  \u26a0 {col}\n", style="bold yellow")
        console.print(Panel(pii_text, title="PII Columns", border_style="yellow"))
    else:
        console.print(Panel("[dim]No PII columns detected.[/dim]", title="PII Columns", border_style="dim"))
