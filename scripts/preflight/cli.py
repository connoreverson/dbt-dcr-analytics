"""Analyst self-check before PR.

Usage:
    python -m scripts.preflight --select int_grant_applications
    python -m scripts.preflight --select fct_reservations --skip-build
"""
from __future__ import annotations

import argparse
import logging
import sys


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preflight check: compile, build, grain, lint, tests, YAML alignment.",
    )
    parser.add_argument(
        "--select", "-s", required=True, metavar="SELECTOR",
        help="dbt model selector",
    )
    parser.add_argument(
        "--skip-build", action="store_true",
        help="Skip compile + build steps (use when model already builds)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

    from scripts.preflight.checks import run_preflight
    return run_preflight(args.select, skip_build=args.skip_build)


if __name__ == "__main__":
    sys.exit(main())
