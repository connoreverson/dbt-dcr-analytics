# tests/scripts/test_dag_lint.py
from scripts.grain.dag_lint import check_dependency_direction, VALID_DIRECTIONS


def test_staging_to_source_valid():
    findings = check_dependency_direction(
        model_name="stg_vistareserve__reservations",
        model_layer="staging",
        depends_on=["source.dcr_analytics.vistareserve.reservations"],
    )
    assert len(findings) == 0


def test_staging_to_integration_invalid():
    findings = check_dependency_direction(
        model_name="stg_bad_model",
        model_layer="staging",
        depends_on=["model.dcr_analytics.int_parks"],
    )
    assert len(findings) == 1
    assert findings[0]["check"] == "reverse_reference"


def test_integration_to_integration_warning():
    findings = check_dependency_direction(
        model_name="int_cases_enriched",
        model_layer="integration",
        depends_on=[
            "model.dcr_analytics.stg_salesforce__cases",
            "model.dcr_analytics.int_parks",
        ],
    )
    same_layer = [f for f in findings if f["check"] == "same_layer_reference"]
    assert len(same_layer) == 1


def test_fact_to_fact_warning():
    findings = check_dependency_direction(
        model_name="fct_executive_summary",
        model_layer="marts",
        depends_on=["model.dcr_analytics.fct_reservations"],
    )
    assert any(f["check"] == "mart_to_mart" for f in findings)


def test_fact_to_integration_valid():
    findings = check_dependency_direction(
        model_name="fct_reservations",
        model_layer="marts",
        depends_on=[
            "model.dcr_analytics.int_contacts",
            "model.dcr_analytics.int_parks",
        ],
    )
    assert len(findings) == 0


def test_skip_layer_warning():
    findings = check_dependency_direction(
        model_name="fct_bad_model",
        model_layer="marts",
        depends_on=["source.dcr_analytics.vistareserve.reservations"],
    )
    assert any(f["check"] == "skip_layer" for f in findings)
