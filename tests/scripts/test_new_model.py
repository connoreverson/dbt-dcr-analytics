# tests/scripts/test_new_model.py
from scripts.llm_context.new_model import (
    classify_entity_behavior,
    build_intake_meta,
    get_existing_models_by_prefix,
)


def test_classify_entity_behavior():
    assert classify_entity_behavior("static reference") == "dimension"
    assert classify_entity_behavior("lifecycle with statuses") == "dimension"
    assert classify_entity_behavior("one-time event/transaction") == "fact"
    assert classify_entity_behavior("point-in-time measurement") == "fact"


def test_build_intake_meta():
    meta = build_intake_meta(
        grain="one row per reservation",
        model_type="fact",
        entity="reservation",
    )
    assert meta["intake_completed"] is True
    assert meta["model_type"] == "fact"
    assert meta["grain"] == "one row per reservation"
    assert "intake_date" in meta


def test_get_existing_models_by_prefix():
    manifest_nodes = {
        "model.dcr_analytics.fct_reservations": {"name": "fct_reservations"},
        "model.dcr_analytics.fct_pos_transactions": {"name": "fct_pos_transactions"},
        "model.dcr_analytics.dim_parks": {"name": "dim_parks"},
        "model.dcr_analytics.int_parks": {"name": "int_parks"},
    }
    facts = get_existing_models_by_prefix(manifest_nodes, "fct_")
    assert len(facts) == 2
    dims = get_existing_models_by_prefix(manifest_nodes, "dim_")
    assert len(dims) == 1
