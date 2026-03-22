"""Connor's review tooling — automated checks, qualitative review, branch review.

Usage:
    python -m scripts.reviewer --select int_grant_applications
    python -m scripts.reviewer --branch feature/grant-models
    python -m scripts.reviewer summarize --input tmp/reviews/
"""
from __future__ import annotations

import argparse
import logging
import sys


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Review tooling: automated checks, qualitative review, branch review.",
    )
    subparsers = parser.add_subparsers(dest="subcommand")

    # Default mode (no subcommand) — review a model or branch
    parser.add_argument("--select", "-s", help="dbt model selector")
    parser.add_argument("--branch", "-b", help="Git branch to review (all changed models)")
    parser.add_argument("--output", "-o", default="terminal", help="Output mode")
    parser.add_argument("--agent", action="store_true", help="Agent-friendly output (suppress dbt noise)")

    # Summarize subcommand
    sub_sum = subparsers.add_parser("summarize", help="Summarize review findings")
    sub_sum.add_argument("--input", "-i", required=True, help="Directory with review files")

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

    if getattr(args, "subcommand", None) == "summarize":
        from scripts.reviewer.summarize import run_summarize
        return run_summarize(args.input)

    if args.branch:
        from scripts.reviewer.automated import run_branch_review
        return run_branch_review(args.branch, agent=args.agent)

    if args.select:
        from scripts.reviewer.automated import run_model_review
        return run_model_review(args.select, agent=args.agent)

    print("Error: provide --select or --branch", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
