# dbt-profiler Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a modular Python profiling utility at `scripts/profiler/` that replaces `scripts/inspect_source.py`, accepts dbt node selectors, and produces terminal (skimpy + rich), markdown (LLM-optimized), and HTML (ydata-profiling) output with Presidio PII sanitization.

**Architecture:** Three layers — (1) selection resolves dbt selectors to database connections via dbtRunner + manifest, (2) analysis uses ydata-profiling as the statistical engine with Presidio for PII detection and a custom dbt-signals layer, (3) rendering produces three output formats where sanitizer.py is called lazily only by renderers that need redaction.

**Tech Stack:** Python 3.10+, dbt-core 1.9 (dbtRunner), ydata-profiling ≥4.6, skimpy ≥0.0.12, presidio-analyzer ≥2.2, presidio-anonymizer ≥2.2, pandas ~2.2, rich ~13, pytest

**Spec:** `docs/superpowers/specs/2026-03-15-dbt-profiler-design.md`

**Activate venv before all commands:** `source .venv/Scripts/activate` (Git Bash)

---

## Chunk 1: Foundation Layer

### Task 1: Bootstrap package structure and dependencies

**Files:**
- Create: `scripts/profiler/__init__.py`
- Create: `scripts/profiler/connectors/__init__.py`
- Create: `scripts/profiler/analyzers/__init__.py`
- Create: `scripts/profiler/renderers/__init__.py`
- Create: `tests/profiler/__init__.py`
- Create: `tests/profiler/connectors/__init__.py`
- Create: `tests/profiler/analyzers/__init__.py`
- Create: `tests/profiler/renderers/__init__.py`
- Create: `tests/profiler/fixtures/manifest.json`
- Create: `tests/profiler/conftest.py`
- Modify: `requirements.txt`

> **Note:** Task 1 is infrastructure-only — no TDD cycle. There is no business logic to test here. The first failing test is in Task 2 Step 1.

- [ ] **Step 1: Create package `__init__.py` files**

`touch` does not create parent directories. Create directories first, then touch files:

```bash
mkdir -p scripts/profiler/connectors \
         scripts/profiler/analyzers \
         scripts/profiler/renderers \
         tests/profiler/connectors \
         tests/profiler/analyzers \
         tests/profiler/renderers \
         tests/profiler/fixtures

touch scripts/profiler/__init__.py \
      scripts/profiler/connectors/__init__.py \
      scripts/profiler/analyzers/__init__.py \
      scripts/profiler/renderers/__init__.py \
      tests/profiler/__init__.py \
      tests/profiler/connectors/__init__.py \
      tests/profiler/analyzers/__init__.py \
      tests/profiler/renderers/__init__.py
```

> **Note:** `tests/profiler/fixtures/` is not a Python package — no `__init__.py` needed there. It holds JSON fixture files only.

- [ ] **Step 2: Create the fixture manifest**

Create `tests/profiler/fixtures/manifest.json` — a minimal manifest that exercises both source and model resolution. This avoids running `dbt parse` during tests.

```json
{
  "metadata": {
    "dbt_schema_version": "https://schemas.getdbt.com/dbt/manifest/v12/manifest.json",
    "dbt_version": "1.9.0",
    "generated_at": "2026-03-15T00:00:00.000000Z",
    "invocation_id": "test-fixture",
    "env": {}
  },
  "nodes": {
    "model.dcr_analytics.stg_parks__facilities": {
      "unique_id": "model.dcr_analytics.stg_parks__facilities",
      "name": "stg_parks__facilities",
      "resource_type": "model",
      "database": "dev",
      "schema": "main",
      "alias": "stg_parks__facilities",
      "config": {"materialized": "view"}
    },
    "model.dcr_analytics.int_parks": {
      "unique_id": "model.dcr_analytics.int_parks",
      "name": "int_parks",
      "resource_type": "model",
      "database": "dev",
      "schema": "main",
      "alias": "int_parks",
      "config": {"materialized": "table"}
    }
  },
  "sources": {
    "source.dcr_analytics.vistareserve.reservations": {
      "unique_id": "source.dcr_analytics.vistareserve.reservations",
      "name": "reservations",
      "source_name": "vistareserve",
      "resource_type": "source",
      "database": "source_data/duckdb/dcr_rev_01_vistareserve.duckdb",
      "schema": "main",
      "identifier": "reservations"
    }
  }
}
```

- [ ] **Step 3: Create `tests/profiler/conftest.py`**

```python
"""Shared pytest fixtures for dbt-profiler tests."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"
PROJECT_ROOT = Path(__file__).parent.parent.parent
DUCKDB_FIXTURE = PROJECT_ROOT / "source_data" / "duckdb" / "dcr_rev_01_vistareserve.duckdb"


@pytest.fixture
def fixture_manifest() -> dict:
    """Minimal manifest dict for selector unit tests."""
    with open(FIXTURES_DIR / "manifest.json") as f:
        return json.load(f)


@pytest.fixture
def fixture_manifest_path(tmp_path, fixture_manifest) -> Path:
    """Write the fixture manifest to a temp file and return its path."""
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(fixture_manifest))
    return p


@pytest.fixture
def fixture_duckdb_path() -> Path:
    """Path to a real DuckDB file for integration tests.

    Skips if the file doesn't exist — run data generation scripts first.
    """
    if not DUCKDB_FIXTURE.exists():
        pytest.skip(
            f"Source DuckDB file not found: {DUCKDB_FIXTURE}. "
            "Run the data generation scripts before connector integration tests."
        )
    return DUCKDB_FIXTURE


@pytest.fixture
def fixture_df() -> pd.DataFrame:
    """A small DataFrame with known contents including PII-like values."""
    return pd.DataFrame({
        "id": ["R-001", "R-002", "R-003"],
        "email_address": ["alice@example.com", "bob@example.com", "carol@example.com"],
        "amount": ["149.99", "89.50", "210.00"],
        "status": ["confirmed", "confirmed", "pending"],
        "legacy_flag": [None, None, None],
        "constant_col": ["X", "X", "X"],
    })
```

- [ ] **Step 4: Add new dependencies to `requirements.txt`**

Append after the existing entries:

```
ydata-profiling>=4.6
skimpy>=0.0.12
presidio-analyzer>=2.2
presidio-anonymizer>=2.2
```

- [ ] **Step 5: Install new dependencies**

```bash
source .venv/Scripts/activate
pip install "ydata-profiling>=4.6" "skimpy>=0.0.12" "presidio-analyzer>=2.2" "presidio-anonymizer>=2.2"
python -m spacy download en_core_web_lg
```

- [ ] **Step 6: Verify imports succeed**

```bash
python -c "from ydata_profiling import ProfileReport; from skimpy import skim; from presidio_analyzer import AnalyzerEngine; print('OK')"
```

Expected: `OK`

- [ ] **Step 7: Commit**

Stage only the bootstrap files — not test files created in later tasks:

```bash
git add scripts/profiler/__init__.py \
        scripts/profiler/connectors/__init__.py \
        scripts/profiler/analyzers/__init__.py \
        scripts/profiler/renderers/__init__.py \
        tests/profiler/__init__.py \
        tests/profiler/connectors/__init__.py \
        tests/profiler/analyzers/__init__.py \
        tests/profiler/renderers/__init__.py \
        tests/profiler/fixtures/manifest.json \
        tests/profiler/conftest.py \
        requirements.txt
git commit -m "chore: bootstrap dbt-profiler package structure and dependencies"
```

---

### Task 2: Shared dataclasses (`models.py`)

**Files:**
- Create: `scripts/profiler/models.py`
- Create: `tests/profiler/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/profiler/test_models.py
from __future__ import annotations
from scripts.profiler.models import SelectionTarget, ColumnDef, DbtSignal, AnalysisResult
import pandas as pd
from datetime import datetime


def test_selection_target_fields():
    t = SelectionTarget(
        prefix="source",
        table="reservations",
        connector_type="duckdb",
        conn_str="source_data/duckdb/dcr_rev_01_vistareserve.duckdb",
        schema="main",
        resource_type="source",
    )
    assert t.table == "reservations"
    assert t.connector_type == "duckdb"


def test_column_def_fields():
    c = ColumnDef(name="email_address", source_type="VARCHAR", nullable=True)
    assert c.nullable is True


def test_dbt_signal_fields():
    s = DbtSignal(
        signal_type="CAST_HINT",
        column_name="amount",
        message="cast(amount as decimal(10,2))",
    )
    assert s.signal_type == "CAST_HINT"


def test_analysis_result_no_sanitized_sample():
    """AnalysisResult must not carry a sanitized_sample field."""
    import dataclasses
    field_names = {f.name for f in dataclasses.fields(AnalysisResult)}
    assert "sanitized_sample" not in field_names

# Note: AnalysisResult cannot be fully instantiated here because it requires
# a live ProfileReport and BaseDescription from ydata-profiling.
# Full construction is validated end-to-end in Task 5 (test_stats.py).
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/profiler/test_models.py -v
```

Expected: `ImportError` — `models` module does not exist yet.

