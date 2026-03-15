"""DuckDB connector -- used for local development with source: and model: nodes."""
from __future__ import annotations

import pandas as pd

from scripts.profiler.connectors.base import BaseConnector
from scripts.profiler.models import ColumnDef, SelectionTarget


class DuckDBConnector(BaseConnector):
    """Connects to a .duckdb file and returns schema + sample as pandas DataFrame."""

    def __init__(self, target: SelectionTarget) -> None:
        super().__init__(target)
        try:
            import duckdb as _duckdb
        except ImportError as e:
            raise ImportError("duckdb is required. Run: pip install duckdb") from e
        self._con = _duckdb.connect(str(target.conn_str), read_only=True)

    def close(self) -> None:
        """Close the underlying DuckDB connection."""
        self._con.close()

    def _fqn(self) -> str:
        """Fully qualified table name with safe identifier quoting."""
        schema = self.target.schema.replace('"', '""')
        table = self.target.table.replace('"', '""')
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
