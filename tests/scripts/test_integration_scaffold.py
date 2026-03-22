from __future__ import annotations

from scripts.scaffold.integration_scaffold import generate_integration_sql, generate_integration_yaml


def test_generate_integration_sql():
    sql = generate_integration_sql(
        model_name="int_grants",
        entity="Grant",
        sources=["stg_grantwatch__applications", "stg_grantwatch__amendments"],
        key_column="application_id",
    )
    assert "grants_sk" in sql
    assert "generate_surrogate_key" in sql
    assert "stg_grantwatch__applications" in sql
    assert "stg_grantwatch__amendments" in sql
    assert "union all" in sql.lower()


def test_generate_integration_sql_single_source():
    sql = generate_integration_sql(
        model_name="int_permits",
        entity="Permit",
        sources=["stg_vistareserve__permits"],
        key_column="permit_id",
    )
    assert "permits_sk" in sql
    assert "union all" not in sql.lower()


def test_generate_integration_yaml():
    yaml_str = generate_integration_yaml(
        model_name="int_grants",
        entity="Grant",
        grain="one row per grant application",
        key_column="application_id",
    )
    assert "int_grants" in yaml_str
    assert "grants_sk" in yaml_str
    assert "cdm_entity: Grant" in yaml_str
    assert "not_null" in yaml_str