- [ ] **Step 3: Write `scripts/profiler/models.py`**

```python
"""Shared dataclasses for dbt-profiler.

AnalysisResult references ydata-profiling types under TYPE_CHECKING only
so that models.py has no hard import of ydata-profiling at module load time.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    import pandas as pd
    from ydata_profiling import ProfileReport
    from ydata_profiling.model.description import BaseDescription


@dataclass
class SelectionTarget:
    """A resolved dbt node ready for profiling."""

    prefix: Literal["source", "model"]
    table: str
    """Unqualified relation name from the manifest 'name' field.
    Used as display title and output filename component."""
    connector_type: Literal["duckdb", "bigquery"]
    conn_str: str
    """Resolved .duckdb path or BigQuery project.dataset string.
    Populated by selector.py from the manifest 'database' field.
    For DuckDB sources, the manifest stores the .duckdb file path in 'database'.
    For BigQuery model nodes, this is 'project.dataset'."""
    schema: str
    resource_type: str
    """'source' or 'model'."""


@dataclass
class ColumnDef:
    """Schema metadata for a single column."""

    name: str
    source_type: str
    nullable: bool


@dataclass
class DbtSignal:
    """A single dbt-specific observation about a column or table."""

    signal_type: Literal["CAST_HINT", "RENAME_HINT", "UNUSED_COLUMN", "NULL_PATTERN"]
    column_name: str
    message: str
    """Human-readable description, e.g. 'cast(amount as decimal(10,2))'."""


@dataclass
class AnalysisResult:
    """The complete output of the analysis pipeline for one SelectionTarget.

    sanitized_sample is intentionally absent. Renderers that need redacted
    data call sanitizer.sanitize(result.sample, result.pii_columns) inline.
    """

    target: SelectionTarget
    profile: ProfileReport
    """Full ydata-profiling ProfileReport object. Used by html renderer."""
    description: BaseDescription
    """profile.get_description(). Used by markdown renderer and dbt_signals."""
    sample: pd.DataFrame
    """Raw sample — never mutated."""
    pii_columns: set[str]
    dbt_signals: list[DbtSignal]
    profiled_at: datetime = field(default_factory=datetime.utcnow)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/profiler/test_models.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/profiler/models.py tests/profiler/test_models.py
git commit -m "feat(profiler): add shared dataclasses (SelectionTarget, ColumnDef, DbtSignal, AnalysisResult)"
```

---

### Task 3: Connectors — BaseConnector and DuckDB

**Files:**
- Create: `scripts/profiler/connectors/base.py`
- Create: `scripts/profiler/connectors/duckdb.py`
- Create: `scripts/profiler/connectors/bigquery.py`
- Create: `tests/profiler/connectors/test_duckdb.py`

- [ ] **Step 1: Write failing tests for the DuckDB connector**

```python
# tests/profiler/connectors/test_duckdb.py
"""Integration tests — require a real DuckDB file from source_data/duckdb/."""
from __future__ import annotations

import pandas as pd
import pytest

from scripts.profiler.connectors.duckdb import DuckDBConnector
from scripts.profiler.models import ColumnDef, SelectionTarget


@pytest.fixture
def vistareserve_target(fixture_duckdb_path) -> SelectionTarget:
    # Inspect the file to find a real table name
    import duckdb
    con = duckdb.connect(str(fixture_duckdb_path), read_only=True)
    table = con.execute(
        "SELECT table_name FROM information_schema.tables LIMIT 1"
    ).fetchone()[0]
    con.close()
    return SelectionTarget(
        prefix="source",
        table=table,
        connector_type="duckdb",
        conn_str=str(fixture_duckdb_path),
        schema="main",
        resource_type="source",
    )


def test_get_schema_returns_column_defs(vistareserve_target):
    conn = DuckDBConnector(vistareserve_target)
    schema = conn.get_schema()
    assert len(schema) > 0
    assert all(isinstance(c, ColumnDef) for c in schema)
    assert all(isinstance(c.name, str) for c in schema)
    assert all(isinstance(c.source_type, str) for c in schema)


def test_get_sample_returns_dataframe(vistareserve_target):
    conn = DuckDBConnector(vistareserve_target)
    df = conn.get_sample(n_rows=10)
    assert isinstance(df, pd.DataFrame)
    assert len(df) <= 10
    assert len(df.columns) > 0


def test_get_sample_respects_row_limit(vistareserve_target):
    conn = DuckDBConnector(vistareserve_target)
    df = conn.get_sample(n_rows=5)
    assert len(df) <= 5


def test_connector_raises_on_bad_table(fixture_duckdb_path):
    target = SelectionTarget(
        prefix="source",
        table="nonexistent_table_xyz",
        connector_type="duckdb",
        conn_str=str(fixture_duckdb_path),
        schema="main",
        resource_type="source",
    )
    conn = DuckDBConnector(target)
    # DuckDB raises duckdb.CatalogException; catching base Exception is intentional
    # to avoid importing duckdb internals in the test file.
    with pytest.raises(Exception, match="nonexistent_table_xyz"):
        conn.get_sample(n_rows=10)
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/profiler/connectors/test_duckdb.py -v
```

Expected: `ImportError` — connectors module does not exist.

- [ ] **Step 3: Write `scripts/profiler/connectors/base.py`**

```python
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
        """Return up to n_rows rows from the target table as a pandas DataFrame."""
        ...
```

- [ ] **Step 4: Write `scripts/profiler/connectors/duckdb.py`**

```python
"""DuckDB connector — used for local development with source: and model: nodes."""
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
        return f"{self.target.schema}.{self.target.table}"

    def get_schema(self) -> list[ColumnDef]:
        con = self._duckdb.connect(self.target.conn_str, read_only=True)
        try:
            rows = con.execute(f"DESCRIBE {self._fqn()}").fetchall()
        finally:
            con.close()
        # DuckDB DESCRIBE columns: [column_name, column_type, null, key, default, extra]
        # Index 2 is the 'null' column ("YES" / "NO"). Index 3 is 'key' — do NOT use row[3].
        return [
            ColumnDef(
                name=row[0],
                source_type=row[1],
                nullable=(row[2] == "YES"),
            )
            for row in rows
        ]

    def get_sample(self, n_rows: int) -> pd.DataFrame:
        con = self._duckdb.connect(self.target.conn_str, read_only=True)
        try:
            df: pd.DataFrame = con.execute(
                f"SELECT * FROM {self._fqn()} LIMIT {n_rows}"
            ).df()
        finally:
            con.close()
        return df
```

- [ ] **Step 5: Write `scripts/profiler/connectors/bigquery.py`**

BigQuery requires credentials unavailable locally — stub with clear lazy import error.

```python
"""BigQuery connector — used for production profiling."""
from __future__ import annotations

import pandas as pd

from scripts.profiler.connectors.base import BaseConnector
from scripts.profiler.models import ColumnDef, SelectionTarget


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
        self._project = parts[0]
        self._dataset = parts[1] if len(parts) > 1 else target.schema
        self._client: object | None = None  # deferred — authenticate on first use

    def _get_client(self):
        """Authenticate lazily to surface clear errors at query time, not construction."""
        if self._client is None:
            self._client = self._bq.Client()
        return self._client

    def _fqn(self) -> str:
        return f"`{self._project}.{self._dataset}.{self.target.table}`"

    def get_schema(self) -> list[ColumnDef]:
        query = f"""
            SELECT column_name, data_type, is_nullable
            FROM `{self._project}.{self._dataset}.INFORMATION_SCHEMA.COLUMNS`
            WHERE table_name = '{self.target.table}'
            ORDER BY ordinal_position
        """
        rows = self._get_client().query(query).result()
        return [
            ColumnDef(
                name=row.column_name,
                source_type=row.data_type,
                nullable=(row.is_nullable == "YES"),
            )
            for row in rows
        ]

    def get_sample(self, n_rows: int) -> pd.DataFrame:
        query = f"SELECT * FROM {self._fqn()} LIMIT {n_rows}"
        return self._get_client().query(query).to_dataframe()
```

- [ ] **Step 6: Run tests**

```bash
pytest tests/profiler/connectors/test_duckdb.py -v
```

Expected: 4 tests PASS (integration tests against `dcr_rev_01_vistareserve.duckdb`).

- [ ] **Step 7: Commit**

```bash
git add scripts/profiler/connectors/ tests/profiler/connectors/
git commit -m "feat(profiler): add BaseConnector, DuckDBConnector, BigQueryConnector stub"
```

---

## Chunk 2: Analysis Layer

### Task 4: Selector

