# tests/scripts/test_mart_lint.py
from scripts.grain.mart_lint import (
    check_wide_fact,
    check_no_dimension_joins,
    check_single_fact_passthrough,
    check_no_aggregation,
)


def test_wide_fact_detected():
    """Fact with descriptive string columns and no FK should flag."""
    columns = {
        "reservation_sk": {"type": "VARCHAR"},
        "park_name": {"type": "VARCHAR"},
        "customer_email": {"type": "VARCHAR"},
        "region": {"type": "VARCHAR"},
        "amount": {"type": "NUMERIC"},
    }
    fk_columns = []  # no _sk or _id FK columns
    finding = check_wide_fact(columns, fk_columns)
    assert finding is not None
    assert finding["check"] == "wide_fact"
    assert "park_name" in finding["message"]


def test_fact_with_fks_ok():
    """Fact with FK columns for its descriptive attributes is fine."""
    columns = {
        "reservation_sk": {"type": "VARCHAR"},
        "parks_sk": {"type": "VARCHAR"},
        "customer_sk": {"type": "VARCHAR"},
        "amount": {"type": "NUMERIC"},
    }
    fk_columns = ["parks_sk", "customer_sk"]
    finding = check_wide_fact(columns, fk_columns)
    assert finding is None


def test_no_dimension_joins():
    depends_on = [
        "model.dcr_analytics.int_financial_transactions",
        "model.dcr_analytics.int_parks",
    ]
    finding = check_no_dimension_joins(depends_on)
    assert finding is not None  # no dim_ in depends_on


def test_has_dimension_joins():
    depends_on = [
        "model.dcr_analytics.int_parks",
        "model.dcr_analytics.dim_parks",
    ]
    finding = check_no_dimension_joins(depends_on)
    assert finding is None


def test_single_fact_passthrough():
    depends_on = ["model.dcr_analytics.fct_reservations"]
    finding = check_single_fact_passthrough(depends_on)
    assert finding is not None


def test_multi_fact_report():
    depends_on = [
        "model.dcr_analytics.fct_reservations",
        "model.dcr_analytics.fct_pos_transactions",
    ]
    finding = check_single_fact_passthrough(depends_on)
    assert finding is None


def test_no_aggregation():
    sql = "select * from fct_reservations"
    finding = check_no_aggregation(sql)
    assert finding is not None


def test_has_aggregation():
    sql = """
    select park_id, count(*) as reservation_count
    from fct_reservations
    group by park_id
    """
    finding = check_no_aggregation(sql)
    assert finding is None
