# Phase 0: `_core/` Shared Infrastructure — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract connectors, renderers, selector, and config from the profiler into a shared `scripts/_core/` package so all downstream packages (grain, llm_context, scaffold, preflight) can reuse them.

**Architecture:** Copy profiler's connectors and renderers to `_core/`, add `run_query()` to the connector ABC, create a shared selector and config module, then update profiler imports to use `_core/` via thin wrappers. The profiler continues to work identically — this is a non-breaking extraction.

**Tech Stack:** Python 3.10+, dbt-core (dbtRunner), DuckDB, pandas, rich

**Spec:** `docs/superpowers/specs/2026-03-20-scripts-redesign-design.md` (sections: "Shared Infrastructure: `_core/`" and "Phase 0: `_core/` Extraction")

---

### Task 1: Create `_core/` directory structure and shared models

**Files:**
- Create: `scripts/_core/__init__.py`
- Create: `scripts/_core/models.py`
- Create: `scripts/_core/connectors/__init__.py`
- Create: `scripts/_core/renderers/__init__.py`
- Test: `tests/scripts/test_core_models.py`

- [ ] **Step 1: Write test for shared dataclasses**

```python
# tests/scripts/test_core_models.py
from scripts._core.models import SelectionTarget, ColumnDef


def test_selection_target_creation():
    target = SelectionTarget(
        prefix="model",
        table="fct_reservations",
        connector_type="duckdb",
        conn_str="target/dcr_analytics.duckdb",
        schema="main",
        resource_type="model",
    )
    assert target.prefix == "model"
    assert target.table == "fct_reservations"
    assert target.database == ""  # default for model nodes


def test_column_def_creation():
    col = ColumnDef(name="reservation_id", source_type="VARCHAR", nullable=False)
    assert col.name == "reservation_id"
    assert col.nullable is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/scripts/test_core_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts._core'`

- [ ] **Step 3: Create `_core/` package with models**

Create `scripts/_core/__init__.py` (empty).
Create `scripts/_core/connectors/__init__.py` (empty).
Create `scripts/_core/renderers/__init__.py` (empty).

Copy `SelectionTarget` and `ColumnDef` from `scripts/profiler/models.py` to `scripts/_core/models.py`. Remove the `AnalysisResult`, `DbtSignal`, and ydata-profiling TYPE_CHECKING imports — those stay in the profiler's own `models.py`. Keep only the two shared dataclasses.

```python
# scripts/_core/models.py
"""Shared dataclasses for all scripts packages."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass
class SelectionTarget:
    """A resolved dbt node ready for analysis."""
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/scripts/test_core_models.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/_core/ tests/scripts/test_core_models.py
git commit -m "feat(_core): create shared models package with SelectionTarget and ColumnDef"
```

---

### Task 2: Extract connectors to `_core/` with `run_query()` method

**Files:**
- Create: `scripts/_core/connectors/base.py`
- Create: `scripts/_core/connectors/duckdb.py`
- Create: `scripts/_core/connectors/bigquery.py`
- Reference: `scripts/profiler/connectors/base.py` (source for extraction)
- Reference: `scripts/profiler/connectors/duckdb.py` (source for extraction)
- Reference: `scripts/profiler/connectors/bigquery.py` (source for extraction)
- Test: `tests/scripts/test_core_connectors.py`

- [ ] **Step 1: Write test for base connector ABC and DuckDB `run_query()`**

```python
# tests/scripts/test_core_connectors.py
import pytest
import pandas as pd
from scripts._core.connectors.base import BaseConnector
from scripts._core.models import SelectionTarget, ColumnDef


def test_base_connector_is_abstract():
    """BaseConnector cannot be instantiated directly."""
    target = SelectionTarget(
        prefix="model", table="test", connector_type="duckdb",
        conn_str="test.duckdb", schema="main", resource_type="model",
    )
    with pytest.raises(TypeError):
        BaseConnector(target)


def test_duckdb_run_query(tmp_path):
    """DuckDBConnector.run_query() executes SQL and returns a DataFrame."""
    import duckdb

    db_path = str(tmp_path / "test.duckdb")
    conn = duckdb.connect(db_path)
    conn.execute("CREATE TABLE test_table (id INTEGER, name VARCHAR)")
    conn.execute("INSERT INTO test_table VALUES (1, 'a'), (2, 'b'), (3, 'c')")
    conn.close()

    from scripts._core.connectors.duckdb import DuckDBConnector

    target = SelectionTarget(
        prefix="model", table="test_table", connector_type="duckdb",
        conn_str=db_path, schema="main", resource_type="model",
    )
    connector = DuckDBConnector(target)
    result = connector.run_query("SELECT count(*) as cnt FROM main.test_table")
    assert isinstance(result, pd.DataFrame)
    assert result["cnt"].iloc[0] == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/scripts/test_core_connectors.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts._core.connectors.base'`