**Files:**
- Create: `scripts/profiler/selector.py`
- Create: `tests/profiler/test_selector.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/profiler/test_selector.py
"""Unit tests for selector.py — uses fixture manifest, no real dbt invocation."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts.profiler.models import SelectionTarget
from scripts.profiler.selector import resolve_selector, _load_manifest, _parse_node


@pytest.fixture
def manifest_path(fixture_manifest_path) -> Path:
    return fixture_manifest_path


def test_parse_model_node(fixture_manifest):
    node = fixture_manifest["nodes"]["model.dcr_analytics.stg_parks__facilities"]
    target = _parse_node(node, connector_type="duckdb", conn_str="/dev/dbt.duckdb")
    assert target.table == "stg_parks__facilities"
    assert target.prefix == "model"
    assert target.resource_type == "model"
    assert target.schema == "main"


def test_parse_source_node(fixture_manifest):
    node = fixture_manifest["sources"][
        "source.dcr_analytics.vistareserve.reservations"
    ]
    target = _parse_node(node, connector_type="duckdb", conn_str=node["database"])
    assert target.table == "reservations"
    assert target.prefix == "source"
    assert target.resource_type == "source"


def test_load_manifest(manifest_path, fixture_manifest):
    loaded = _load_manifest(manifest_path)
    assert "nodes" in loaded
    assert "sources" in loaded


def test_resolve_selector_model(fixture_manifest, manifest_path):
    """resolve_selector with a mocked dbtRunner that returns one unique_id."""
    mock_result = MagicMock()
    mock_result.success = True
    mock_result.result = ["model.dcr_analytics.stg_parks__facilities"]

    with patch("scripts.profiler.selector.dbtRunner") as MockRunner:
        instance = MockRunner.return_value
        instance.invoke.return_value = mock_result

        targets = resolve_selector(
            selector="stg_parks__facilities",
            manifest_path=manifest_path,
            connector_type="duckdb",
            conn_str="/dev/dbt.duckdb",
            manifest=fixture_manifest,
        )

    assert len(targets) == 1
    assert targets[0].table == "stg_parks__facilities"


def test_resolve_selector_source(fixture_manifest, manifest_path):
    mock_result = MagicMock()
    mock_result.success = True
    mock_result.result = ["source.dcr_analytics.vistareserve.reservations"]

    with patch("scripts.profiler.selector.dbtRunner") as MockRunner:
        instance = MockRunner.return_value
        instance.invoke.return_value = mock_result

        targets = resolve_selector(
            selector="source:vistareserve.reservations",
            manifest_path=manifest_path,
            connector_type="duckdb",
            conn_str="",
            manifest=fixture_manifest,
        )

    assert len(targets) == 1
    assert targets[0].table == "reservations"
    assert targets[0].prefix == "source"


def test_resolve_selector_raises_on_dbt_failure(fixture_manifest, manifest_path):
    # manifest is pre-loaded, so _ensure_manifest is bypassed — only the dbt ls invocation is mocked
    mock_result = MagicMock()
    mock_result.success = False
    mock_result.result = []

    with patch("scripts.profiler.selector.dbtRunner") as MockRunner:
        instance = MockRunner.return_value
        instance.invoke.return_value = mock_result

        with pytest.raises(RuntimeError, match="dbt ls"):
            resolve_selector(
                selector="nonexistent_model",
                manifest_path=manifest_path,
                connector_type="duckdb",
                conn_str="/dev/dbt.duckdb",
                manifest=fixture_manifest,
            )


def test_resolve_selector_raises_when_no_nodes_returned(fixture_manifest, manifest_path):
    """Covers the success=True but empty result.result path."""
    mock_result = MagicMock()
    mock_result.success = True
    mock_result.result = []

    with patch("scripts.profiler.selector.dbtRunner") as MockRunner:
        instance = MockRunner.return_value
        instance.invoke.return_value = mock_result

        with pytest.raises(RuntimeError, match="no nodes"):
            resolve_selector(
                selector="stg_*",
                manifest_path=manifest_path,
                connector_type="duckdb",
                conn_str="/dev/dbt.duckdb",
                manifest=fixture_manifest,
            )
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/profiler/test_selector.py -v
```

Expected: `ImportError` — selector module does not exist.

- [ ] **Step 3: Write `scripts/profiler/selector.py`**

```python
"""Resolves dbt node selectors to SelectionTarget objects.

Uses dbtRunner to delegate selection grammar to dbt, then looks up
connection metadata in target/manifest.json.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal

from dbt.cli.main import dbtRunner

from scripts.profiler.models import SelectionTarget

_DEFAULT_MANIFEST = Path("target") / "manifest.json"


def _load_manifest(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def _ensure_manifest(manifest_path: Path) -> None:
    """Run dbt parse if manifest is absent or older than dbt_project.yml."""
    project_yml = Path("dbt_project.yml")
    needs_parse = not manifest_path.exists() or (
        project_yml.exists()
        and manifest_path.stat().st_mtime < project_yml.stat().st_mtime
    )
    if needs_parse:
        dbt = dbtRunner()
        result = dbt.invoke(["parse"])
        if not result.success:
            raise RuntimeError(
                "dbt parse failed. Check your dbt_project.yml and profiles."
            )


def _parse_node(
    node: dict,
    connector_type: Literal["duckdb", "bigquery"],
    conn_str: str,
) -> SelectionTarget:
    resource_type = node.get("resource_type", "model")
    prefix: Literal["source", "model"] = (
        "source" if resource_type == "source" else "model"
    )
    # For source nodes, conn_str comes from the node's database field
    resolved_conn = node["database"] if resource_type == "source" else conn_str
    return SelectionTarget(
        prefix=prefix,
        table=node["name"],
        connector_type=connector_type,
        conn_str=resolved_conn,
        schema=node["schema"],
        resource_type=resource_type,
    )


def resolve_selector(
    selector: str,
    connector_type: Literal["duckdb", "bigquery"] = "duckdb",
    conn_str: str = "",
    manifest_path: Path | None = None,
    manifest: dict | None = None,
) -> list[SelectionTarget]:
    """Resolve a dbt selector string to a list of SelectionTarget objects.

    Args:
        selector: A dbt node selector, e.g. 'stg_parks__facilities' or
                  'source:vistareserve.reservations'.
        connector_type: Which connector backend to use.
        conn_str: Connection string for model nodes (dbt target .duckdb path or
                  BQ project.dataset). Ignored for source nodes — their conn_str
                  comes from the manifest's database field.
        manifest_path: Path to manifest.json. Defaults to target/manifest.json.
        manifest: Pre-loaded manifest dict (used in tests to skip file I/O).
    """
    resolved_path = manifest_path or _DEFAULT_MANIFEST

    if manifest is None:
        _ensure_manifest(resolved_path)
        manifest = _load_manifest(resolved_path)

    dbt = dbtRunner()
    result = dbt.invoke(
        ["ls", "--select", selector, "--output", "selector", "--quiet"]
    )

    if not result.success:
        raise RuntimeError(
            f"dbt ls failed for selector '{selector}'. "
            "Ensure the selector matches at least one node and dbt parse has run."
        )

    unique_ids: list[str] = list(result.result or [])
    if not unique_ids:
        raise RuntimeError(
            f"dbt ls returned no nodes for selector '{selector}'. "
            "Check that the model or source exists in your project."
        )

    all_nodes = {**manifest.get("nodes", {}), **manifest.get("sources", {})}
    targets = []
    for uid in unique_ids:
        uid = uid.strip()
        if not uid:
            continue
        node = all_nodes.get(uid)
        if node is None:
            raise RuntimeError(
                f"Node '{uid}' returned by dbt ls was not found in manifest.json. "
                "Try running 'dbt parse' to refresh the manifest."
            )
        targets.append(_parse_node(node, connector_type, conn_str))

    return targets
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/profiler/test_selector.py -v
```

Expected: 6 tests PASS (dbtRunner is mocked — no live dbt invocation).

- [ ] **Step 5: Commit**

```bash
git add scripts/profiler/selector.py tests/profiler/test_selector.py
git commit -m "feat(profiler): add selector — resolves dbt node selectors via dbtRunner + manifest"
```

---

### Task 5: Statistical analyzer (`stats.py`)

**Files:**
- Create: `scripts/profiler/analyzers/stats.py`
- Create: `tests/profiler/analyzers/test_stats.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/profiler/analyzers/test_stats.py
from __future__ import annotations

import pandas as pd
import pytest

from scripts.profiler.analyzers.stats import build_analysis_result
from scripts.profiler.models import AnalysisResult, SelectionTarget


@pytest.fixture
def dummy_target() -> SelectionTarget:
    return SelectionTarget(
        prefix="source",
        table="test_table",
        connector_type="duckdb",
        conn_str=":memory:",
        schema="main",
        resource_type="source",
    )


def test_build_analysis_result_returns_correct_type(fixture_df, dummy_target):
    result = build_analysis_result(fixture_df, dummy_target, minimal=True)
    assert isinstance(result, AnalysisResult)


def test_analysis_result_has_profile(fixture_df, dummy_target):
    from ydata_profiling import ProfileReport
    result = build_analysis_result(fixture_df, dummy_target, minimal=True)
    assert isinstance(result.profile, ProfileReport)


def test_analysis_result_has_description(fixture_df, dummy_target):
    result = build_analysis_result(fixture_df, dummy_target, minimal=True)
    assert result.description is not None
    # description should expose variable stats
    assert hasattr(result.description, "variables")


def test_analysis_result_preserves_sample(fixture_df, dummy_target):
    # ydata-profiling may mutate the input DataFrame in-place (dtype coercion).
    # Pass df.copy() to ProfileReport and store the original as sample (see stats.py).
    # Assert value equality, not identity.
    result = build_analysis_result(fixture_df, dummy_target, minimal=True)
    assert result.sample.equals(fixture_df)


def test_analysis_result_no_sanitized_sample_field(fixture_df, dummy_target):
    import dataclasses
    result = build_analysis_result(fixture_df, dummy_target, minimal=True)
    field_names = {f.name for f in dataclasses.fields(result)}
    assert "sanitized_sample" not in field_names
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/profiler/analyzers/test_stats.py -v
```

