"""Shared dbt selector resolution.

All packages delegate --select parsing to this module.
Delegates to dbtRunner for actual resolution.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
from typing import Literal

from scripts._core.config import ensure_manifest, MANIFEST_PATH
from scripts._core.models import SelectionTarget


def resolve_selector(
    selector: str,
    env: Literal["local", "prod"] = "local",
) -> list[SelectionTarget]:
    """Resolve a dbt selector to SelectionTarget objects."""
    ensure_manifest()
    unique_ids = _run_dbt_ls(selector)
    manifest = _load_manifest()
    return [_build_target(uid, manifest, env) for uid in unique_ids]


def load_manifest() -> dict:
    """Load and return the manifest as a dict. Public for direct consumers."""
    return _load_manifest()


def determine_layer(model_name: str) -> str:
    """Determine a model's layer from its naming prefix."""
    if model_name.startswith("stg_"):
        return "staging"
    if model_name.startswith("base_"):
        return "base"
    if model_name.startswith("int_"):
        return "integration"
    if model_name.startswith(("fct_", "dim_", "rpt_")):
        return "marts"
    return "unknown"


def _run_dbt_ls(selector: str) -> list[str]:
    """Invoke dbt ls and return unique node IDs.

    Only models and sources are included; tests, seeds, and analyses are
    excluded.
    """
    from dbt.cli.main import dbtRunner

    runner = dbtRunner()
    with contextlib.redirect_stdout(io.StringIO()):
        result = runner.invoke(["ls", "--select", selector, "--output", "json"])
    if not result.success:
        raise RuntimeError(
            f"dbt ls failed for selector {selector!r}. "
            "Run `dbt ls --select <selector>` manually to see the full error."
        )
    unique_ids = []
    for item in result.result:
        node_data = json.loads(item) if isinstance(item, str) else item
        if node_data.get("resource_type") in ("model", "source"):
            unique_ids.append(node_data["unique_id"])
    if not unique_ids:
        raise ValueError(f"No dbt nodes matched selector: {selector!r}")
    return unique_ids


def _load_manifest() -> dict:
    """Load manifest.json."""
    try:
        with open(MANIFEST_PATH, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"manifest.json not found at {MANIFEST_PATH}. Run `dbt parse` to generate it."
        ) from exc
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"manifest.json is malformed: {exc}. Run `dbt parse` to regenerate."
        ) from exc


def _build_target(
    unique_id: str,
    manifest: dict,
    env: Literal["local", "prod"],
) -> SelectionTarget:
    """Build a SelectionTarget from a manifest node."""
    prefix_part = unique_id.split(".")[0]

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
            f"Node {unique_id!r} not found in manifest. Run `dbt parse` to refresh."
        )

    schema = node.get("schema", "")
    name = node.get("name", "")

    if env == "prod":
        connector_type: Literal["duckdb", "bigquery"] = "bigquery"
        database = node.get("database", "")
        conn_str = f"{database}.{schema}"
    else:
        connector_type = "duckdb"
        conn_str = _resolve_duckdb_path(node)
        database = node.get("database", "") if prefix_part == "source" else ""

    return SelectionTarget(
        prefix=prefix,
        table=name,
        connector_type=connector_type,
        conn_str=conn_str,
        schema=schema,
        resource_type=resource_type,
        database=database,
    )


def _resolve_duckdb_path(node: dict) -> str:
    """Resolve the .duckdb file path for a node.

    Checks PROFILER_DUCKDB_PATH env var first, then falls back to the dbt
    target database where all models are materialized.
    """
    env_path = os.environ.get("PROFILER_DUCKDB_PATH")
    if env_path:
        return env_path
    return str(Path("target") / "dcr_analytics.duckdb")
