# tests/scripts/test_source_context.py
from scripts.llm_context.source_context import build_source_context


def test_build_source_context_basic():
    """Build context from a manifest source node."""
    node = {
        "name": "reservations",
        "source_name": "vistareserve",
        "schema": "main",
        "description": "Raw reservation data from VistaReserve",
        "columns": {
            "id": {"name": "id", "data_type": "INTEGER"},
            "guest_name": {"name": "guest_name", "data_type": "VARCHAR"},
            "amount": {"name": "amount", "data_type": "DECIMAL"},
        },
    }
    context = build_source_context(node)
    assert context["Source System"] == "vistareserve"
    assert context["Table"] == "reservations"
    assert "id" in str(context["Columns"])


def test_build_source_context_no_columns():
    """Handles missing columns gracefully."""
    node = {
        "name": "unknown_table",
        "source_name": "legacy",
        "schema": "raw",
        "description": "",
        "columns": {},
    }
    context = build_source_context(node)
    assert context["Source System"] == "legacy"
    assert context["Description"] == "No description"
    assert context["Columns"] == ["No column metadata in manifest"]


def test_build_source_context_missing_fields():
    """Handles a minimal node with missing optional fields."""
    node = {"name": "bare_table"}
    context = build_source_context(node)
    assert context["Source System"] == "unknown"
    assert context["Table"] == "bare_table"
    assert context["Schema"] == ""