Expected: `ImportError` — stats module does not exist.

- [ ] **Step 3: Write `scripts/profiler/analyzers/stats.py`**

```python
"""Statistical analyzer — delegates to ydata-profiling as the computation engine."""
from __future__ import annotations

import pandas as pd

from scripts.profiler.models import AnalysisResult, SelectionTarget


def build_analysis_result(
    df: pd.DataFrame,
    target: SelectionTarget,
    minimal: bool = True,
) -> AnalysisResult:
    """Build an AnalysisResult from a pandas DataFrame using ydata-profiling.

    Args:
        df: Raw sample DataFrame from the connector.
        target: The resolved SelectionTarget for this profile run.
        minimal: If True (default), skips correlations and interactions.
                 Pass False only for --full-profile HTML runs.
    """
    try:
        from ydata_profiling import ProfileReport
    except ImportError as e:
        raise ImportError(
            "ydata-profiling is required. Run: pip install 'ydata-profiling>=4.6'"
        ) from e

    # Pass df.copy() to ProfileReport — ydata-profiling may mutate the input DataFrame
    # in-place (dtype coercion, index resets). Store the original df as sample.
    profile = ProfileReport(df.copy(), minimal=minimal, title=target.table, progress_bar=False)
    description = profile.get_description()

    return AnalysisResult(
        target=target,
        profile=profile,
        description=description,
        sample=df,
        pii_columns=set(),       # populated downstream by pii.py
        dbt_signals=[],           # populated downstream by dbt_signals.py
    )
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/profiler/analyzers/test_stats.py -v
```

Expected: 5 tests PASS. Note: `build_analysis_result` can be slow on large DataFrames; the `fixture_df` has 3 rows so it's fast.

- [ ] **Step 5: Commit**

```bash
git add scripts/profiler/analyzers/stats.py tests/profiler/analyzers/test_stats.py
git commit -m "feat(profiler): add stats analyzer — ydata-profiling orchestrator"
```

---

### Task 6: PII analyzer (`pii.py`)

**Files:**
- Create: `scripts/profiler/analyzers/pii.py`
- Create: `tests/profiler/analyzers/test_pii.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/profiler/analyzers/test_pii.py
from __future__ import annotations

import pandas as pd
import pytest

from scripts.profiler.analyzers.pii import detect_pii_columns


def _spacy_available() -> bool:
    try:
        import spacy
        spacy.load("en_core_web_lg")
        return True
    except Exception:
        return False

# Synthetic DataFrame with obvious PII
PII_DF = pd.DataFrame({
    "id": ["001", "002", "003"],
    "email_address": ["alice@example.com", "bob@example.com", "carol@example.com"],
    "customer_phone": ["555-123-4567", "555-987-6543", "555-000-1111"],
    "amount": ["149.99", "89.50", "210.00"],
    "status": ["confirmed", "pending", "confirmed"],
})

# DataFrame with obfuscated PII column names
OBFUSCATED_DF = pd.DataFrame({
    "col_a": ["alice@example.com", "bob@example.com", "carol@example.com"],
    "amount": ["149.99", "89.50", "210.00"],
})


def test_name_heuristic_flags_email_column():
    flagged = detect_pii_columns(PII_DF)
    assert "email_address" in flagged


def test_name_heuristic_flags_phone_column():
    flagged = detect_pii_columns(PII_DF)
    assert "customer_phone" in flagged


def test_non_pii_columns_not_flagged_by_name():
    flagged = detect_pii_columns(PII_DF)
    assert "amount" not in flagged
    assert "status" not in flagged


@pytest.mark.skipif(
    not _spacy_available(),
    reason="en_core_web_lg not installed — run: python -m spacy download en_core_web_lg",
)
def test_value_scan_flags_obfuscated_email():
    """Presidio value scan should catch email values even in 'col_a'."""
    flagged = detect_pii_columns(OBFUSCATED_DF)
    assert "col_a" in flagged


def test_returns_set():
    flagged = detect_pii_columns(PII_DF)
    assert isinstance(flagged, set)


def test_empty_dataframe_returns_empty_set():
    flagged = detect_pii_columns(pd.DataFrame())
    assert flagged == set()
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/profiler/analyzers/test_pii.py -v
```

Expected: `ImportError` — pii module does not exist.

- [ ] **Step 3: Write `scripts/profiler/analyzers/pii.py`**

```python
"""PII detection using Microsoft Presidio.

Two-pass strategy:
1. Name-heuristic: flags columns whose names match known PII patterns.
2. Value-scan: runs presidio-analyzer over sampled string values for remaining columns.

Returns set[str] of flagged column names. Detection only — see sanitizer.py for
anonymization.
"""
from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)

# Lowercase substrings that indicate PII when found in a column name
_PII_NAME_PATTERNS = frozenset({
    "email", "e_mail", "phone", "mobile", "ssn", "social_security",
    "dob", "date_of_birth", "birthdate", "first_name", "last_name",
    "full_name", "address", "street", "zip", "postal", "ip_address",
    "passport", "license", "credit_card", "card_number", "account_number",
    "tax_id", "national_id", "driver",
})


def _name_heuristic_pass(df: pd.DataFrame) -> set[str]:
    flagged = set()
    for col in df.columns:
        col_lower = col.lower()
        if any(pattern in col_lower for pattern in _PII_NAME_PATTERNS):
            flagged.add(col)
    return flagged


def _value_scan_pass(df: pd.DataFrame, skip_columns: set[str]) -> set[str]:
    """Run Presidio analyzer over sampled string values for non-heuristic columns."""
    try:
        from presidio_analyzer import AnalyzerEngine
    except ImportError:
        logger.warning(
            "presidio-analyzer not installed — value-scan PII detection skipped. "
            "Run: pip install presidio-analyzer && python -m spacy download en_core_web_lg"
        )
        return set()

    try:
        analyzer = AnalyzerEngine()
    except Exception as e:
        logger.warning("Presidio AnalyzerEngine failed to initialize (%s) — value-scan skipped.", e)
        return set()

    flagged = set()
    str_cols = [
        c for c in df.select_dtypes(include=["object", "string"]).columns
        if c not in skip_columns
    ]

    for col in str_cols:
        sample_values = df[col].dropna().astype(str).head(100).tolist()
        for value in sample_values:
            results = analyzer.analyze(text=value, language="en")
            if results:
                flagged.add(col)
                break  # one hit is enough — move to next column

    return flagged


def detect_pii_columns(df: pd.DataFrame) -> set[str]:
    """Return the set of column names that likely contain PII."""
    if df.empty:
        return set()

    heuristic_flags = _name_heuristic_pass(df)
    value_scan_flags = _value_scan_pass(df, skip_columns=heuristic_flags)
    return heuristic_flags | value_scan_flags
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/profiler/analyzers/test_pii.py -v
```

Expected: 6 tests PASS. The obfuscated email test requires `en_core_web_lg` — if the spaCy model is absent, the value-scan pass logs a warning and the test will fail. If so, run `python -m spacy download en_core_web_lg` first.

- [ ] **Step 5: Commit**

```bash
git add scripts/profiler/analyzers/pii.py tests/profiler/analyzers/test_pii.py
git commit -m "feat(profiler): add PII detector — Presidio two-pass (name heuristic + value scan)"
```

---

### Task 7: dbt signals, sanitizer

**Files:**
- Create: `scripts/profiler/analyzers/dbt_signals.py`
- Create: `scripts/profiler/sanitizer.py`
- Create: `tests/profiler/analyzers/test_dbt_signals.py`
- Create: `tests/profiler/test_sanitizer.py`

- [ ] **Step 1: Write failing tests for `dbt_signals.py`**

