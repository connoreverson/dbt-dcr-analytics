"""Shared dataclasses for all scripts packages."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass
class SelectionTarget:
    """A resolved dbt node and its database connection details."""

    prefix: Literal["source", "model"]
    table: str
    connector_type: Literal["duckdb", "bigquery"]
    conn_str: str
    schema: str
    resource_type: str
    database: str = ""


@dataclass
class ColumnDef:
    """Schema metadata for a single column."""

    name: str
    source_type: str
    nullable: bool

