# dbt-profiler — Design Spec

**Date:** 2026-03-15
**Status:** Draft
**Replaces:** `scripts/inspect_source.py`

---

## Overview

A modular Python profiling utility purpose-built for dbt workflows. Given any dbt
node selector, it profiles the underlying table or view and produces three output
formats: a compact terminal summary, a markdown report optimized for LLM consumption,
and a full interactive HTML report. PII is detected via Microsoft Presidio and
redacted before any LLM-destined output.

---

## Goals

- Replace `scripts/inspect_source.py` with a cleaner, extensible design
- Support profiling of any dbt node — raw sources, staging, integration, or mart models
- Generate LLM-ready markdown containing DDL, column statistics, dbt-specific signals,
  and sanitized sample rows to support staging model generation and code review
- Detect PII using Microsoft Presidio before any markdown output
- Leverage `ydata-profiling` as the statistical engine and `skimpy` for terminal output
  rather than reimplementing statistics from scratch

## Non-Goals

- dbt manifest-aware graph traversal (`+`, `tag:`, `path:`) — deferred; manifest is
  used for node resolution but complex graph operations are out of scope for v1
- Cross-node fan-out detection (requires querying two nodes and comparing sums) — v2
- Automatic staging model code generation — the markdown output feeds an LLM prompt;
  generation itself is out of scope
- Real-time or streaming profiling — batch, sample-based only

---

## Package Structure

```
scripts/profiler/
├── cli.py                  # Argparse entry point; wires all layers together
├── selector.py             # Resolves --select syntax via dbtRunner + manifest
├── connectors/
│   ├── base.py             # BaseConnector ABC: get_schema() + get_sample()
│   ├── duckdb.py           # DuckDB implementation (local dev, source: and model:)
│   └── bigquery.py         # BigQuery implementation (prod, source: and model:)
├── analyzers/
│   ├── stats.py            # ydata-profiling orchestrator → AnalysisResult
│   ├── dbt_signals.py      # dbt-specific signals from AnalysisResult
│   └── pii.py              # Presidio analyzer wrapper
├── renderers/
│   ├── terminal.py         # skimpy + rich
│   ├── markdown.py         # Custom LLM-optimized markdown; calls sanitizer directly
│   └── html.py             # ydata-profiling HTML output
└── sanitizer.py            # Presidio anonymizer — called by renderers that need redaction
```

---

## Data Flow

```
CLI: --select <selector> --output <modes> --sample <n>
        │
        ▼
selector.py
  dbtRunner.invoke(["ls", "--select", selector, "--output", "selector"])
  → iterate result.result (one unique_id per entry)
  manifest.json → nodes[unique_id] → {database, schema, name, resource_type}
  → SelectionTarget
        │
        ▼
connector (duckdb.py or bigquery.py)
  get_schema() → list[ColumnDef]
  get_sample(n_rows) → pd.DataFrame
        │
        ▼
analyzers/
  stats.py        → ProfileReport(df, minimal=True) → description → AnalysisResult
  pii.py          → name-heuristic pass + Presidio value-scan → pii_columns: set[str]
  dbt_signals.py  → AnalysisResult → list[DbtSignal]
        │
        ▼
renderers/ (one or more, single pass over AnalysisResult)
  terminal.py  → skimpy.skim(df) + rich panels for signals and PII flags → stdout
  markdown.py  → calls sanitizer.py → DDL + stats + signals + redacted sample → .md
  html.py      → profile.to_html() buffer + prepended signals block → .html
```

`sanitizer.py` is called lazily by individual renderers that require redaction
(`markdown.py` always; `html.py` only when `--sanitize-html` is passed). It is not
a pipeline stage that runs unconditionally.

---

## CLI Interface