```python
# tests/profiler/analyzers/test_dbt_signals.py
"""Unit tests — use fixture description dicts, no real ydata-profiling run."""
from __future__ import annotations

import pytest

from scripts.profiler.analyzers.dbt_signals import detect_signals
from scripts.profiler.models import DbtSignal


def _make_description(variables: dict) -> object:
    """Build a minimal description-like object from a dict of variable dicts."""
    from types import SimpleNamespace
    ns = SimpleNamespace()
    ns.variables = {k: SimpleNamespace(**v) for k, v in variables.items()}
    return ns


def test_detects_unused_column_constant():
    """n_distinct == 0 triggers UNUSED_COLUMN (constant column)."""
    desc = _make_description({
        "legacy_flag": {"type": "Unsupported", "p_missing": 0.0, "n_distinct": 0},
    })
    signals = detect_signals(desc)
    types = [s.signal_type for s in signals]
    assert "UNUSED_COLUMN" in types


def test_detects_unused_column_high_null():
    desc = _make_description({
        "reserved_col": {"type": "Text", "p_missing": 0.98, "n_distinct": 2},
    })
    signals = detect_signals(desc)
    assert any(s.signal_type == "UNUSED_COLUMN" and s.column_name == "reserved_col"
               for s in signals)


def test_detects_cast_hint_numeric_varchar():
    desc = _make_description({
        "amount": {"type": "Text", "p_missing": 0.0, "n_distinct": 50,
                   "value_counts_without_nan": {"149.99": 1, "89.50": 1}},
    })
    # Cast hints are inferred from type="Text" + numeric-looking values
    # We inject a synthetic numeric_fraction to simulate ydata-profiling output
    desc.variables["amount"].numeric_fraction = 1.0
    signals = detect_signals(desc)
    assert any(s.signal_type == "CAST_HINT" and s.column_name == "amount"
               for s in signals)


def test_detects_rename_hint_camelcase():
    desc = _make_description({
        "custID": {"type": "Text", "p_missing": 0.0, "n_distinct": 100},
    })
    signals = detect_signals(desc)
    assert any(s.signal_type == "RENAME_HINT" and s.column_name == "custID"
               for s in signals)


def test_no_false_positives_on_clean_column():
    # Use "confirmed_at" — a clean column that is not in _AMBIGUOUS_NAMES,
    # not camelCase, not Hungarian, not high-null, not constant.
    # Note: "status" IS in _AMBIGUOUS_NAMES and would trigger a RENAME_HINT.
    desc = _make_description({
        "confirmed_at": {"type": "DateTime", "p_missing": 0.0, "n_distinct": 100,
                         "numeric_fraction": 0.0},
    })
    signals = detect_signals(desc)
    assert signals == []


def test_returns_list_of_dbt_signal():
    desc = _make_description({
        "null_col": {"type": "Unsupported", "p_missing": 1.0, "n_distinct": 0},
    })
    signals = detect_signals(desc)
    assert all(isinstance(s, DbtSignal) for s in signals)
```

- [ ] **Step 2: Write failing tests for `sanitizer.py`**

```python
# tests/profiler/test_sanitizer.py
from __future__ import annotations

import pandas as pd
import pytest

from scripts.profiler.sanitizer import sanitize


def test_sanitize_replaces_pii_values(fixture_df):
    flagged = {"email_address"}
    result = sanitize(fixture_df, flagged)
    # Accept both the full Presidio path ([REDACTED:EMAIL_ADDRESS]) and the
    # import-fallback path ([REDACTED]) — both indicate successful sanitization.
    for val in result["email_address"]:
        assert "REDACTED" in val


def test_sanitize_does_not_mutate_original(fixture_df):
    original_values = fixture_df["email_address"].tolist()
    flagged = {"email_address"}
    sanitize(fixture_df, flagged)
    assert fixture_df["email_address"].tolist() == original_values


def test_sanitize_non_pii_columns_unchanged(fixture_df):
    flagged = {"email_address"}
    result = sanitize(fixture_df, flagged)
    assert result["status"].tolist() == fixture_df["status"].tolist()


def test_sanitize_empty_set_returns_copy(fixture_df):
    result = sanitize(fixture_df, set())
    assert result is not fixture_df          # must be a new object
    pd.testing.assert_frame_equal(result, fixture_df)  # with identical content


def test_sanitize_returns_new_dataframe(fixture_df):
    result = sanitize(fixture_df, {"email_address"})
    assert result is not fixture_df
```

- [ ] **Step 3: Run to verify failures**

```bash
pytest tests/profiler/analyzers/test_dbt_signals.py tests/profiler/test_sanitizer.py -v
```

Expected: `ImportError` for both.

- [ ] **Step 4: Write `scripts/profiler/analyzers/dbt_signals.py`**

```python
"""dbt-specific signal detection from ydata-profiling description output.

Reads the BaseDescription object from AnalysisResult and emits DbtSignal
objects. No statistical computation — pure interpretation of what ydata-profiling
already computed.
"""
from __future__ import annotations

import re

from scripts.profiler.models import DbtSignal

# Null fraction threshold above which a column is flagged as UNUSED
_NULL_THRESHOLD = 0.95

# Ambiguous single-word column names that warrant a RENAME_HINT
_AMBIGUOUS_NAMES = frozenset({"id", "code", "flag", "name", "type", "value",
                               "status", "date", "key", "num", "no"})

# camelCase detector
_CAMEL_CASE_RE = re.compile(r"[a-z][A-Z]")

# Hungarian notation prefixes
_HUNGARIAN_PREFIXES = ("str", "int", "flt", "dbl", "arr", "obj", "bln", "lng")


def _is_camel_case(name: str) -> bool:
    return bool(_CAMEL_CASE_RE.search(name))


def _is_hungarian(name: str) -> bool:
    lower = name.lower()
    return any(lower.startswith(p) and len(lower) > len(p) for p in _HUNGARIAN_PREFIXES)


def detect_signals(description) -> list[DbtSignal]:
    """Detect dbt-specific signals from a ydata-profiling description.

    Args:
        description: A BaseDescription object (or duck-typed equivalent with
                     a .variables attribute mapping column names to variable stats).
    """
    signals: list[DbtSignal] = []

    for col_name, var in description.variables.items():
        p_missing = getattr(var, "p_missing", 0.0) or 0.0
        n_distinct = getattr(var, "n_distinct", None)
        var_type = getattr(var, "type", "") or ""
        numeric_fraction = getattr(var, "numeric_fraction", 0.0) or 0.0

        # UNUSED_COLUMN — constant or overwhelmingly null
        if p_missing >= _NULL_THRESHOLD or n_distinct == 0:
            signals.append(DbtSignal(
                signal_type="UNUSED_COLUMN",
                column_name=col_name,
                message=(
                    f"Column is {p_missing:.0%} null or constant — "
                    "candidate for exclusion in staging SELECT."
                ),
            ))
            continue  # skip further checks on dead columns

        # CAST_HINT — VARCHAR with predominantly numeric values
        if var_type in ("Text", "Unsupported") and numeric_fraction >= 0.9:
            signals.append(DbtSignal(
                signal_type="CAST_HINT",
                column_name=col_name,
                message=(
                    f"cast({col_name} as decimal(18,4))  "
                    f"-- {numeric_fraction:.0%} of values are numeric"
                ),
            ))

        # RENAME_HINT — camelCase, Hungarian notation, or ambiguous names
        if _is_camel_case(col_name):
            signals.append(DbtSignal(
                signal_type="RENAME_HINT",
                column_name=col_name,
                message=f"camelCase detected — rename to snake_case per ALL-FMT-05.",
            ))
        elif _is_hungarian(col_name):
            signals.append(DbtSignal(
                signal_type="RENAME_HINT",
                column_name=col_name,
                message=f"Hungarian notation detected — drop type prefix.",
            ))
        elif col_name.lower() in _AMBIGUOUS_NAMES:
            signals.append(DbtSignal(
                signal_type="RENAME_HINT",
                column_name=col_name,
                message=(
                    f"'{col_name}' is ambiguous — prefix with entity name "
                    "(e.g. reservation_id, park_status)."
                ),
            ))

    return signals
```

- [ ] **Step 5: Write `scripts/profiler/sanitizer.py`**

```python
"""Presidio-based PII anonymization.

Called lazily by renderers that require redacted output (markdown always,
html only when --sanitize-html is passed). Never mutates the input DataFrame.
"""
from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def sanitize(df: pd.DataFrame, pii_columns: set[str]) -> pd.DataFrame:
    """Return a copy of df with PII column values replaced by [REDACTED:<entity>].

    Args:
        df: Raw sample DataFrame. Never mutated.
        pii_columns: Set of column names identified as containing PII.
    """
    if not pii_columns:
        return df.copy()

    try:
        from presidio_analyzer import AnalyzerEngine
        from presidio_anonymizer import AnonymizerEngine
        from presidio_anonymizer.entities import OperatorConfig
    except ImportError:
        logger.warning(
            "presidio-anonymizer not installed — returning [REDACTED] without entity type. "
            "Run: pip install presidio-anonymizer"
        )
        result = df.copy()
        for col in pii_columns:
            if col in result.columns:
                result[col] = "[REDACTED]"
        return result

    analyzer = AnalyzerEngine()
    anonymizer = AnonymizerEngine()
    result = df.copy()

    for col in pii_columns:
        if col not in result.columns:
            continue

        redacted_values = []
        for val in result[col].astype(str):
            analysis = analyzer.analyze(text=val, language="en")
            if analysis:
                entity_type = analysis[0].entity_type
                redacted = f"[REDACTED:{entity_type}]"
            else:
                redacted = "[REDACTED:PII]"
            redacted_values.append(redacted)
        result[col] = redacted_values

    return result
```

- [ ] **Step 6: Run all analyzer and sanitizer tests**

