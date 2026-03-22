# tests/scripts/test_model_context.py
from scripts.llm_context.model_context import build_model_context


def test_build_model_context_basic():
    """Build context from a manifest node dict."""
    node = {
        "name": "int_parks",
        "resource_type": "model",
        "schema": "main",
        "description": "Parks integration model",
        "meta": {"cdm_entity": "Asset"},
        "depends_on": {
            "nodes": [
                "model.dcr_analytics.stg_geoparks__parks",
                "model.dcr_analytics.stg_infratrak__assets",
            ]
        },
        "columns": {
            "parks_sk": {"name": "parks_sk", "description": "Surrogate key"},
            "name": {"name": "name", "description": "Park name"},
        },
    }
    context = build_model_context(node)
    assert context["Model"] == "int_parks"
    assert context["Layer"] == "Integration"
    assert context["CDM Entity"] == "Asset"
    assert "stg_geoparks__parks" in context["Parents"]


def test_build_model_context_no_meta():
    """Handles missing meta gracefully."""
    node = {
        "name": "stg_test",
        "resource_type": "model",
        "schema": "main",
        "description": "",
        "meta": {},
        "depends_on": {"nodes": []},
        "columns": {},
    }
    context = build_model_context(node)
    assert context["CDM Entity"] == "Not specified"