```bash
# Profile a raw source, terminal output (default)
python scripts/profiler/cli.py --select "source:reservations.transactions"

# Profile a staging model, markdown output for LLM
python scripts/profiler/cli.py --select stg_parks__facilities --output markdown

# Profile a mart, all outputs, custom sample size
python scripts/profiler/cli.py --select fct_reservations --output terminal,markdown,html --sample 5000

# Full ydata-profiling report (includes correlations, interactions)
python scripts/profiler/cli.py --select stg_parks__facilities --output html --full-profile

# Production environment
python scripts/profiler/cli.py --select "source:reservations.transactions" --env prod
```

**Flags:**

| Flag | Default | Description |
|---|---|---|
| `--select` | required | dbt node selector (source: prefix or bare model name) |
| `--output` | `terminal` | Comma-separated: `terminal`, `markdown`, `html`, or `all` |
| `--sample` | `1000` | Number of rows to sample |
| `--full-profile` | false | Enable full ydata-profiling (correlations, interactions) |
| `--env` | `local` | `local` (DuckDB target) or `prod` (BigQuery). v1 maps directly to connector type; a future version should read the active target from `profiles.yml` instead. |
| `--sanitize-html` | false | Redact PII in HTML sample rows as well |
| `--verbose` | false | Show full tracebacks on error |

---

## Selection & Resolution

`selector.py` does not implement any selector grammar. It delegates to dbt:

1. Invokes `dbtRunner.invoke(["ls", "--select", selector, "--output", "selector"])`.
   Uses `--output selector` (the default) rather than `--output json` — the JSON
   output format changes between dbt-core minor versions and the dbtRunner result
   object exposes a clean iterable via `result.result` regardless of format. Each
   entry in `result.result` is a unique node ID string
   (e.g. `model.dcr_analytics.stg_parks__facilities`).
2. Loads `target/manifest.json` and looks up each unique ID in `manifest["nodes"]`
   (for models) or `manifest["sources"]` (for source nodes) to extract `database`,
   `schema`, `name`, and `resource_type`.
3. Returns a list of `SelectionTarget` objects.

If `target/manifest.json` is absent, or its `mtime` is older than `dbt_project.yml`,
`selector.py` runs `dbtRunner.invoke(["parse"])` automatically before resolution
(no SQL executed, fast).

```python
@dataclass
class SelectionTarget:
    prefix: Literal["source", "model"]
    table: str              # unqualified relation name from manifest "name" field,
                            # e.g. "stg_parks__facilities" or "transactions"
                            # used as display title and output filename component
    connector_type: Literal["duckdb", "bigquery"]
    conn_str: str           # resolved .duckdb path or BQ project.dataset
    schema: str
    resource_type: str      # "source" | "model"
```

**Supported selectors (v1):**

| Selector | Example | Notes |
|---|---|---|
| Source ref | `source:reservations.transactions` | Resolves via manifest sources dict |
| Bare model name | `stg_parks__facilities` | Resolves via manifest nodes dict |
| Glob | `stg_*` | dbt ls resolves; all matching nodes profiled sequentially |

Complex graph selectors (`+model`, `tag:`, `path:`) are deferred to v2.

---

## Connectors

`BaseConnector` defines two methods implemented by both backends:

```python
class BaseConnector(ABC):
    @abstractmethod
    def get_schema(self) -> list[ColumnDef]: ...

    @abstractmethod
    def get_sample(self, n_rows: int) -> pd.DataFrame: ...
```

`ColumnDef` carries `name`, `source_type`, and `nullable`.

Both connectors return a `pd.DataFrame` directly:
- **DuckDB**: `con.execute("SELECT * FROM <table> LIMIT <n>").df()` — the DuckDB
  Python client returns pandas natively.
- **BigQuery**: `client.query("SELECT * FROM <table> LIMIT <n>").to_dataframe()`.

The `pd.DataFrame` is passed directly to `ProfileReport`. No intermediate polars
conversion layer is required for v1. If file-scanning performance becomes a concern
in future (e.g. profiling large Parquet exports), a polars-backed connector can be
added without changing the `BaseConnector` interface.

---

## Analyzers

### stats.py

Orchestrates ydata-profiling as the statistical engine:

```python
profile = ProfileReport(df, minimal=True, title=target.table)
description = profile.get_description()
```