```bash
pytest tests/profiler/analyzers/ tests/profiler/test_sanitizer.py -v
```

Expected: all tests PASS.

- [ ] **Step 7: Commit**

```bash
git add scripts/profiler/analyzers/dbt_signals.py scripts/profiler/sanitizer.py \
        tests/profiler/analyzers/test_dbt_signals.py tests/profiler/test_sanitizer.py
git commit -m "feat(profiler): add dbt_signals detector and Presidio sanitizer"
```

---

## Chunk 3: Output Layer

### Task 8: Terminal renderer (`terminal.py`)

**Files:**
- Create: `scripts/profiler/renderers/terminal.py`
- Create: `tests/profiler/renderers/test_terminal.py`

- [ ] **Step 1: Write smoke tests**

```python
# tests/profiler/renderers/test_terminal.py
from __future__ import annotations

import pytest
from io import StringIO

from scripts.profiler.renderers.terminal import render_terminal
from scripts.profiler.models import DbtSignal


def test_render_terminal_no_exception(fixture_df):
    """Smoke test — must not raise."""
    render_terminal(
        df=fixture_df,
        dbt_signals=[
            DbtSignal("CAST_HINT", "amount", "cast(amount as decimal(10,2))"),
        ],
        pii_columns={"email_address"},
    )


def test_render_terminal_with_empty_signals(fixture_df):
    render_terminal(df=fixture_df, dbt_signals=[], pii_columns=set())


def test_render_terminal_with_pii_no_signals(fixture_df):
    """PII panel renders without exception even when dbt_signals is empty."""
    render_terminal(df=fixture_df, dbt_signals=[], pii_columns={"email_address"})
```

- [ ] **Step 2: Run to verify failure**

```bash
PYTHONUTF8=1 pytest tests/profiler/renderers/test_terminal.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Write `scripts/profiler/renderers/terminal.py`**

```python
"""Terminal renderer — skimpy for column stats, rich for dbt signals and PII flags.

Always use PYTHONUTF8=1 prefix on Windows/Git Bash to avoid cp1252 encoding errors
on rich console output (e.g. PYTHONUTF8=1 python scripts/profiler/cli.py ...).
"""
from __future__ import annotations

import pandas as pd
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from scripts.profiler.models import DbtSignal

console = Console()


def render_terminal(
    df: pd.DataFrame,
    dbt_signals: list[DbtSignal],
    pii_columns: set[str],
) -> None:
    """Print a compact profile to the terminal."""
    try:
        from skimpy import skim
    except ImportError as e:
        raise ImportError(
            "skimpy is required for terminal output. Run: pip install 'skimpy>=0.0.12'"
        ) from e

    skim(df)

    if dbt_signals:
        signal_text = Text()
        for s in dbt_signals:
            color = {
                "CAST_HINT": "cyan",
                "RENAME_HINT": "yellow",
                "UNUSED_COLUMN": "red",
                "NULL_PATTERN": "magenta",
            }.get(s.signal_type, "white")
            signal_text.append(f"[{s.signal_type}] ", style=f"bold {color}")
            signal_text.append(f"{s.column_name}: {s.message}\n")
        console.print(Panel(signal_text, title="dbt Signals", border_style="blue"))

    if pii_columns:
        pii_text = Text()
        for col in sorted(pii_columns):
            pii_text.append(f"  ⚠ {col}\n", style="bold yellow")
        console.print(Panel(pii_text, title="PII Columns (local surface — not redacted)", border_style="yellow"))
```

- [ ] **Step 4: Run tests**

```bash
PYTHONUTF8=1 pytest tests/profiler/renderers/test_terminal.py -v
```

Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/profiler/renderers/terminal.py tests/profiler/renderers/test_terminal.py
git commit -m "feat(profiler): add terminal renderer (skimpy + rich)"
```

---

### Task 9: Markdown renderer (`markdown.py`)

**Files:**
- Create: `scripts/profiler/renderers/markdown.py`
- Create: `tests/profiler/renderers/test_markdown.py`

> **Note:** Tests use substring assertions, not snapshot comparisons. The expected markdown fixture file originally listed here is not needed.

- [ ] **Step 1: Write snapshot tests**

```python
# tests/profiler/renderers/test_markdown.py
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from scripts.profiler.models import ColumnDef, DbtSignal, SelectionTarget
from scripts.profiler.renderers.markdown import render_markdown

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def dummy_target():
    return SelectionTarget(
        prefix="source",
        table="test_table",
        connector_type="duckdb",
        conn_str=":memory:",
        schema="main",
        resource_type="source",
    )


@pytest.fixture
def dummy_schema():
    return [
        ColumnDef("id", "VARCHAR", False),
        ColumnDef("email_address", "VARCHAR", True),
        ColumnDef("amount", "VARCHAR", True),
        ColumnDef("status", "VARCHAR", True),
    ]


def test_render_markdown_returns_string(fixture_df, dummy_target, dummy_schema):
    result = render_markdown(
        df=fixture_df,
        target=dummy_target,
        schema=dummy_schema,
        dbt_signals=[DbtSignal("CAST_HINT", "amount", "cast(amount as decimal(10,2))")],
        pii_columns={"email_address"},
        row_count=1000,
    )
    assert isinstance(result, str)
    assert len(result) > 0


def test_markdown_contains_ddl_section(fixture_df, dummy_target, dummy_schema):
    result = render_markdown(
        df=fixture_df, target=dummy_target, schema=dummy_schema,
        dbt_signals=[], pii_columns=set(), row_count=1000,
    )
    assert "CREATE TABLE" in result
    assert "test_table" in result


def test_markdown_contains_column_stats_table(fixture_df, dummy_target, dummy_schema):
    result = render_markdown(
        df=fixture_df, target=dummy_target, schema=dummy_schema,
        dbt_signals=[], pii_columns=set(), row_count=1000,
    )
    assert "| column |" in result or "| Column |" in result


def test_markdown_redacts_pii_in_sample(fixture_df, dummy_target, dummy_schema):
    result = render_markdown(
        df=fixture_df, target=dummy_target, schema=dummy_schema,
        dbt_signals=[], pii_columns={"email_address"}, row_count=1000,
    )
    assert "[REDACTED:" in result
    assert "alice@example.com" not in result


def test_markdown_contains_signals_section(fixture_df, dummy_target, dummy_schema):
    result = render_markdown(
        df=fixture_df, target=dummy_target, schema=dummy_schema,
        dbt_signals=[DbtSignal("CAST_HINT", "amount", "cast(amount as decimal(10,2))")],
        pii_columns=set(), row_count=1000,
    )
    assert "CAST_HINT" in result
    assert "amount" in result


def test_markdown_pii_section_lists_flagged_columns(fixture_df, dummy_target, dummy_schema):
    result = render_markdown(
        df=fixture_df, target=dummy_target, schema=dummy_schema,
        dbt_signals=[], pii_columns={"email_address"}, row_count=1000,
    )
    assert "email_address" in result
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/profiler/renderers/test_markdown.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Write `scripts/profiler/renderers/markdown.py`**

```python
"""LLM-optimized markdown renderer.

Produces a structured .md file designed to be pasted directly into an LLM prompt
for dbt staging model generation. Calls sanitizer.sanitize() inline for sample rows.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from scripts.profiler.models import ColumnDef, DbtSignal, SelectionTarget
from scripts.profiler import sanitizer


def render_markdown(
    df: pd.DataFrame,
    target: SelectionTarget,
    schema: list[ColumnDef],
    dbt_signals: list[DbtSignal],
    pii_columns: set[str],
    row_count: int,
    profiled_at: datetime | None = None,
) -> str:
    """Render a complete LLM-optimized markdown report as a string."""
    if profiled_at is None:
        profiled_at = datetime.now(timezone.utc)

    sanitized_df = sanitizer.sanitize(df, pii_columns)
    lines: list[str] = []

    # --- Header ---
    lines.append(f"## Source: {target.schema}.{target.table}")
    lines.append(
        f"**Profiled at:** {profiled_at.strftime('%Y-%m-%d %H:%M UTC')}  |  "
        f"**Rows sampled:** {len(df):,} of {row_count:,}\n"
    )

    # --- DDL (inferred) ---
    lines.append("## DDL (inferred)\n")
    lines.append(f"```sql")
    lines.append(f"CREATE TABLE {target.schema}.{target.table} (")
    ddl_hints = {s.column_name: s.message for s in dbt_signals if s.signal_type == "CAST_HINT"}
    col_lines = []
    for col in schema:
        comment = f"  -- {ddl_hints[col.name]}" if col.name in ddl_hints else ""
        col_lines.append(f"    {col.name:<30} {col.source_type}{comment}")
    lines.append(",\n".join(col_lines))
    lines.append(");")
    lines.append("```\n")

    # --- Column statistics ---
    lines.append("## Column Statistics\n")
    lines.append("| column | type | null_pct | n_distinct | notes |")
    lines.append("|---|---|---|---|---|")
    null_pcts = (df.isnull().sum() / max(len(df), 1) * 100).round(1)
    n_distinct = df.nunique()
    for col in schema:
        np_ = f"{null_pcts.get(col.name, 0):.1f}%"
        nd_ = str(n_distinct.get(col.name, "—"))
        notes = "⚠ PII" if col.name in pii_columns else ""
        lines.append(f"| {col.name} | {col.source_type} | {np_} | {nd_} | {notes} |")
    lines.append("")

    # --- dbt Signals ---
    if dbt_signals:
        lines.append("## dbt Signals\n")
        for s in dbt_signals:
            lines.append(f"- **{s.signal_type}** `{s.column_name}`: {s.message}")
        lines.append("")

    # --- PII columns ---
    if pii_columns:
        lines.append("## PII Columns (redacted in samples)\n")
        for col in sorted(pii_columns):
            lines.append(f"- `{col}`")
        lines.append("")

    # --- Sample rows (5 rows, PII redacted) ---
    lines.append("## Sample Rows (5 rows, PII redacted)\n")
    sample = sanitized_df.head(5)
    col_headers = " | ".join(sample.columns)
    separators = " | ".join("---" for _ in sample.columns)
    lines.append(f"| {col_headers} |")
    lines.append(f"| {separators} |")
    for _, row in sample.iterrows():
        row_str = " | ".join(str(v) for v in row)
        lines.append(f"| {row_str} |")

    return "\n".join(lines) + "\n"
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/profiler/renderers/test_markdown.py -v
```

Expected: 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/profiler/renderers/markdown.py tests/profiler/renderers/test_markdown.py
git commit -m "feat(profiler): add LLM-optimized markdown renderer with Presidio redaction"
```

---

### Task 10: HTML renderer (`html.py`)

**Files:**
- Create: `scripts/profiler/renderers/html.py`
- Create: `tests/profiler/renderers/test_html.py`

- [ ] **Step 1: Write smoke tests**

```python
# tests/profiler/renderers/test_html.py
from __future__ import annotations

from pathlib import Path
import pytest

from scripts.profiler.renderers.html import render_html
from scripts.profiler.models import DbtSignal


def test_render_html_creates_file(fixture_df, tmp_path):
    from ydata_profiling import ProfileReport
    profile = ProfileReport(fixture_df, minimal=True, title="test", progress_bar=False)
    out = tmp_path / "profile_test.html"

    render_html(
        profile=profile,
        dbt_signals=[DbtSignal("CAST_HINT", "amount", "cast(amount as decimal(10,2))")],
        pii_columns={"email_address"},
        output_path=out,
    )
    assert out.exists()
    assert out.stat().st_size > 0


def test_render_html_contains_signals_section(fixture_df, tmp_path):
    from ydata_profiling import ProfileReport
    profile = ProfileReport(fixture_df, minimal=True, title="test", progress_bar=False)
    out = tmp_path / "profile_test.html"

    render_html(
        profile=profile,
        dbt_signals=[DbtSignal("RENAME_HINT", "custID", "rename to cust_id")],
        pii_columns=set(),
        output_path=out,
    )
    content = out.read_text(encoding="utf-8")
    assert "RENAME_HINT" in content
    assert "custID" in content


def test_render_html_signals_inside_body(fixture_df, tmp_path):
    """Signals div must appear after <body>, not before <html>."""
    from ydata_profiling import ProfileReport
    profile = ProfileReport(fixture_df, minimal=True, title="test", progress_bar=False)
    out = tmp_path / "profile_test.html"

    render_html(
        profile=profile,
        dbt_signals=[DbtSignal("CAST_HINT", "amount", "cast hint")],
        pii_columns=set(),
        output_path=out,
    )
    content = out.read_text(encoding="utf-8")
    body_pos = content.find("<body")
    signals_pos = content.find("dbt-profiler-signals")
    assert body_pos != -1
    assert signals_pos > body_pos
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/profiler/renderers/test_html.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Write `scripts/profiler/renderers/html.py`**

```python
"""HTML renderer — ydata-profiling with injected dbt signals preface.

