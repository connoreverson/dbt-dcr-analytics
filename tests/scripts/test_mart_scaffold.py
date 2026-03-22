from __future__ import annotations

from scripts.scaffold.mart_scaffold import generate_fact_sql, generate_dimension_sql, generate_report_sql


def test_generate_fact_sql():
    sql = generate_fact_sql(
        name="fct_permits",
        grain="one row per permit application",
        dimensions=["dim_parks", "dim_customers", "dim_date"],
        measures=["permit_fee", "processing_days"],
    )
    assert "parks_sk" in sql
    assert "customer" in sql.lower()
    assert "date_key" in sql
    assert "permit_fee" in sql
    # Should not have descriptive attributes
    assert "Descriptive attributes come from dimensions" in sql


def test_generate_dimension_sql():
    sql = generate_dimension_sql(
        name="dim_applicants",
        grain="one row per applicant organization",
        key="applicant_id",
    )
    assert "applicants_sk" in sql
    assert "generate_surrogate_key" in sql
    assert "applicant_id" in sql


def test_generate_report_sql():
    sql = generate_report_sql(
        name="rpt_park_revenue_summary",
        facts=["fct_reservations", "fct_pos_transactions"],
        grain="one row per park per month",
    )
    assert "fct_reservations" in sql
    assert "fct_pos_transactions" in sql
    assert "group by" in sql.lower()
    assert "combines" in sql.lower()
