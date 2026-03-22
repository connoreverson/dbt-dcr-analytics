from scripts.reviewer.cli import parse_args


def test_parse_select():
    args = parse_args(["--select", "int_parks"])
    assert args.select == "int_parks"
    assert args.branch is None


def test_parse_branch():
    args = parse_args(["--branch", "feature/grant-models"])
    assert args.branch == "feature/grant-models"
    assert args.select is None


def test_parse_summarize():
    args = parse_args(["summarize", "--input", "tmp/reviews/"])
    assert args.subcommand == "summarize"
    assert args.input == "tmp/reviews/"
