from scripts.scaffold.cli import parse_args


def test_parse_tests():
    args = parse_args(["tests", "--select", "stg_vistareserve__reservations"])
    assert args.subcommand == "tests"
    assert args.select == "stg_vistareserve__reservations"
    assert args.apply is False


def test_parse_tests_apply():
    args = parse_args(["tests", "--select", "stg_test", "--apply"])
    assert args.apply is True


def test_parse_integration():
    args = parse_args([
        "integration", "--entity", "Request",
        "--sources", "stg_a", "stg_b", "--key", "request_id",
    ])
    assert args.subcommand == "integration"
    assert args.entity == "Request"
    assert args.sources == ["stg_a", "stg_b"]


def test_parse_fact():
    args = parse_args([
        "fact", "--name", "fct_permits",
        "--grain", "one row per permit",
        "--dimensions", "dim_parks", "dim_customers",
    ])
    assert args.subcommand == "fact"
    assert args.name == "fct_permits"


def test_parse_freshness():
    args = parse_args(["freshness", "--select", "source:peoplefirst"])
    assert args.subcommand == "freshness"
    assert args.apply is False