- [ ] **Step 3: Create `_core/connectors/` with base, duckdb, bigquery**

Copy `scripts/profiler/connectors/base.py` to `scripts/_core/connectors/base.py`. Add `run_query()` abstract method:

```python
# scripts/_core/connectors/base.py
"""Abstract base class for all database connectors."""
from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

from scripts._core.models import ColumnDef, SelectionTarget


class BaseConnector(ABC):
    """Connects to a data source and exposes schema + sample + query."""

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

    @abstractmethod
    def run_query(self, sql: str) -> pd.DataFrame:
        """Execute arbitrary analytical SQL and return results as a DataFrame."""
        ...
```

Copy `scripts/profiler/connectors/duckdb.py` to `scripts/_core/connectors/duckdb.py`. Update imports to use `scripts._core.models` and `scripts._core.connectors.base`. Add `run_query()` implementation:

```python
def run_query(self, sql: str) -> pd.DataFrame:
    """Execute SQL against the DuckDB connection and return a DataFrame."""
    return self._conn.execute(sql).df()
```

Copy `scripts/profiler/connectors/bigquery.py` to `scripts/_core/connectors/bigquery.py`. Update imports. Add `run_query()` implementation:

```python
def run_query(self, sql: str) -> pd.DataFrame:
    """Execute SQL against BigQuery and return a DataFrame."""
    return self._client.query(sql).to_dataframe()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/scripts/test_core_connectors.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/_core/connectors/ tests/scripts/test_core_connectors.py
git commit -m "feat(_core): extract connectors from profiler with run_query() method"
```

---

### Task 3: Extract renderers to `_core/` and create LLM renderer

**Files:**
- Create: `scripts/_core/renderers/terminal.py`
- Create: `scripts/_core/renderers/markdown.py`
- Create: `scripts/_core/renderers/html.py`
- Create: `scripts/_core/renderers/llm.py`
- Reference: `scripts/profiler/renderers/` (source for extraction)
- Test: `tests/scripts/test_core_renderers.py`

- [ ] **Step 1: Write test for LLM renderer**

The terminal/markdown/html renderers are copies of existing tested code. Focus the new test on the LLM renderer which is new.

```python
# tests/scripts/test_core_renderers.py
from scripts._core.renderers.llm import render_llm_context


def test_render_llm_context_basic():
    """LLM renderer produces structured markdown with labeled sections."""
    sections = {
        "Model": "fct_reservations",
        "Layer": "Mart (fact)",
        "Grain": "One row per reservation",
        "Parents": ["int_contacts", "int_parks"],
    }
    output = render_llm_context(sections)
    assert "## Model" in output
    assert "fct_reservations" in output
    assert "## Grain" in output
    assert "int_contacts" in output
    # Should not contain rich formatting or decorative characters
    assert "═" not in output
    assert "[bold]" not in output


def test_render_llm_context_with_prompt():
    """LLM renderer includes a suggested prompt section when provided."""
    sections = {
        "Model": "int_parks",
    }
    prompt = "I have a parks integration model. How should I add a new source?"
    output = render_llm_context(sections, suggested_prompt=prompt)
    assert "## Suggested Prompt" in output
    assert "How should I add a new source?" in output
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/scripts/test_core_renderers.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [x] **Step 3: Copy existing renderers and create LLM renderer**

`llm.py` was created as specified (see below). `terminal.py`, `markdown.py`, and `html.py` were NOT copied — these renderers import `AnalysisResult` (profiler-specific type) and `scripts.profiler.sanitizer` (profiler-specific module). Copying them would create a backwards dependency from `_core` → `profiler`. These three renderers stay in `scripts/profiler/renderers/` and will be addressed in Phase 6 when the full profiler migration occurs.

Create `scripts/_core/renderers/llm.py`:

```python
# scripts/_core/renderers/llm.py
"""LLM-optimized renderer: structured markdown for pasting into Gemini or other LLMs."""
from __future__ import annotations


