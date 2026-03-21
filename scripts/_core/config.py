"""Environment detection, manifest resolution, and project path helpers."""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

MANIFEST_PATH = Path("target/manifest.json")
MODELS_DIR = Path("models")


def is_manifest_stale(
    manifest_path: Path = MANIFEST_PATH,
    models_dir: Path = MODELS_DIR,
) -> bool:
    """Return True if manifest.json is absent or older than any model file."""
    if not manifest_path.exists():
        return True

    manifest_mtime = manifest_path.stat().st_mtime
    for pattern in ("**/*.sql", "**/*.yml", "**/*.yaml"):
        for f in models_dir.glob(pattern):
            if f.stat().st_mtime > manifest_mtime:
                return True
    return False


def ensure_manifest(
    manifest_path: Path = MANIFEST_PATH,
    models_dir: Path = MODELS_DIR,
) -> Path:
    """Ensure manifest exists and is fresh. Runs dbt parse if stale.

    Returns the manifest path.
    Raises RuntimeError if dbt parse fails.
    """
    if not is_manifest_stale(manifest_path, models_dir):
        return manifest_path

    logger.info("Manifest is stale or missing — running dbt parse...")
    from dbt.cli.main import dbtRunner

    runner = dbtRunner()
    result = runner.invoke(["parse"])
    if not result.success:
        error_detail = str(result.exception) if result.exception else "unknown error"
        raise RuntimeError(
            f"Manifest is stale and `dbt parse` failed: {error_detail}. "
            f"Run `dbt parse` manually to diagnose."
        )
    return manifest_path


def detect_environment(
    profiles_paths: list[Path] | None = None,
) -> str:
    """Detect whether the project targets DuckDB (local) or BigQuery (prod).

    Reads profiles.yml to determine the active target adapter.
    Returns 'duckdb' or 'bigquery'.
    """
    import yaml

    if profiles_paths is None:
        profiles_paths = [
            Path("profiles.yml"),
            Path.home() / ".dbt" / "profiles.yml",
        ]
    for p in profiles_paths:
        if p.exists():
            with open(p, encoding="utf-8") as f:
                profiles = yaml.safe_load(f)
            # Walk the profile to find the target adapter
            for _profile_name, profile_data in profiles.items():
                if isinstance(profile_data, dict):
                    target_name = profile_data.get("target", "dev")
                    outputs = profile_data.get("outputs", {})
                    target_config = outputs.get(target_name, {})
                    adapter = target_config.get("type", "duckdb")
                    return adapter if adapter == "bigquery" else "duckdb"
    return "duckdb"  # default
