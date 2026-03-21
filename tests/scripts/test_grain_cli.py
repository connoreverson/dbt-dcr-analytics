# tests/scripts/test_grain_cli.py
from scripts.grain.cli import parse_args


def test_parse_args_basic():
    args = parse_args(["--select", "fct_reservations"])
    assert args.select == "fct_reservations"
    assert args.output == "terminal"


def test_parse_args_with_output():
    args = parse_args(["--select", "int_parks", "--output", "markdown"])
    assert args.output == "markdown"


def test_parse_args_with_checks():
    args = parse_args(["--select", "fct_reservations", "--checks", "grain,joins"])
    assert args.checks == "grain,joins"