Signals are injected as a <div> immediately after the <body> opening tag,
not prepended before <html> (which would produce malformed HTML).

When --sanitize-html is active, the caller must build a second ProfileReport
from the sanitized DataFrame before calling this function.
"""
from __future__ import annotations

from pathlib import Path

from scripts.profiler.models import DbtSignal


def _render_signals_div(dbt_signals: list[DbtSignal], pii_columns: set[str]) -> str:
    """Return a self-contained HTML <div> with signals and PII summary."""
    rows = []
    for s in dbt_signals:
        color = {
            "CAST_HINT": "#17a2b8",
            "RENAME_HINT": "#ffc107",
            "UNUSED_COLUMN": "#dc3545",
            "NULL_PATTERN": "#6f42c1",
        }.get(s.signal_type, "#6c757d")
        rows.append(
            f'<tr><td style="color:{color};font-weight:bold">{s.signal_type}</td>'
            f"<td><code>{s.column_name}</code></td>"
            f"<td>{s.message}</td></tr>"
        )

    signals_table = ""
    if rows:
        signals_table = (
            "<h4>dbt Signals</h4>"
            '<table border="1" cellpadding="4" style="border-collapse:collapse;width:100%">'
            "<tr><th>Type</th><th>Column</th><th>Message</th></tr>"
            + "".join(rows)
            + "</table>"
        )

    pii_section = ""
    if pii_columns:
        pii_items = "".join(f"<li><code>{c}</code></li>" for c in sorted(pii_columns))
        pii_section = f"<h4>⚠ PII Columns</h4><ul>{pii_items}</ul>"

    if not signals_table and not pii_section:
        return ""

    return (
        '<div id="dbt-profiler-signals" style="'
        "background:#f8f9fa;border:1px solid #dee2e6;border-radius:4px;"
        'padding:16px;margin:16px 0">'
        "<h3>dbt-profiler Signals</h3>"
        + signals_table
        + pii_section
        + "</div>"
    )


def render_html(
    profile,
    dbt_signals: list[DbtSignal],
    pii_columns: set[str],
    output_path: Path,
) -> None:
    """Render the ydata-profiling report to HTML with an injected signals section.

    Args:
        profile: A ydata_profiling.ProfileReport instance.
        dbt_signals: List of DbtSignal objects to display in the preface.
        pii_columns: Set of PII-flagged column names.
        output_path: Path to write the final .html file.
    """
    try:
        report_html: str = profile.to_html()
    except Exception as e:
        raise RuntimeError(f"ydata-profiling HTML generation failed: {e}") from e

    signals_div = _render_signals_div(dbt_signals, pii_columns)

    if signals_div:
        # Inject immediately after <body> opening — not before <html>
        combined = report_html.replace("<body>", "<body>" + signals_div, 1)
        # Guard: if ydata-profiling ever adds attributes to <body> (e.g. <body class="...">),
        # the replace will silently no-op. Detect this and raise rather than silently drop signals.
        if combined == report_html:
            raise RuntimeError(
                "dbt-profiler: signals injection failed — exact '<body>' tag not found in "
                "ydata-profiling HTML output. The template may have changed."
            )
    else:
        combined = report_html

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(combined, encoding="utf-8")
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/profiler/renderers/test_html.py -v
```

Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/profiler/renderers/html.py tests/profiler/renderers/test_html.py
git commit -m "feat(profiler): add HTML renderer (ydata-profiling + injected signals div)"
```

---

### Task 11: CLI entrypoint and cleanup

**Files:**
- Create: `scripts/profiler/cli.py`
- Delete: `scripts/inspect_source.py`
- Create: `tests/profiler/test_cli.py`

- [ ] **Step 1: Write smoke tests for the CLI**

```python
# tests/profiler/test_cli.py
"""Smoke tests for the CLI — mock the full pipeline to avoid live dbt invocations."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from scripts.profiler import cli


@pytest.fixture
def mock_pipeline(fixture_df, tmp_path):
    """Patch selector, connector, and analyzers to avoid real I/O."""
    from datetime import datetime, timezone
    from scripts.profiler.models import (
        AnalysisResult, DbtSignal, SelectionTarget,
    )
    from ydata_profiling import ProfileReport

    target = SelectionTarget(
        prefix="source", table="test_table", connector_type="duckdb",
        conn_str=":memory:", schema="main", resource_type="source",
    )
    profile = ProfileReport(fixture_df, minimal=True, title="test_table", progress_bar=False)
    result = AnalysisResult(
        target=target,
        profile=profile,
        description=profile.get_description(),
        sample=fixture_df,
        pii_columns={"email_address"},
        dbt_signals=[DbtSignal("CAST_HINT", "amount", "cast(amount as decimal(10,2))")],
        profiled_at=datetime(2026, 3, 15, tzinfo=timezone.utc),
    )
    return result, target, tmp_path


def test_cli_terminal_output_no_exception(mock_pipeline):
    result, target, tmp_path = mock_pipeline
    with patch("scripts.profiler.cli.resolve_selector", return_value=[target]), \
         patch("scripts.profiler.cli._build_connector") as mock_conn, \
         patch("scripts.profiler.cli.build_analysis_result", return_value=result), \
         patch("scripts.profiler.cli.detect_pii_columns", return_value={"email_address"}), \
         patch("scripts.profiler.cli.detect_signals", return_value=result.dbt_signals), \
         patch("scripts.profiler.cli.render_terminal"):
        mock_conn.return_value.get_schema.return_value = []
        mock_conn.return_value.get_sample.return_value = result.sample
        cli.run(["--select", "test_table", "--output", "terminal"])


