from __future__ import annotations

from scripts.preflight.cli import parse_args


def test_parse_basic():
    args = parse_args(["--select", "int_parks"])
    assert args.select == "int_parks"


def test_parse_skip_build():
    args = parse_args(["--select", "int_parks", "--skip-build"])
    assert args.skip_build is True
