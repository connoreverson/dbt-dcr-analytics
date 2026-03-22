# tests/scripts/test_test_scaffold.py
import pandas as pd
from scripts.scaffold.test_scaffold import (
    suggest_tests_for_column,
    detect_hardcoded_case,
)


def test_suggest_tests_id_column():
    """_id columns should get not_null + unique."""
    suggestions = suggest_tests_for_column(
        col_name="reservation_id",
        dtype="VARCHAR",
        series=pd.Series(["R001", "R002", "R003"]),
        existing_tests=[],
    )
    assert any(s["test"] == "not_null" for s in suggestions)
    assert any(s["test"] == "unique" for s in suggestions)


def test_suggest_tests_sk_column():
    """_sk columns should get not_null + unique."""
    suggestions = suggest_tests_for_column(
        col_name="parks_sk",
        dtype="VARCHAR",
        series=pd.Series(["sk1", "sk2", "sk3"]),
        existing_tests=[],
    )
    assert any(s["test"] == "not_null" for s in suggestions)
    assert any(s["test"] == "unique" for s in suggestions)


def test_suggest_tests_low_cardinality():
    """Low cardinality categorical columns get accepted_values."""
    suggestions = suggest_tests_for_column(
        col_name="status",
        dtype="VARCHAR",
        series=pd.Series(["active", "inactive", "active", "pending"]),
        existing_tests=[],
    )
    assert any(s["test"] == "accepted_values" for s in suggestions)


def test_suggest_tests_already_covered():
    """Don't suggest tests that already exist."""
    suggestions = suggest_tests_for_column(
        col_name="reservation_id",
        dtype="VARCHAR",
        series=pd.Series(["R001", "R002"]),
        existing_tests=["not_null", "unique"],
    )
    assert len(suggestions) == 0


def test_detect_hardcoded_case():
    sql = """
    select
        case when type = 'A' then 'Active'
             when type = 'I' then 'Inactive'
             when type = 'P' then 'Pending' end as status_label
    from source
    """
    cases = detect_hardcoded_case(sql)
    assert len(cases) >= 1
    assert cases[0]["column"] == "status_label"
    assert "A" in str(cases[0]["values"])


def test_detect_no_case():
    sql = "select id, name from source"
    cases = detect_hardcoded_case(sql)
    assert len(cases) == 0
