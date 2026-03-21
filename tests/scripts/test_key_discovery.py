# tests/scripts/test_key_discovery.py
import pandas as pd
import pytest
from scripts.grain.key_discovery import (
    compute_uniqueness_ratios,
    find_candidate_keys,
    check_yaml_test_coverage,
)


def test_compute_uniqueness_ratios():
    """Uniqueness ratio = count_distinct / total_rows."""
    df = pd.DataFrame({
        "id": [1, 2, 3, 4, 5],
        "category": ["a", "a", "b", "b", "c"],
        "constant": ["x", "x", "x", "x", "x"],
    })
    ratios = compute_uniqueness_ratios(df)
    assert ratios["id"] == 1.0
    assert ratios["category"] == pytest.approx(0.6)
    assert ratios["constant"] == pytest.approx(0.2)


def test_find_candidate_keys_single_column():
    """A perfectly unique column is a candidate key."""
    df = pd.DataFrame({
        "pk": [1, 2, 3],
        "name": ["a", "b", "c"],
        "group": ["x", "x", "y"],
    })
    candidates = find_candidate_keys(df)
    # pk and name are both perfectly unique
    assert candidates[0]["columns"] == ["pk"]
    assert candidates[0]["uniqueness_ratio"] == 1.0


def test_find_candidate_keys_composite():
    """Two columns together form a composite key."""
    df = pd.DataFrame({
        "a": [1, 1, 2, 2],
        "b": ["x", "y", "x", "y"],
        "c": [10, 10, 10, 10],
    })
    candidates = find_candidate_keys(df)
    composite = [c for c in candidates if len(c["columns"]) == 2]
    assert any(
        set(c["columns"]) == {"a", "b"} and c["uniqueness_ratio"] == 1.0
        for c in composite
    )


def test_check_yaml_test_coverage():
    """Identifies whether candidate key has unique test in YAML."""
    yaml_tests = {
        "pk_col": ["unique", "not_null"],
        "other_col": ["not_null"],
    }
    result = check_yaml_test_coverage(["pk_col"], yaml_tests)
    assert result["covered"] is True
    assert result["missing_tests"] == []

    result2 = check_yaml_test_coverage(["other_col"], yaml_tests)
    assert result2["covered"] is False
    assert "unique" in result2["missing_tests"]


def test_find_candidate_keys_empty():
    """Empty DataFrame returns no candidates."""
    df = pd.DataFrame({"id": [], "name": []})
    candidates = find_candidate_keys(df)
    assert candidates == []


def test_check_yaml_test_coverage_composite():
    """Composite key always needs unique_combination_of_columns."""
    yaml_tests = {
        "col_a": ["not_null"],
        "col_b": ["not_null"],
    }
    result = check_yaml_test_coverage(["col_a", "col_b"], yaml_tests)
    assert result["covered"] is False
    assert "unique_combination_of_columns" in result["missing_tests"]
