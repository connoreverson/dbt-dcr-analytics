"""DuckDB connector -- used for local development with source: and model: nodes."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

from scripts._core.connectors.base import BaseConnector
from scripts._core.models import ColumnDef, SelectionTarget

_PROFILES_PATH = Path("profiles.yml")


class DuckDBConnector(BaseConnector):
    """Connects to a .duckdb file and returns schema + sample as pandas DataFrame."""

    def __init__(self, target: SelectionTarget) -> None:
        super().__init__(target)
        try:
            import duckdb as _duckdb
        except ImportError as e:
            raise ImportError("duckdb is required. Run: pip install duckdb") from e
        self._con = _duckdb.connect(str(target.conn_str), read_only=True)
        self._attach_sources()

    def _attach_sources(self) -> None:
        """Re-attach source databases from profiles.yml.

        Staging models are views referencing attached source schemas (e.g.
        geoparks.parks_master). When opened outside dbt, those attachments are
        absent -- this method restores them so view queries can resolve.
        """
        if not _PROFILES_PATH.exists():
            return
        with open(_PROFILES_PATH, encoding="utf-8") as f:
            profiles = yaml.safe_load(f)
        for profile in profiles.values():
            if not isinstance(profile, dict):
                continue
            target_name = profile.get("target", "dev")
            target_config = profile.get("outputs", {}).get(target_name, {})
            for attachment in target_config.get("attach", []):
                path = attachment.get("path", "")
                alias = attachment.get("alias", "")
                if path and alias:
                    try:
                        self._con.execute(
                            f"ATTACH '{path}' AS \"{alias}\" (READ_ONLY)"
                        )
                    except Exception:
                        pass  # already attached or file missing -- skip
            break  # only the first matching profile

    def close(self) -> None:
        """Close the underlying DuckDB connection."""
        self._con.close()

    def _fqn(self) -> str:
        """Fully qualified table name with safe identifier quoting.

        Sources need a three-part FQN (attach_alias.schema.table) because their
        data lives in an attached database. Models use two parts (schema.table)
        since they materialize into the main target database.
        """
        schema = self.target.schema.replace('"', '""')
        table = self.target.table.replace('"', '""')
        if self.target.database:
            db = self.target.database.replace('"', '""')
            return f'"{db}"."{schema}"."{table}"'
        return f'"{schema}"."{table}"'

    def get_schema(self) -> list[ColumnDef]:
        """Return column definitions via DESCRIBE."""
        rows = self._con.execute(f"DESCRIBE {self._fqn()}").fetchall()
        # DuckDB DESCRIBE columns: [column_name, column_type, null, key, default, extra]
        # Index 2 is the 'null' column ("YES" / "NO").
        # Index 3 is 'key' -- do NOT use row[3] for nullable.
        return [
            ColumnDef(
                name=row[0],
                source_type=row[1],
                nullable=(row[2] == "YES"),
            )
            for row in rows
        ]

    def get_sample(self, n_rows: int) -> pd.DataFrame:
        """Return up to *n_rows* rows as a pandas DataFrame."""
        if n_rows < 1:
            raise ValueError(f"n_rows must be a positive integer, got {n_rows}")
        return self._con.execute(
            f"SELECT * FROM {self._fqn()} LIMIT {n_rows}"
        ).df()

    def run_query(self, sql: str) -> pd.DataFrame:
        """Execute SQL against the DuckDB connection and return a DataFrame."""
        return self._con.execute(sql).df()
