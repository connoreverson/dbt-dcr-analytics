from __future__ import annotations

import pytest

from scripts.profiler.cli import parse_args, resolve_output_modes


def test_parse_args_defaults():
    args = parse_args(["--select", "stg_parks__facilities"])
    assert args.select == "stg_parks__facilities"
    assert args.output == "terminal"
    assert args.sample == 1000
    assert args.env == "local"
    assert args.full_profile is False
    assert args.sanitize_html is False
    assert args.verbose is False


def test_parse_args_all_flags():
    args = parse_args([
        "--select", "fct_reservations",
        "--output", "terminal,markdown,html",
        "--sample", "5000",
        "--full-profile",
        "--env", "prod",
        "--sanitize-html",
        "--verbose",
    ])
    assert args.sample == 5000
    assert args.full_profile is True
    assert args.env == "prod"
    assert args.sanitize_html is True
    assert args.verbose is True


def test_resolve_output_modes_terminal():
    assert resolve_output_modes("terminal") == {"terminal"}


def test_resolve_output_modes_all():
    assert resolve_output_modes("all") == {"terminal", "markdown", "html", "llm"}


def test_resolve_output_modes_multiple():
    result = resolve_output_modes("terminal,markdown")
    assert result == {"terminal", "markdown"}


def test_resolve_output_modes_invalid_raises():
    with pytest.raises(ValueError, match="Invalid output mode"):
        resolve_output_modes("invalid_mode")


def test_resolve_output_modes_case_insensitive():
    assert resolve_output_modes("Terminal,Markdown") == {"terminal", "markdown"}
