#!/usr/bin/env python3
"""dbt-profiler CLI entrypoint.

Usage:
    PYTHONUTF8=1 python scripts/profiler/cli.py --select stg_parks__facilities
    PYTHONUTF8=1 python scripts/profiler/cli.py --select "source:reservations.transactions" --output markdown
    PYTHONUTF8=1 python scripts/profiler/cli.py --select fct_reservations --output terminal,markdown,html --sample 5000
    PYTHONUTF8=1 python scripts/profiler/cli.py --select fct_reservations --output llm
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Profile a dbt node (source or model) and output statistics.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--select", "-s",
        required=True,
        metavar="SELECTOR",
        help="dbt node selector (e.g. stg_parks__facilities or source:reservations.transactions)",
    )
    parser.add_argument(
        "--output", "-o",
        default="terminal",
        metavar="MODES",
        help="Comma-separated output modes: terminal, markdown, html, llm, or all (default: terminal)",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=1000,
        metavar="N",
        help="Number of rows to sample (default: 1000)",
    )
    parser.add_argument(
        "--full-profile",
        action="store_true",
        help="Enable full ydata-profiling (correlations, interactions -- slower)",
    )
    parser.add_argument(
        "--env",
        choices=["local", "prod"],
        default="local",
        help="Environment: local (DuckDB) or prod (BigQuery) (default: local)",
    )
    parser.add_argument(
        "--sanitize-pii",
        action="store_true",
        help="Redact PII values in output (slower; for LLM-safe sharing)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show full tracebacks on error",
    )
    return parser.parse_args(argv)


def resolve_output_modes(output_str: str) -> set[str]:
    """Expand 'all' and validate output modes."""
    valid = {"terminal", "markdown", "html", "llm"}
    if output_str.strip().lower() == "all":
        return valid
    modes = {m.strip().lower() for m in output_str.split(",")}
    invalid = modes - valid
    if invalid:
        raise ValueError(
            f"Invalid output mode(s): {', '.join(sorted(invalid))}. "
            f"Valid options: {', '.join(sorted(valid))}"
        )
    return modes


def _render_quick_stats_table(quick_stats: dict, table_name: str) -> None:
    """Render warehouse-side quick stats as a rich Table."""
    from rich.console import Console
    from rich.table import Table as RichTable

    console = Console()
    console.rule(f"[bold blue]Warehouse Stats: {table_name}[/bold blue]")

    tbl = RichTable(show_header=True, header_style="bold cyan", box=None, padding=(0, 1))
    tbl.add_column("Column", style="bold", no_wrap=True)
    tbl.add_column("Total", justify="right")
    tbl.add_column("Nulls", justify="right")
    tbl.add_column("Null %", justify="right")
    tbl.add_column("Distinct", justify="right")
    tbl.add_column("Unique %", justify="right")
    tbl.add_column("Min", justify="right", style="dim")
    tbl.add_column("Max", justify="right", style="dim")
    tbl.add_column("Top Values", style="dim")

    for col, s in quick_stats.items():
        null_pct = f"{s['null_rate'] * 100:.1f}%"
        uniq_pct = f"{s['uniqueness_ratio'] * 100:.1f}%"
        top_vals = ", ".join(str(v) for v in (s.get("top_values") or [])[:3])
        tbl.add_row(
            col,
            str(s["total_count"]),
            str(s["null_count"]),
            null_pct,
            str(s["distinct_count"]),
            uniq_pct,
            str(s.get("min") or ""),
            str(s.get("max") or ""),
            top_vals,
        )

    console.print(tbl)


def profile_target(target, args, modes: set[str]) -> None:
    """Run the full profiling pipeline for a single SelectionTarget."""
    from scripts._core.connectors.duckdb import DuckDBConnector
    from scripts._core.connectors.bigquery import BigQueryConnector
    from scripts.profiler.analyzers.pii import detect_pii
    from scripts.profiler.analyzers.dbt_signals import detect_signals

    # html/markdown require a ydata-profiling ProfileReport — auto-upgrade if needed
    needs_full_profile = args.full_profile or "html" in modes or "markdown" in modes

    # Connect
    if target.connector_type == "duckdb":
        connector = DuckDBConnector(target)
    else:
        connector = BigQueryConnector(target)

    quick_stats: dict | None = None
    try:
        if needs_full_profile:
            # Full mode: fetch sample DataFrame for ydata-profiling
            df = connector.get_sample(args.sample)
        else:
            # Quick mode: run SQL-based stats warehouse-side, no large data transfer
            from scripts.profiler.analyzers.stats import (
                build_quick_profile_sql,
                parse_quick_profile_result,
            )
            schema = connector.target.schema or "main"
            table = connector.target.table
            try:
                columns = [c.name for c in connector.get_schema()]
            except Exception:
                # Fall back to fetching a tiny sample to get column names
                df_tmp = connector.get_sample(1)
                columns = list(df_tmp.columns)

            sql = build_quick_profile_sql(schema, table, columns, dialect=target.connector_type)
            quick_stats = parse_quick_profile_result(connector.run_query(sql))

            # Small sample for PII detection and grain analysis
            df = connector.get_sample(min(args.sample, 200))
    finally:
        if hasattr(connector, "close"):
            connector.close()

    # Grain / candidate key analysis — shown at top of every profile
    try:
        from scripts.grain.key_discovery import find_candidate_keys
        candidates = find_candidate_keys(df) if df is not None else []
        if candidates:
            print(f"\nCANDIDATE KEYS:")
            for c in candidates[:3]:
                cols = ", ".join(c["columns"])
                print(f"  [{c['uniqueness_ratio']:.0%}] {cols}")
    except Exception:
        pass  # Grain analysis is best-effort

    # Build AnalysisResult
    if needs_full_profile:
        from scripts.profiler.analyzers.stats import profile_dataframe
        result = profile_dataframe(df, target, full_profile=args.full_profile)
    else:
        from scripts.profiler.models import AnalysisResult
        result = AnalysisResult(
            target=target,
            profile=None,
            description=None,
            sample=df,
            pii_columns=set(),
            dbt_signals=[],
        )

    result.pii_columns = detect_pii(df)
    if result.description is not None:
        result.dbt_signals = detect_signals(result.description)

    # Render outputs
    if "terminal" in modes:
        # Quick mode: show warehouse-side stats table first, then signals/PII panels
        if quick_stats is not None:
            _render_quick_stats_table(quick_stats, target.table)
        from scripts.profiler.renderers.terminal import render_terminal
        render_terminal(result)

    if "markdown" in modes:
        from scripts.profiler.renderers.markdown import render_markdown
        out = render_markdown(result, sanitize_pii=args.sanitize_pii)
        print(f"Markdown: {out}")

    if "html" in modes:
        from scripts.profiler.renderers.html import render_html
        out = render_html(result, sanitize_pii=args.sanitize_pii)
        print(f"HTML:     {out}")

    if "llm" in modes:
        from scripts._core.renderers.llm import render_llm_context
        sections: dict = {
            "Table": target.table,
            "Row Count": str(len(df)),
            "PII Columns": list(result.pii_columns) if result.pii_columns else ["none detected"],
        }
        if quick_stats is not None:
            sections["Column Stats"] = [
                f"{col}: nulls={s['null_rate']*100:.1f}%, "
                f"distinct={s['distinct_count']}, "
                f"unique={s['uniqueness_ratio']*100:.1f}%"
                + (
                    f", top=[{', '.join(str(v) for v in s.get('top_values', [])[:3])}]"
                    if s.get("top_values")
                    else ""
                )
                for col, s in quick_stats.items()
            ]
        print(render_llm_context(sections))


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")

    try:
        modes = resolve_output_modes(args.output)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    try:
        from scripts.profiler.selector import resolve_selector

        targets = resolve_selector(args.select, env=args.env)
    except Exception as exc:
        if args.verbose:
            raise
        print(f"Error resolving selector: {exc}", file=sys.stderr)
        return 1

    exit_code = 0
    for target in targets:
        try:
            profile_target(target, args, modes)
        except Exception as exc:
            if args.verbose:
                raise
            print(f"Error profiling {target.table}: {exc}", file=sys.stderr)
            exit_code = 1

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