`minimal=True` computes: null counts and percentages, cardinality, min/max/mean/std,
histogram data, duplicate rows, and alerts (`CONSTANT`, `HIGH_NULLS`,
`HIGH_CARDINALITY`, `DUPLICATES`, `SKEWED`, `ZEROS`). Skips correlation matrices and
interaction plots unless `--full-profile` is passed.

`AnalysisResult` is populated from the `description` object and the raw `profile`
object (retained for the HTML renderer).

### pii.py

Two-pass detection:

1. **Name-heuristic pass:** immediately flags columns matching known PII name patterns
   (`email`, `ssn`, `phone`, `dob`, `first_name`, `last_name`, `address`,
   `ip_address`, etc.)
2. **Value-scan pass:** runs `presidio-analyzer` over up to 100 sampled string values
   per non-flagged column — catches obfuscated column names

Returns `set[str]` of flagged column names. Detection only — anonymization is
`sanitizer.py`'s responsibility.

**Setup requirement:** `presidio-analyzer` requires a spaCy language model.
After installing requirements, run:

```bash
python -m spacy download en_core_web_lg
```

If the model is absent, `pii.py` falls back to name-heuristic detection only and
emits a warning. Profiling continues.

### dbt_signals.py

Reads `AnalysisResult` and emits `DbtSignal` objects. No statistical computation —
pure interpretation of the description and alert data:

| Signal type | Trigger |
|---|---|
| `CAST_HINT` | VARCHAR column with ydata-profiling type inferred as numeric or date |
| `RENAME_HINT` | camelCase, Hungarian notation, or ambiguous names (`id`, `code`, `flag`) |
| `UNUSED_COLUMN` | `CONSTANT` or `HIGH_NULLS` alert from ydata-profiling |
| `NULL_PATTERN` | High-null column correlated with another column's distinct values |

`FAN_OUT_RISK` detection is deferred to v2 — it requires cross-node analysis
(querying both a model and its upstream source), which is outside the single-node
scope of `AnalysisResult`.

```python
@dataclass
class DbtSignal:
    signal_type: Literal["CAST_HINT", "RENAME_HINT", "UNUSED_COLUMN", "NULL_PATTERN"]
    column_name: str
    message: str        # human-readable, e.g. "cast(amount as decimal(10,2))"
```

### sanitizer.py

Called by renderers that require redaction, not as a shared pipeline stage.
Runs `presidio-anonymizer` over the sample `pd.DataFrame`, replacing values in
PII-flagged columns with `[REDACTED:<entity_type>]`
(e.g. `[REDACTED:EMAIL_ADDRESS]`). Returns a new `pd.DataFrame` with redacted
values — the original `AnalysisResult.sample` is never mutated.

---

## AnalysisResult

```python
@dataclass
class AnalysisResult:
    target: SelectionTarget
    profile: ProfileReport          # full ydata-profiling object (HTML renderer)
    description: BaseDescription    # profile.get_description() (markdown + signals)
    sample: pd.DataFrame            # raw sample (never mutated)
    pii_columns: set[str]
    dbt_signals: list[DbtSignal]
    profiled_at: datetime
```

`sanitized_sample` is not stored on `AnalysisResult`. The markdown renderer calls
`sanitizer.sanitize(result.sample, result.pii_columns)` inline when building the
sample rows section. This keeps `AnalysisResult` as a pure analysis artifact and
avoids running Presidio anonymization when only terminal output is requested.

---

## Renderers

### terminal.py

```
skimpy.skim(df)                            → compact per-column stats table
rich.Panel(dbt_signals, title="Signals")   → casting hints, rename hints, debt flags
rich.Panel(pii_columns, title="PII")       → flagged column names in yellow
```

PII-flagged columns are highlighted but not redacted. Terminal is a local surface.

**Windows / Git Bash note:** prefix invocation with `PYTHONUTF8=1` to avoid
`cp1252` encoding errors on skimpy's rich console output (consistent with
`check_model.py` convention):

