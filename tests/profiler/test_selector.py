"""Unit tests for scripts.profiler.selector.

Tests use the fixture manifest at tests/profiler/fixtures/manifest.json.
dbtRunner is never invoked -- only _build_target and _load_manifest are tested.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.profiler.models import SelectionTarget
from scripts.profiler.selector import _build_target, _load_manifest

FIXTURE_MANIFEST = Path("tests/profiler/fixtures/manifest.json")


@pytest.fixture
def manifest() -> dict:
    with open(FIXTURE_MANIFEST, encoding="utf-8") as f:
        return json.load(f)


def test_build_target_model_local(manifest):
    uid = "model.dcr_analytics.stg_parks__facilities"
    target = _build_target(uid, manifest, env="local")
    assert target.prefix == "model"
    assert target.table == "stg_parks__facilities"
    assert target.schema == "main"
    assert target.connector_type == "duckdb"
    assert target.resource_type == "model"


def test_build_target_source_local(manifest):
    uid = "source.dcr_analytics.reservations.transactions"
    target = _build_target(uid, manifest, env="local")
    assert target.prefix == "source"
    assert target.table == "transactions"
    assert target.schema == "reservations"
    assert target.connector_type == "duckdb"
    assert target.resource_type == "source"


def test_build_target_prod_uses_bigquery(manifest):
    uid = "model.dcr_analytics.stg_parks__facilities"
    target = _build_target(uid, manifest, env="prod")
    assert target.connector_type == "bigquery"
    assert "dev" in target.conn_str  # database.schema format
    assert "main" in target.conn_str


def test_build_target_missing_node_raises(manifest):
    with pytest.raises(ValueError, match="not found in manifest"):
        _build_target("model.dcr_analytics.nonexistent_model", manifest, env="local")


def test_load_manifest_returns_dict(tmp_path):
    fake = {"nodes": {}, "sources": {}}
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(fake), encoding="utf-8")
    # Monkeypatch MANIFEST_PATH for the duration of this test
    import scripts.profiler.selector as sel_mod
    original = sel_mod.MANIFEST_PATH
    sel_mod.MANIFEST_PATH = p
    try:
        result = _load_manifest()
        assert "nodes" in result
    finally:
        sel_mod.MANIFEST_PATH = original


def test_duckdb_path_from_env(manifest, monkeypatch):
    monkeypatch.setenv("PROFILER_DUCKDB_PATH", "/custom/path.duckdb")
    uid = "model.dcr_analytics.stg_parks__facilities"
    target = _build_target(uid, manifest, env="local")
    assert target.conn_str == "/custom/path.duckdb"
