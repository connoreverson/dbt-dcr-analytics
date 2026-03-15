#!/usr/bin/env python3
"""dbt-profiler CLI entrypoint.

Usage:
    PYTHONUTF8=1 python scripts/profiler/cli.py --select stg_parks__facilities
    PYTHONUTF8=1 python scripts/profiler/cli.py --select "source:reservations.transactions" --output markdown
    PYTHONUTF8=1 python scripts/profiler/cli.py --select fct_reservations --output terminal,markdown,html --sample 5000
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
        help="Comma-separated output modes: terminal, markdown, html, or all (default: terminal)",
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
        "--sanitize-html",
        action="store_true",
        help="Redact PII in HTML sample rows (slower; for LLM-safe sharing)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show full tracebacks on error",
    )
    return parser.parse_args(argv)


def resolve_output_modes(output_str: str) -> set[str]:
    """Expand 'all' and validate output modes."""
    valid = {"terminal", "markdown", "html"}
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


def profile_target(target, args) -> None:
    """Run the full profiling pipeline for a single SelectionTarget."""
    from scripts.profiler.connectors.duckdb import DuckDBConnector
    from scripts.profiler.connectors.bigquery import BigQueryConnector
    from scripts.profiler.analyzers.stats import profile_dataframe
    from scripts.profiler.analyzers.pii import detect_pii
    from scripts.profiler.analyzers.dbt_signals import detect_signals

    # Connect and fetch data
    if target.connector_type == "duckdb":
        connector = DuckDBConnector(target)
    else:
        connector = BigQueryConnector(target)

    try:
        df = connector.get_sample(args.sample)
    finally:
        if hasattr(connector, "close"):
            connector.close()

    # Run analyzers
    modes = resolve_output_modes(args.output)
    needs_full_stats = "html" in modes or "markdown" in modes

    if needs_full_stats:
        result = profile_dataframe(df, target, full_profile=args.full_profile)
    else:
        # Terminal-only: skip ydata-profiling for speed (still need result object)
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
        from scripts.profiler.renderers.terminal import render_terminal

        render_terminal(result)

    if "markdown" in modes:
        from scripts.profiler.renderers.markdown import render_markdown

        out = render_markdown(result)
        print(f"Markdown: {out}")

    if "html" in modes:
        from scripts.profiler.renderers.html import render_html

        out = render_html(result, sanitize_html=args.sanitize_html)
        print(f"HTML:     {out}")


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
            profile_target(target, args)
        except Exception as exc:
            if args.verbose:
                raise
            print(f"Error profiling {target.table}: {exc}", file=sys.stderr)
            exit_code = 1

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
