"""Shared pytest fixtures for dbt-profiler tests."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"
PROJECT_ROOT = Path(__file__).parent.parent.parent
DUCKDB_FIXTURE = PROJECT_ROOT / "source_data" / "duckdb" / "dcr_rev_01_vistareserve.duckdb"


@pytest.fixture
def fixture_manifest() -> dict:
    """Minimal manifest dict for selector unit tests."""
    with open(FIXTURES_DIR / "manifest.json") as f:
        return json.load(f)


@pytest.fixture
def fixture_manifest_path(tmp_path, fixture_manifest) -> Path:
    """Write the fixture manifest to a temp file and return its path."""
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(fixture_manifest))
    return p


@pytest.fixture
def fixture_duckdb_path() -> Path:
    """Path to a real DuckDB file for integration tests.

    Skips if the file doesn't exist -- run data generation scripts first.
    """
    if not DUCKDB_FIXTURE.exists():
        pytest.skip(
            f"Source DuckDB file not found: {DUCKDB_FIXTURE}. "
            "Run the data generation scripts before connector integration tests."
        )
    return DUCKDB_FIXTURE


@pytest.fixture
def fixture_df() -> pd.DataFrame:
    """A small DataFrame with known contents including PII-like values."""
    return pd.DataFrame({
        "id": ["R-001", "R-002", "R-003"],
        "email_address": ["alice@example.com", "bob@example.com", "carol@example.com"],
        "amount": ["149.99", "89.50", "210.00"],
        "status": ["confirmed", "confirmed", "pending"],
        "legacy_flag": [None, None, None],
        "constant_col": ["X", "X", "X"],
    })