def test_cli_markdown_creates_file(mock_pipeline, tmp_path):
    result, target, _ = mock_pipeline
    with patch("scripts.profiler.cli.resolve_selector", return_value=[target]), \
         patch("scripts.profiler.cli._build_connector") as mock_conn, \
         patch("scripts.profiler.cli.build_analysis_result", return_value=result), \
         patch("scripts.profiler.cli.detect_pii_columns", return_value={"email_address"}), \
         patch("scripts.profiler.cli.detect_signals", return_value=result.dbt_signals), \
         patch("scripts.profiler.cli.render_markdown", return_value="# test\n") as mock_md, \
         patch("scripts.profiler.cli._output_dir", return_value=tmp_path):
        mock_conn.return_value.get_schema.return_value = []
        mock_conn.return_value.get_sample.return_value = result.sample
        cli.run(["--select", "test_table", "--output", "markdown"])
        mock_md.assert_called_once()
        # Verify a markdown file was actually written to tmp_path
        md_files = list(tmp_path.glob("profile_test_table_*.md"))
        assert len(md_files) == 1, f"Expected 1 markdown file, found: {md_files}"
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/profiler/test_cli.py -v
```

Expected: `ImportError` — cli module does not exist.

- [ ] **Step 3: Write `scripts/profiler/cli.py`**

```python
"""CLI entrypoint for dbt-profiler.

Usage:
    PYTHONUTF8=1 python scripts/profiler/cli.py --select stg_parks__facilities
    PYTHONUTF8=1 python scripts/profiler/cli.py --select "source:reservations.transactions" --output markdown
    PYTHONUTF8=1 python scripts/profiler/cli.py --select fct_reservations --output terminal,markdown,html --sample 5000
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from scripts.profiler.analyzers.dbt_signals import detect_signals
from scripts.profiler.analyzers.pii import detect_pii_columns
from scripts.profiler.analyzers.stats import build_analysis_result
from scripts.profiler.connectors.base import BaseConnector
from scripts.profiler.models import SelectionTarget
from scripts.profiler.selector import resolve_selector


def _build_connector(target: SelectionTarget) -> BaseConnector:
    if target.connector_type == "duckdb":
        from scripts.profiler.connectors.duckdb import DuckDBConnector
        return DuckDBConnector(target)
    elif target.connector_type == "bigquery":
        from scripts.profiler.connectors.bigquery import BigQueryConnector
        return BigQueryConnector(target)
    raise ValueError(f"Unknown connector type: {target.connector_type!r}")


def _output_dir() -> Path:
    p = Path("tmp")
    p.mkdir(exist_ok=True)
    return p


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def run(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="dbt-profiler",
        description="Profile any dbt node (source or model) with LLM-ready output.",
    )
    parser.add_argument("--select", required=True, help="dbt node selector")
    parser.add_argument(
        "--output",
        default="terminal",
        help="Comma-separated output modes: terminal, markdown, html, all",
    )
    parser.add_argument("--sample", type=int, default=1000, help="Rows to sample")
    parser.add_argument(
        "--full-profile", action="store_true",
        help="Enable full ydata-profiling (correlations, interactions)",
    )
    parser.add_argument(
        "--env", choices=["local", "prod"], default="local",
        help="'local' uses DuckDB target; 'prod' uses BigQuery",
    )
    parser.add_argument(
        "--sanitize-html", action="store_true",
        help="Redact PII in HTML sample rows (builds a second ProfileReport — slower)",
    )
    parser.add_argument("--verbose", action="store_true", help="Show full tracebacks")

    args = parser.parse_args(argv)

    connector_type = "bigquery" if args.env == "prod" else "duckdb"
    modes = {m.strip() for m in args.output.split(",")}
    if "all" in modes:
        modes = {"terminal", "markdown", "html"}

    try:
        targets = resolve_selector(args.select, connector_type=connector_type)
    except Exception as e:
        print(f"[error] Could not resolve selector '{args.select}': {e}", file=sys.stderr)
        if args.verbose:
            raise
        sys.exit(1)

    for target in targets:
        print(f"\nProfiling: {target.schema}.{target.table}")
        try:
            _profile_target(target, args, modes)
        except Exception as e:
            print(f"[error] Failed to profile {target.table}: {e}", file=sys.stderr)
            if args.verbose:
                raise


def _profile_target(target: SelectionTarget, args, modes: set[str]) -> None:
    from scripts.profiler.renderers.terminal import render_terminal

    connector = _build_connector(target)
    schema = connector.get_schema()
    df = connector.get_sample(n_rows=args.sample)

    row_count_result = None
    try:
        import duckdb
        con = duckdb.connect(target.conn_str, read_only=True)
        row_count_result = con.execute(
            f"SELECT COUNT(*) FROM {target.schema}.{target.table}"
        ).fetchone()[0]
        con.close()
    except Exception:
        row_count_result = len(df)

    result = build_analysis_result(df, target, minimal=not args.full_profile)
    result.pii_columns = detect_pii_columns(df)
    result.dbt_signals = detect_signals(result.description)

    ts = _timestamp()
    out_dir = _output_dir()

    if "terminal" in modes:
        render_terminal(
            df=df,
            dbt_signals=result.dbt_signals,
            pii_columns=result.pii_columns,
        )

    if "markdown" in modes:
        from scripts.profiler.renderers.markdown import render_markdown
        md = render_markdown(
            df=df,
            target=target,
            schema=schema,
            dbt_signals=result.dbt_signals,
            pii_columns=result.pii_columns,
            row_count=row_count_result,
        )
        md_path = out_dir / f"profile_{target.table}_{ts}.md"
        md_path.write_text(md, encoding="utf-8")
        print(f"  Markdown → {md_path}")

    if "html" in modes:
        from scripts.profiler.renderers.html import render_html
        profile_for_html = result.profile
        if args.sanitize_html:
            from scripts.profiler import sanitizer
            from ydata_profiling import ProfileReport
            sanitized_df = sanitizer.sanitize(df, result.pii_columns)
            profile_for_html = ProfileReport(
                sanitized_df, minimal=not args.full_profile,
                title=target.table, progress_bar=False,
            )
        html_path = out_dir / f"profile_{target.table}_{ts}.html"
        render_html(
            profile=profile_for_html,
            dbt_signals=result.dbt_signals,
            pii_columns=result.pii_columns,
            output_path=html_path,
        )
        print(f"  HTML → {html_path}")


if __name__ == "__main__":
    run()
```

- [ ] **Step 4: Run CLI tests**

```bash
PYTHONUTF8=1 pytest tests/profiler/test_cli.py -v
```

Expected: 2 PASS.

- [ ] **Step 5: Run the full test suite**

```bash
PYTHONUTF8=1 pytest tests/profiler/ -v
```

Expected: all tests PASS. Note any failures and fix before proceeding.

- [ ] **Step 6: Smoke-test the real CLI against a live DuckDB source**

```bash
source .venv/Scripts/activate
PYTHONUTF8=1 python scripts/profiler/cli.py \
  --select "source:vistareserve.reservations" \
  --output terminal \
  --sample 100
```

Expected: skimpy stats table + rich panels printed to terminal, no tracebacks.

- [ ] **Step 7: Remove `scripts/inspect_source.py`**

```bash
git rm scripts/inspect_source.py
```

> **Note:** `git rm` automatically stages the deletion. No separate `git add` is needed for the deleted file. It will be included in the Step 9 commit.

- [ ] **Step 8: Update `CLAUDE.md` reference**

In `CLAUDE.md`, find the rule that references `inspect_source.py` (Operating Principle 25) and update it:

Old:
```
run `python scripts/inspect_source.py --type <duckdb|bigquery> --conn <path_to_db> --table <schema.table_name>`
```

New:
```
run `python scripts/profiler/cli.py --select <selector>` to profile a source or model before staging.
```

- [ ] **Step 9: Final commit**

```bash
git add scripts/profiler/cli.py tests/profiler/test_cli.py CLAUDE.md
git commit -m "feat(profiler): add CLI entrypoint, remove inspect_source.py, update CLAUDE.md

Completes the dbt-profiler implementation. Replaces scripts/inspect_source.py
with a modular utility supporting dbt node selection, three output formats,
and Presidio PII sanitization."
```

---

## Post-Implementation Checklist

- [ ] All tests pass: `PYTHONUTF8=1 pytest tests/profiler/ -v`
- [ ] Terminal smoke test works against a real DuckDB source
- [ ] Markdown output written to `tmp/` and readable
- [ ] HTML output opens in a browser without errors
- [ ] `scripts/inspect_source.py` is deleted
- [ ] `CLAUDE.md` Operating Principle 25 updated
- [ ] `requirements.txt` committed with new dependencies