def render_llm_context(
    sections: dict[str, str | list[str]],
    suggested_prompt: str | None = None,
) -> str:
    """Render sections as clean markdown optimized for LLM consumption.

    Args:
        sections: Ordered dict of section_name -> content.
            Content can be a string or list of strings (rendered as bullets).
        suggested_prompt: Optional pre-written prompt for the analyst to paste.

    Returns:
        Markdown string with no decorative formatting.
    """
    lines: list[str] = []
    for heading, content in sections.items():
        lines.append(f"## {heading}")
        if isinstance(content, list):
            for item in content:
                lines.append(f"- {item}")
        else:
            lines.append(str(content))
        lines.append("")

    if suggested_prompt:
        lines.append("## Suggested Prompt")
        lines.append(suggested_prompt)
        lines.append("")

    return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/scripts/test_core_renderers.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/_core/renderers/ tests/scripts/test_core_renderers.py
git commit -m "feat(_core): extract renderers from profiler, add LLM renderer"
```

---

### Task 4: Create `_core/config.py` — Environment and manifest resolution

**Files:**
- Create: `scripts/_core/config.py`
- Test: `tests/scripts/test_core_config.py`

- [ ] **Step 1: Write test for manifest staleness detection**

```python
# tests/scripts/test_core_config.py
import time
from pathlib import Path

from scripts._core.config import is_manifest_stale, detect_environment


def test_manifest_stale_when_missing(tmp_path):
    """Manifest is stale when it doesn't exist."""
    manifest = tmp_path / "target" / "manifest.json"
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    (models_dir / "test.sql").write_text("select 1")
    assert is_manifest_stale(manifest, models_dir) is True


def test_manifest_stale_when_older_than_model(tmp_path):
    """Manifest is stale when a model file is newer."""
    target_dir = tmp_path / "target"
    target_dir.mkdir()
    manifest = target_dir / "manifest.json"
    manifest.write_text("{}")

    time.sleep(0.1)  # ensure different mtime

    models_dir = tmp_path / "models"
    models_dir.mkdir()
    (models_dir / "test.sql").write_text("select 1")

    assert is_manifest_stale(manifest, models_dir) is True


def test_manifest_fresh_when_newer(tmp_path):
    """Manifest is fresh when it's newer than all model files."""
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    (models_dir / "test.sql").write_text("select 1")

    time.sleep(0.1)

    target_dir = tmp_path / "target"
    target_dir.mkdir()
    manifest = target_dir / "manifest.json"
    manifest.write_text("{}")

    assert is_manifest_stale(manifest, models_dir) is False


def test_detect_environment_duckdb(tmp_path):
    """Detects DuckDB when profiles.yml has type: duckdb."""
    profiles = tmp_path / "profiles.yml"
    profiles.write_text(
        "dcr_analytics:\n"
        "  target: dev\n"
        "  outputs:\n"
        "    dev:\n"
        "      type: duckdb\n"
        "      path: target/dcr_analytics.duckdb\n"
    )
    result = detect_environment(profiles_paths=[profiles])
    assert result == "duckdb"


def test_detect_environment_bigquery(tmp_path):
    """Detects BigQuery when profiles.yml has type: bigquery."""
    profiles = tmp_path / "profiles.yml"
    profiles.write_text(
        "dcr_analytics:\n"
        "  target: prod\n"
        "  outputs:\n"
        "    prod:\n"
        "      type: bigquery\n"
        "      project: my-project\n"
    )
    result = detect_environment(profiles_paths=[profiles])
    assert result == "bigquery"


def test_detect_environment_default_when_missing():
    """Returns duckdb when no profiles.yml found."""
    from pathlib import Path
    result = detect_environment(profiles_paths=[Path("/nonexistent/profiles.yml")])
    assert result == "duckdb"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/scripts/test_core_config.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement `config.py`**

```python
# scripts/_core/config.py
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
        raise RuntimeError(
            f"Manifest is stale and `dbt parse` failed. "
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
            for profile_name, profile_data in profiles.items():
                if isinstance(profile_data, dict):
                    target_name = profile_data.get("target", "dev")
                    outputs = profile_data.get("outputs", {})
                    target_config = outputs.get(target_name, {})
                    adapter = target_config.get("type", "duckdb")
                    return adapter
    return "duckdb"  # default
```

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/scripts/test_core_config.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/_core/config.py tests/scripts/test_core_config.py
git commit -m "feat(_core): add config module with manifest staleness detection"
```

---

### Task 5: Create `_core/selector.py` — Shared dbt selector resolution

**Files:**
- Create: `scripts/_core/selector.py`
- Reference: `scripts/profiler/selector.py` (source for extraction)
- Test: `tests/scripts/test_core_selector.py`

- [ ] **Step 1: Write test for selector resolution**

This test requires a dbt project with a compiled manifest, so it's an integration test. Write a unit test for the helper functions and mark the integration test.

```python
# tests/scripts/test_core_selector.py
import pytest
from scripts._core.selector import _determine_layer


