# tests/scripts/test_llm_context_cli.py
from scripts.llm_context.cli import parse_args


def test_parse_cdm_match():
    args = parse_args(["cdm-match", "--concept", "grant application"])
    assert args.subcommand == "cdm-match"
    assert args.concept == "grant application"


def test_parse_cdm_match_with_columns():
    args = parse_args([
        "cdm-match", "--concept", "park", "--source-columns", "id,name,acres"
    ])
    assert args.source_columns == "id,name,acres"


def test_parse_model_summary():
    args = parse_args(["model-summary", "--select", "int_parks"])
    assert args.subcommand == "model-summary"
    assert args.select == "int_parks"


def test_parse_source_summary():
    args = parse_args(["source-summary", "--select", "source:peoplefirst.employees"])
    assert args.subcommand == "source-summary"
    assert args.select == "source:peoplefirst.employees"


def test_parse_new_model():
    args = parse_args(["new-model"])
    assert args.subcommand == "new-model"
