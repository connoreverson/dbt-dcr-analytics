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
            import duckdb
        except ImportError as e:
            raise ImportError("duckdb is required. Run: pip install duckdb") from e
        self._duckdb = duckdb

    def _fqn(self) -> str:
        """Fully qualified table name: schema.table."""
        return f"{self.target.schema}.{self.target.table}"

    def get_schema(self) -> list[ColumnDef]:
        """Return column definitions via DESCRIBE."""
        con = self._duckdb.connect(self.target.conn_str, read_only=True)
        try:
            rows = con.execute(f"DESCRIBE {self._fqn()}").fetchall()
        finally:
            con.close()
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
        con = self._duckdb.connect(self.target.conn_str, read_only=True)
        try:
            df: pd.DataFrame = con.execute(
                f"SELECT * FROM {self._fqn()} LIMIT {n_rows}"
            ).df()
        finally:
            con.close()
        return df