def test_determine_layer_staging():
    assert _determine_layer("stg_vistareserve__reservations") == "staging"


def test_determine_layer_integration():
    assert _determine_layer("int_parks") == "integration"


def test_determine_layer_fact():
    assert _determine_layer("fct_reservations") == "marts"


def test_determine_layer_dimension():
    assert _determine_layer("dim_parks") == "marts"


def test_determine_layer_report():
    assert _determine_layer("rpt_park_revenue_summary") == "marts"


def test_determine_layer_base():
    assert _determine_layer("base_vistareserve__deduped") == "base"


def test_determine_layer_unknown():
    assert _determine_layer("some_random_model") == "unknown"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/scripts/test_core_selector.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement selector.py**

Extract the core logic from `scripts/profiler/selector.py`. The key addition is `_determine_layer()` which all linters need.

```python
# scripts/_core/selector.py
"""Shared dbt selector resolution.

All packages delegate --select parsing to this module.
Delegates to dbtRunner for actual resolution.
"""
from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
from typing import Literal

from scripts._core.config import ensure_manifest
from scripts._core.models import SelectionTarget


MANIFEST_PATH = Path("target/manifest.json")


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


def _determine_layer(model_name: str) -> str:
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
    """Invoke dbt ls and return unique node IDs."""
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
    import os

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
        env_path = os.environ.get("PROFILER_DUCKDB_PATH")
        conn_str = env_path if env_path else str(Path("target") / "dcr_analytics.duckdb")
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/scripts/test_core_selector.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/_core/selector.py tests/scripts/test_core_selector.py
git commit -m "feat(_core): add shared selector with layer detection"
```

---

### Task 6: Update profiler imports to use `_core/` as thin wrappers

**Files:**
- Modify: `scripts/profiler/models.py` — import and re-export from `_core`
- Modify: `scripts/profiler/connectors/base.py` — re-export from `_core`
- Modify: `scripts/profiler/connectors/duckdb.py` — re-export from `_core`
- Modify: `scripts/profiler/connectors/bigquery.py` — re-export from `_core`

- [ ] **Step 1: Update profiler's `models.py` to import shared dataclasses from `_core`**

Keep `AnalysisResult` and `DbtSignal` in the profiler's `models.py`. Import `SelectionTarget` and `ColumnDef` from `_core` and re-export them so existing profiler code doesn't break.

Add at the top of `scripts/profiler/models.py`:
```python
from scripts._core.models import SelectionTarget, ColumnDef  # noqa: F401 — re-export
```

Remove the duplicate `SelectionTarget` and `ColumnDef` class definitions from `scripts/profiler/models.py`.

- [ ] **Step 2: Update profiler connector imports**

In `scripts/profiler/connectors/base.py`, replace the local `BaseConnector` with a re-export:
```python
from scripts._core.connectors.base import BaseConnector  # noqa: F401
```

Likewise for `duckdb.py` and `bigquery.py` — re-export from `_core` or update imports to use `_core.connectors.base.BaseConnector` and `_core.models.SelectionTarget`.

- [ ] **Step 3: Verify profiler still works end-to-end**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/ -v -k "profiler" --timeout=60`

If no profiler tests exist, run the profiler CLI manually:
```bash
source .venv/Scripts/activate && PYTHONUTF8=1 python -m scripts.profiler.cli --select stg_vistareserve__reservations --output terminal --sample 10
```
Expected: Same output as before. No import errors.

- [ ] **Step 4: Commit**

```bash
git add scripts/profiler/
git commit -m "refactor(profiler): import shared models and connectors from _core"
```

---

### Task 7: Add sqlglot dependency

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add sqlglot to requirements.txt**

Add `sqlglot>=20.0` to `requirements.txt` (after the existing dependencies).

- [ ] **Step 2: Install**

Run: `source .venv/Scripts/activate && pip install sqlglot>=20.0`

- [ ] **Step 3: Verify import**

Run: `source .venv/Scripts/activate && python -c "import sqlglot; print(sqlglot.__version__)"`
Expected: Version number printed.

- [ ] **Step 4: Commit**

```bash
git add requirements.txt
git commit -m "deps: add sqlglot for SQL AST parsing in grain package"
```
