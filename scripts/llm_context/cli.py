# scripts/llm_context/cli.py
"""LLM context generation, CDM advisor, and guided intake.

Usage:
    python -m scripts.llm_context new-model
    python -m scripts.llm_context cdm-match --concept "grant application"
    python -m scripts.llm_context model-summary --select int_parks
    python -m scripts.llm_context source-summary --select source:peoplefirst.employees
"""
from __future__ import annotations

import argparse
import logging
import sys


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the llm_context package.

    Args:
        argv: Argument list to parse. Defaults to sys.argv[1:] when None.

    Returns:
        Parsed namespace with `subcommand` and subcommand-specific attributes.
    """
    parser = argparse.ArgumentParser(
        description="LLM context generation, CDM advisor, and guided intake.",
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # new-model
    subparsers.add_parser("new-model", help="Guided intake questionnaire")

    # cdm-match
    sub_cdm = subparsers.add_parser("cdm-match", help="CDM entity matching")
    sub_cdm.add_argument("--concept", required=True, help="Business concept to match")
    sub_cdm.add_argument(
        "--source-columns", default="",
        help="Comma-separated source column names for column overlap bonus",
    )

    # model-summary
    sub_model = subparsers.add_parser("model-summary", help="Summarize existing model for LLM")
    sub_model.add_argument("--select", "-s", required=True, help="dbt model selector")
    sub_model.add_argument(
        "--include-standards",
        action="store_true",
        default=False,
        help="Append layer-applicable governance standards (for fresh LLM sessions)",
    )

    # source-summary
    sub_source = subparsers.add_parser("source-summary", help="Summarize source table for LLM")
    sub_source.add_argument("--select", "-s", required=True, help="dbt source selector")

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Entry point for the llm_context CLI.

    Args:
        argv: Argument list. Defaults to sys.argv[1:] when None.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    args = parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

    if args.subcommand == "new-model":
        from scripts.llm_context.new_model import run_new_model
        return run_new_model()

    elif args.subcommand == "cdm-match":
        from scripts.llm_context.cdm_advisor import run_cdm_match
        columns = [c.strip() for c in args.source_columns.split(",") if c.strip()]
        return run_cdm_match(args.concept, source_columns=columns)

    elif args.subcommand == "model-summary":
        from scripts.llm_context.model_context import run_model_summary
        return run_model_summary(args.select, include_standards=args.include_standards)

    elif args.subcommand == "source-summary":
        from scripts.llm_context.source_context import run_source_summary
        return run_source_summary(args.select)

    else:
        raise AssertionError(f"Unhandled subcommand: {args.subcommand}")


if __name__ == "__main__":
    sys.exit(main())
