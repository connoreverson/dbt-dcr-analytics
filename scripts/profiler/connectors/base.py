"""Abstract base class for all database connectors."""
from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

from scripts.profiler.models import ColumnDef, SelectionTarget


class BaseConnector(ABC):
    """Connects to a data source and exposes schema + sample data."""

    def __init__(self, target: SelectionTarget) -> None:
        self.target = target

    @abstractmethod
    def get_schema(self) -> list[ColumnDef]:
        """Return full column list for the target table."""
        ...

    @abstractmethod
    def get_sample(self, n_rows: int) -> pd.DataFrame:
        """Return up to *n_rows* rows from the target table."""
        ...