```bash
PYTHONUTF8=1 python scripts/profiler/cli.py --select stg_parks__facilities
```

### markdown.py

Produces a structured `.md` file optimized for LLM prompts. Calls
`sanitizer.sanitize()` to produce redacted sample rows inline. Sections in order:

1. **Header** — source name, profiled timestamp, row count vs sample size
2. **DDL (inferred)** — `CREATE TABLE` with source types, PK candidate comments,
   cast hint inline comments
3. **Column statistics table** — column, type, null %, n_distinct, ydata alerts
4. **dbt Signals** — casting hints, rename hints, unused columns as a bulleted list
5. **PII Columns** — flagged column names and detected entity types
6. **Sample Rows** — 5 rows with PII columns showing `[REDACTED:<entity_type>]`

Output path: `tmp/profile_<table>_<timestamp>.md`

### html.py

Uses `profile.to_html()` to render the report to a string buffer, prepends a
custom signals and PII section as an HTML string, then writes the combined output
to file:

```python
report_html = profile.to_html()   # complete HTML document string
signals_html = _render_signals_section(result.dbt_signals, result.pii_columns)
# Inject signals <div> immediately after <body> opening tag
combined = report_html.replace("<body>", "<body>" + signals_html, 1)
output_path.write_text(combined, encoding="utf-8")
```

This approach avoids dependency on ydata-profiling's internal config API and is
robust across minor version changes. The signals section is a self-contained
`<div>` injected as the first child of `<body>` — not prepended before `<html>`,
which would produce malformed output.

When `--sanitize-html` is passed, `html.py` calls `sanitizer.sanitize()` to
produce a redacted frame, then constructs a **second** `ProfileReport` from that
frame before rendering. `AnalysisResult.profile` (built from the unredacted frame)
is not reused in this case. This is intentionally more expensive than the default
path and is expected to be used only for LLM-safe sharing, not routine use.

Output path: `tmp/profile_<table>_<timestamp>.html`

---

## Error Handling

- Connector and selector errors fail immediately with an actionable message before
  profiling begins
- Renderer failures are isolated — HTML failure does not abort terminal or markdown
- Optional dependencies (`google-cloud-bigquery`, `presidio-analyzer`, `ydata-profiling`)
  imported lazily; absent packages produce a named error with the `pip install` command
- PII scan failure degrades gracefully — profiling continues with a warning that PII
  detection was skipped
- `--verbose` flag exposes full tracebacks; default shows clean user-facing messages

---

## Testing

Tests live in `tests/profiler/` mirroring the package structure.

| Layer | Strategy |
|---|---|
| `selector.py` | Unit tests with fixture manifest — assert correct `SelectionTarget` per selector |
| `connectors/` | Integration tests against fixture `.duckdb` from `source_data/duckdb/` |
| `analyzers/pii.py` | Unit tests with synthetic PII strings — assert correct column flagging |
| `analyzers/dbt_signals.py` | Unit tests with fixture `BaseDescription` dicts — assert correct signals |
| `renderers/markdown.py` | Snapshot tests — rendered output matches expected `.md` fixture |
| `renderers/terminal.py` | Smoke tests — no exception, skimpy output non-empty |
| `renderers/html.py` | Smoke tests — `.html` file created and non-empty |

---

## Dependencies

New additions to `requirements.txt`:

```
ydata-profiling>=4.6
skimpy>=0.0.12
presidio-analyzer>=2.2
presidio-anonymizer>=2.2
```

**Post-install step** (one-time, required for Presidio NLP detection):

```bash
python -m spacy download en_core_web_lg
```

`google-cloud-bigquery` remains an optional install (already removed from core
requirements per 2026-03-06 cleanup).

---

## Output File Conventions

All generated artifacts written to `tmp/` per project operating principles:

```
tmp/profile_stg_parks__facilities_20260315_143022.md
tmp/profile_stg_parks__facilities_20260315_143022.html
```

`tmp/` is gitignored. No artifacts written to project root or `scripts/`.
