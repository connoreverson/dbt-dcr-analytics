"""Resolve a dbt selector string into SelectionTarget objects.

Uses dbtRunner to list matching nodes and reads the manifest to build
typed SelectionTarget instances for downstream profiling.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal

from scripts.profiler.models import SelectionTarget


MANIFEST_PATH = Path("target/manifest.json")


def resolve_selector(
    selector: str,
    env: Literal["local", "prod"] = "local",
) -> list[SelectionTarget]:
    """Resolve a dbt selector to SelectionTarget objects via dbtRunner + manifest."""
    _ensure_manifest()
    unique_ids = _run_dbt_ls(selector)
    manifest = _load_manifest()
    return [_build_target(uid, manifest, env) for uid in unique_ids]


def _ensure_manifest() -> None:
    """Run `dbt parse` if manifest is absent or older than dbt_project.yml."""
    dbt_project = Path("dbt_project.yml")
    if (
        not MANIFEST_PATH.exists()
        or (
            dbt_project.exists()
            and MANIFEST_PATH.stat().st_mtime < dbt_project.stat().st_mtime
        )
    ):
        from dbt.cli.main import dbtRunner
        runner = dbtRunner()
        result = runner.invoke(["parse"])
        if not result.success:
            raise RuntimeError("dbt parse failed; cannot resolve selector")


def _run_dbt_ls(selector: str) -> list[str]:
    """Invoke `dbt ls --select <selector> --output selector` via dbtRunner.

    Returns a list of unique node IDs (e.g. 'model.dcr_analytics.stg_parks__facilities').
    """
    from dbt.cli.main import dbtRunner
    runner = dbtRunner()
    result = runner.invoke(["ls", "--select", selector, "--output", "selector"])
    if not result.success:
        raise RuntimeError(
            f"dbt ls failed for selector {selector!r}. "
            "This may indicate a syntax error in the selector or a dbt configuration problem. "
            "Run `dbt ls --select <selector>` manually to see the full error."
        )
    # result.result is an iterable of unique_id strings
    unique_ids = list(result.result)
    if not unique_ids:
        raise ValueError(f"No dbt nodes matched selector: {selector!r}")
    return unique_ids


def _load_manifest() -> dict:
    try:
        with open(MANIFEST_PATH, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"manifest.json is malformed at {MANIFEST_PATH}: {exc}. "
            "Run `dbt parse` to regenerate it."
        ) from exc


def _build_target(
    unique_id: str,
    manifest: dict,
    env: Literal["local", "prod"],
) -> SelectionTarget:
    """Look up a node in the manifest and build a SelectionTarget."""
    # Determine resource type from unique_id prefix
    prefix_part = unique_id.split(".")[0]  # "model", "source", "seed", etc.

    if prefix_part == "source":
        node = manifest.get("sources", {}).get(unique_id)
        resource_type = "source"
        prefix: Literal["source", "model"] = "source"
    else:
        node = manifest.get("nodes", {}).get(unique_id)
        resource_type = node.get("resource_type", "model") if node else "model"
        prefix = "model"

    if node is None:
        raise ValueError(
            f"Node {unique_id!r} not found in manifest. "
            "Try running `dbt parse` to refresh the manifest."
        )

    schema = node.get("schema", "")
    name = node.get("name", "")

    # Resolve connector type and conn_str from env
    if env == "prod":
        connector_type: Literal["duckdb", "bigquery"] = "bigquery"
        database = node.get("database", "")
        conn_str = f"{database}.{schema}"
    else:
        connector_type = "duckdb"
        # Resolve DuckDB path from environment or fall back to project convention
        conn_str = _resolve_duckdb_path(node)

    return SelectionTarget(
        prefix=prefix,
        table=name,
        connector_type=connector_type,
        conn_str=conn_str,
        schema=schema,
        resource_type=resource_type,
    )


def _resolve_duckdb_path(node: dict) -> str:
    """Resolve the .duckdb file path for a node.

    Checks PROFILER_DUCKDB_PATH env var first, then falls back to a
    convention-based path: source_data/duckdb/<database>.duckdb
    """
    env_path = os.environ.get("PROFILER_DUCKDB_PATH")
    if env_path:
        return env_path
    database = node.get("database", "dev")
    return str(Path("source_data") / "duckdb" / f"{database}.duckdb")
