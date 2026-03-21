# tests/scripts/test_join_analysis.py
from scripts.grain.join_analysis import classify_cardinality, extract_joins


def test_extract_joins_single_left_join():
    sql = """
    select a.id, b.name
    from orders a
    left join customers b on a.customer_id = b.customer_id
    """
    joins = extract_joins(sql)
    assert len(joins) == 1
    assert joins[0]["join_type"] == "LEFT"
    assert "customer_id" in joins[0]["on_condition"]


def test_extract_joins_multiple():
    sql = """
    select o.id, c.name, p.product_name
    from orders o
    inner join customers c on o.customer_id = c.customer_id
    left join products p on o.product_id = p.product_id
    """
    joins = extract_joins(sql)
    assert len(joins) == 2
    assert joins[0]["join_type"] == "INNER"
    assert joins[1]["join_type"] == "LEFT"


def test_extract_joins_no_joins():
    sql = "select id, name from customers"
    joins = extract_joins(sql)
    assert len(joins) == 0


def test_extract_joins_cte():
    sql = """
    with source as (
        select * from raw_data
    ),
    enriched as (
        select s.id, d.label
        from source s
        left join dim_types d on s.type_id = d.type_id
    )
    select * from enriched
    """
    joins = extract_joins(sql)
    assert len(joins) == 1
    assert joins[0]["join_type"] == "LEFT"


def test_classify_cardinality_one_to_one():
    result = classify_cardinality(left_distinct=100, right_distinct=100, result_rows=100, left_rows=100)
    assert result["cardinality"] == "1:1"
    assert result["fan_out"] is False
    assert result["expansion_ratio"] == 1.0


def test_classify_cardinality_fan_out():
    result = classify_cardinality(left_distinct=50, right_distinct=10, result_rows=150, left_rows=100)
    assert result["cardinality"] == "1:M"
    assert result["fan_out"] is True


def test_classify_cardinality_many_to_many():
    # Equal distinct counts but result expands -- should be M:M, not 1:M
    result = classify_cardinality(left_distinct=100, right_distinct=100, result_rows=200, left_rows=100)
    assert result["cardinality"] == "M:M"
    assert result["fan_out"] is True


def test_classify_cardinality_many_to_one():
    result = classify_cardinality(left_distinct=10, right_distinct=100, result_rows=100, left_rows=100)
    assert result["cardinality"] == "M:1"
    assert result["fan_out"] is False
