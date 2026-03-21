"""Grain verification, join cardinality, and layer-specific lint.

Usage:
    python -m scripts.grain --select fct_reservations
    python -m scripts.grain --select int_parks --output markdown
    python -m scripts.grain --select stg_vistareserve__reservations --checks staging
"""
from __future__ import annotations

import argparse
import logging
import sys


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Grain verification, join cardinality, and layer-specific lint.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--select", "-s", required=True, metavar="SELECTOR",
        help="dbt model selector (e.g. fct_reservations, int_parks)",
    )
    parser.add_argument(
        "--output", "-o", default="terminal", metavar="MODE",
        help="Output mode: terminal, markdown, llm (default: terminal)",
    )
    parser.add_argument(
        "--checks", default="all", metavar="CHECKS",
        help="Comma-separated checks: grain, joins, lint, all (default: all)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

    from scripts._core.selector import resolve_selector, _determine_layer

    try:
        targets = resolve_selector(args.select)
    except Exception as exc:
        print(f"Error resolving selector: {exc}", file=sys.stderr)
        return 1

    checks = set(args.checks.split(",")) if args.checks != "all" else {"grain", "joins", "lint"}
    exit_code = 0

    for target in targets:
        layer = _determine_layer(target.table)

        if "grain" in checks:
            from scripts.grain.key_discovery import run_key_discovery
            run_key_discovery(target, args.output)

        if "joins" in checks:
            from scripts.grain.join_analysis import run_join_analysis
            run_join_analysis(target, args.output)

        if "lint" in checks:
            if layer == "staging" or layer == "base":
                from scripts.grain.staging_lint import run_staging_lint
                run_staging_lint(target, args.output)
            elif layer == "integration":
                from scripts.grain.integration_lint import run_integration_lint
                run_integration_lint(target, args.output)
            elif layer == "marts":
                from scripts.grain.mart_lint import run_mart_lint
                run_mart_lint(target, args.output)

            from scripts.grain.dag_lint import run_dag_lint
            run_dag_lint(target, args.output)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
