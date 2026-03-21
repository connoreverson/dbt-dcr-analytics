# tests/scripts/test_core_config.py
import time
from pathlib import Path

from scripts._core.config import is_manifest_stale, detect_environment


def test_manifest_stale_when_missing(tmp_path):
    """Manifest is stale when it doesn't exist."""
    manifest = tmp_path / "target" / "manifest.json"
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    (models_dir / "test.sql").write_text("select 1")
    assert is_manifest_stale(manifest, models_dir) is True


def test_manifest_stale_when_older_than_model(tmp_path):
    """Manifest is stale when a model file is newer."""
    target_dir = tmp_path / "target"
    target_dir.mkdir()
    manifest = target_dir / "manifest.json"
    manifest.write_text("{}")

    time.sleep(0.1)  # ensure different mtime

    models_dir = tmp_path / "models"
    models_dir.mkdir()
    (models_dir / "test.sql").write_text("select 1")

    assert is_manifest_stale(manifest, models_dir) is True


def test_manifest_fresh_when_newer(tmp_path):
    """Manifest is fresh when it's newer than all model files."""
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    (models_dir / "test.sql").write_text("select 1")

    time.sleep(0.1)

    target_dir = tmp_path / "target"
    target_dir.mkdir()
    manifest = target_dir / "manifest.json"
    manifest.write_text("{}")

    assert is_manifest_stale(manifest, models_dir) is False


def test_detect_environment_duckdb(tmp_path):
    """Detects DuckDB when profiles.yml has type: duckdb."""
    profiles = tmp_path / "profiles.yml"
    profiles.write_text(
        "dcr_analytics:\n"
        "  target: dev\n"
        "  outputs:\n"
        "    dev:\n"
        "      type: duckdb\n"
        "      path: target/dcr_analytics.duckdb\n"
    )
    result = detect_environment(profiles_paths=[profiles])
    assert result == "duckdb"


def test_detect_environment_bigquery(tmp_path):
    """Detects BigQuery when profiles.yml has type: bigquery."""
    profiles = tmp_path / "profiles.yml"
    profiles.write_text(
        "dcr_analytics:\n"
        "  target: prod\n"
        "  outputs:\n"
        "    prod:\n"
        "      type: bigquery\n"
        "      project: my-project\n"
    )
    result = detect_environment(profiles_paths=[profiles])
    assert result == "bigquery"


def test_detect_environment_default_when_missing():
    """Returns duckdb when no profiles.yml found."""
    result = detect_environment(profiles_paths=[Path("/nonexistent/profiles.yml")])
    assert result == "duckdb"
