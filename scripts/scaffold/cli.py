# scripts/scaffold/cli.py
"""Test and model scaffolding.

Usage:
    python -m scripts.scaffold tests --select stg_vistareserve__reservations
    python -m scripts.scaffold tests --select stg_test --apply
    python -m scripts.scaffold integration --entity Request --sources stg_a stg_b --key request_id
    python -m scripts.scaffold fact --name fct_permits --grain "one row per permit" --dimensions dim_parks
    python -m scripts.scaffold freshness --select source:peoplefirst
"""
from __future__ import annotations

import argparse
import logging
import sys


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the scaffold package.

    Args:
        argv: Argument list to parse. Defaults to sys.argv[1:] when None.

    Returns:
        Parsed namespace with ``subcommand`` and subcommand-specific attributes.
    """
    parser = argparse.ArgumentParser(description="Test and model scaffolding.")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # tests
    sub_tests = subparsers.add_parser("tests", help="Generate missing YAML tests")
    sub_tests.add_argument("--select", "-s", required=True, help="dbt model selector")
    sub_tests.add_argument("--apply", action="store_true", help="Write into YAML file")

    # integration
    sub_int = subparsers.add_parser("integration", help="Generate integration model skeleton")
    sub_int.add_argument("--entity", required=True, help="CDM entity name")
    sub_int.add_argument("--sources", nargs="+", required=True, help="Source model names")
    sub_int.add_argument("--key", required=True, help="Primary key column")

    # fact
    sub_fact = subparsers.add_parser("fact", help="Generate fact model skeleton")
    sub_fact.add_argument("--name", required=True, help="Model name")
    sub_fact.add_argument("--grain", required=True, help="Grain description")
    sub_fact.add_argument("--dimensions", nargs="+", default=[], help="Dimension models to join")
    sub_fact.add_argument("--measures", default="", help="Comma-separated measure columns")

    # dimension
    sub_dim = subparsers.add_parser("dimension", help="Generate dimension model skeleton")
    sub_dim.add_argument("--name", required=True, help="Model name")
    sub_dim.add_argument("--grain", required=True, help="Grain description")
    sub_dim.add_argument("--key", required=True, help="Natural key column")

    # report
    sub_rpt = subparsers.add_parser("report", help="Generate report model skeleton")
    sub_rpt.add_argument("--name", required=True, help="Model name")
    sub_rpt.add_argument("--facts", nargs="+", required=True, help="Fact models to combine")
    sub_rpt.add_argument("--grain", required=True, help="Aggregation grain")

    # freshness
    sub_fresh = subparsers.add_parser("freshness", help="Generate source freshness YAML")
    sub_fresh.add_argument("--select", "-s", required=True, help="dbt source selector")
    sub_fresh.add_argument("--apply", action="store_true", help="Write into source YAML")

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Entry point for the scaffold CLI.

    Args:
        argv: Argument list. Defaults to sys.argv[1:] when None.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    args = parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

    if args.subcommand == "tests":
        from scripts.scaffold.test_scaffold import run_test_scaffold

        return run_test_scaffold(args.select, apply_changes=args.apply)
    elif args.subcommand == "integration":
        from scripts.scaffold.integration_scaffold import run_integration_scaffold

        return run_integration_scaffold(args.entity, args.sources, args.key)
    elif args.subcommand in ("fact", "dimension", "report"):
        from scripts.scaffold.mart_scaffold import run_mart_scaffold

        return run_mart_scaffold(args)
    elif args.subcommand == "freshness":
        from scripts.scaffold.source_freshness_scaffold import run_freshness_scaffold

        return run_freshness_scaffold(args.select, apply_changes=args.apply)
    else:
        raise AssertionError(f"Unhandled subcommand: {args.subcommand}")


if __name__ == "__main__":
    sys.exit(main())
