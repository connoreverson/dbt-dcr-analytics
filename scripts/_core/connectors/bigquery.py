"""BigQuery connector -- used for production profiling."""
from __future__ import annotations

import pandas as pd

from scripts._core.connectors.base import BaseConnector
from scripts._core.models import ColumnDef, SelectionTarget


class BigQueryConnector(BaseConnector):
    """Connects to a BigQuery dataset and returns schema + sample as pandas DataFrame."""

    def __init__(self, target: SelectionTarget) -> None:
        super().__init__(target)
        try:
            from google.cloud import bigquery as _bq

            self._bq = _bq
        except ImportError as e:
            raise ImportError(
                "google-cloud-bigquery is required for BigQuery profiling. "
                "Run: pip install google-cloud-bigquery"
            ) from e
        # conn_str format: "project.dataset"
        parts = target.conn_str.split(".")
        if len(parts) < 2:
            raise ValueError(
                f"BigQuery conn_str must be 'project.dataset', got: {target.conn_str!r}"
            )
        self._project = parts[0]
        self._dataset = parts[1]
        self._client: object | None = None  # deferred -- authenticate on first use

    def _get_client(self):
        """Authenticate lazily to surface clear errors at query time, not construction."""
        if self._client is None:
            self._client = self._bq.Client()
        return self._client

    def _fqn(self) -> str:
        """Fully qualified table reference with backtick quoting."""
        return f"`{self._project}.{self._dataset}.{self.target.table}`"

    def get_schema(self) -> list[ColumnDef]:
        """Return column definitions via INFORMATION_SCHEMA."""
        bq = self._bq
        query = (
            f"SELECT column_name, data_type, is_nullable "
            f"FROM `{self._project}.{self._dataset}.INFORMATION_SCHEMA.COLUMNS` "
            f"WHERE table_name = @table_name "
            f"ORDER BY ordinal_position"
        )
        job_config = bq.QueryJobConfig(
            query_parameters=[
                bq.ScalarQueryParameter("table_name", "STRING", self.target.table)
            ]
        )
        rows = self._get_client().query(query, job_config=job_config).result()
        return [
            ColumnDef(
                name=row.column_name,
                source_type=row.data_type,
                nullable=(row.is_nullable == "YES"),
            )
            for row in rows
        ]

    def get_sample(self, n_rows: int) -> pd.DataFrame:
        """Return up to *n_rows* rows as a pandas DataFrame."""
        query = f"SELECT * FROM {self._fqn()} LIMIT {n_rows}"
        return self._get_client().query(query).to_dataframe()

    def run_query(self, sql: str) -> pd.DataFrame:
        """Execute SQL against BigQuery and return a DataFrame."""
        return self._get_client().query(sql).to_dataframe()
