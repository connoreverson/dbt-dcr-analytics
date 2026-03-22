from __future__ import annotations

from scripts.scaffold.source_freshness_scaffold import (
    classify_table_type,
    suggest_loaded_at_field,
    generate_freshness_block,
)


def test_classify_transactional():
    assert classify_table_type("transactions") == "transactional"
    assert classify_table_type("event_logs") == "transactional"
    assert classify_table_type("orders") == "transactional"


def test_classify_reference():
    assert classify_table_type("status_codes") == "reference"
    assert classify_table_type("type_mappings") == "reference"
    assert classify_table_type("categories") == "reference"


def test_classify_default():
    assert classify_table_type("employees") == "standard"
    assert classify_table_type("reservations") == "standard"


def test_suggest_loaded_at_field():
    columns = ["id", "name", "updated_at", "created_at"]
    field = suggest_loaded_at_field(columns)
    assert field == "updated_at"


def test_suggest_loaded_at_field_modified():
    columns = ["id", "modified_date", "status"]
    field = suggest_loaded_at_field(columns)
    assert field == "modified_date"


def test_suggest_loaded_at_field_none():
    columns = ["id", "name", "status"]
    field = suggest_loaded_at_field(columns)
    assert field is None


def test_generate_freshness_block():
    block = generate_freshness_block(
        table_name="employees",
        loaded_at_field="updated_at",
        table_type="standard",
    )
    assert "updated_at" in block
    assert "warn_after" in block
    assert "error_after" in block
