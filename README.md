# DCR Analytics — dbt Public Sector Example

This is an example project demonstrating how a state government agency — the Department of Conservation and Recreation (DCR) — might build a governed, tested, and documented analytical data platform using dbt and DuckDB. The project models 10 synthetic source systems spanning reservations, finance, asset management, law enforcement, human capital, biological surveys, and visitor counting; then transforms them through a three-layer dbt pipeline into business-ready marts.

The source data is entirely synthetic, generated with Python and [Mimesis](https://mimesis.name/) to simulate realistic data quality issues that public sector organizations encounter: stale crosswalks, regional coverage gaps, mixed identifier formats, and legacy system quirks. The governance toolchain — sqlfluff, dbt-score, and dbt-project-evaluator — enforces 103 project standards that map to [DAMA data quality dimensions](#data-quality-and-dama-dimensions), making this a practical reference for teams that need to balance compliance with usability.

## Quick Start

For the impatient:

```powershell
git clone https://github.com/<your-org>/dbt-dcr-analytics.git
cd dbt-dcr-analytics
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
dbt deps && dbt seed && dbt build
```

All 10 source databases are included. No external setup needed. See [Getting Started](#getting-started) for detailed instructions and [Running Tests](#running-tests) for CI automation.

## Architecture

DCR Analytics uses [dbt-duckdb](https://github.com/duckdb/dbt-duckdb) with DuckDB's `ATTACH` feature to query all 10 source databases as cross-database schemas from a single analytical warehouse — no data movement or ETL pipeline required.

```
┌──────────────────────────────────────────────────────────────┐
│                    target/dcr_analytics.duckdb                │
│                                                              │
│   ┌─────────────┐  ┌──────────────┐  ┌────────────────────┐ │
│   │  Staging     │  │ Integration  │  │  Marts             │ │
│   │  (views)     │→ │ (tables)     │→ │  (tables)          │ │
│   └─────────────┘  └──────────────┘  └────────────────────┘ │
│         ↑                                                    │
│   ATTACH aliases: vistareserve, geoparks, infratrak, ...     │
└──────────────────────────────────────────────────────────────┘
         ↑
   source_data/duckdb/*.duckdb  (10 files, one per system)
```

Each source `.duckdb` file is attached as a named schema in `profiles.yml`. Staging models read directly from these attached schemas as dbt sources, and the rest of the pipeline builds from there.

### Source Systems

| Code | Alias | Domain | Description |
|---|---|---|---|
| DCR-REV-01 | `vistareserve` | Reservations & POS | Primary reservation platform with customer profiles, inventory, and point-of-sale transactions |
| DCR-REV-02 | `legacyres` | Legacy reservations | Predecessor system with historical reservations and fee schedules |
| DCR-GEO-01 | `geoparks` | GIS / Parks master | Authoritative park boundaries, GIS features, and infrastructure mapping |
| DCR-FIN-01 | `stategov` | State General Ledger | Chart of accounts, journal entries, encumbrances, and vendor payments |
| DCR-FIN-02 | `granttrack` | Federal grants | Grant applications, award budgets, reimbursements, and compliance tracking |
| DCR-AST-01 | `infratrak` | Asset management | Enterprise asset management with condition assessments and work orders |
| DCR-LES-01 | `rangershield` | Law enforcement | CAD/RMS system for incidents, citations, dispatch, and officer activity (CJIS air-gapped) |
| DCR-NRM-01 | `biosurvey` | Biological surveys | Flora/fauna observations, water quality tests, and invasive species monitoring |
| DCR-HCM-01 | `peoplefirst` | Human capital | Employee records, positions, payroll, benefits, and leave balances |
| DCR-VUM-01 | `trafficcount` | Visitor counting | IoT sensor data for vehicle, pedestrian, and cyclist counts |

## dbt Layer Structure

The pipeline follows a three-layer architecture where each layer has distinct responsibilities, materialization strategies, and governance expectations.

### Staging

Staging models are **views** that rename, cast, and lightly clean columns from a single source table. They do not join, filter, aggregate, or apply business logic. Each staging subdirectory corresponds to one source system, and models follow the naming convention `stg_<source>__<table>`.

Staging is where source-specific column names become consistent types and formats. An integer `park_id` from VistaReserve becomes a `varchar`; a `TIMESTAMP` from InfraTrak becomes a properly cast `date`. No rows are added or removed.

Some sources also have a `base/` subdirectory for intermediate cleaning steps — deduplication or JSON extraction — that feed into the main staging model.

**What belongs here:** Column renaming, type casting, simple string trimming, boolean recoding from `VARCHAR` values like `'Y'`/`'N'`.

**What does not belong here:** Joins between tables, `WHERE` clauses that filter rows, aggregations, surrogate key generation, or business logic of any kind.

### Integration

Integration models are **tables** that combine data from multiple staging sources into entity-aligned datasets conforming to the [Microsoft Common Data Model](https://learn.microsoft.com/en-us/common-data-model/) (CDM). This is where cross-system joins, unions, deduplication, and surrogate key generation happen.

Each integration model maps to a CDM entity. The model name matches the entity name: `int_parks` maps to the Park entity, `int_financial_transactions` maps to FinancialTransaction, and so on. Surrogate keys are generated using `dbt_utils.generate_surrogate_key()` and named `<entity>_sk`. Foreign keys to other integration models are prefixed with an underscore (e.g., `_park_sk`, `_contact_sk`).

When the standard CDM catalog does not include all columns needed for DCR's domain, a CDM Exception document in `reference/CDM_EXCEPTION_*.md` formally records the deviation and the rationale.

**What belongs here:** Multi-source unions and joins, surrogate key generation, CDM column mapping, deduplication, source system tagging.

**What does not belong here:** Business logic, KPI calculations, or presentation-layer concerns. Integration models should also never be simple passthroughs of a single staging source — if a model only renames columns from one source, it is missing its purpose.

### Marts

Mart models are **tables** organized by business domain (revenue, finance, operations, attendance, core, reporting). They consume integration models and apply business logic: calculated fields, KPI aggregations, date spine joins, and domain-specific transformations.

Marts use a dimensional modeling pattern with `dim_` (dimensions), `fct_` (facts), and `rpt_` (report-level aggregates) prefixes. All mart models enforce [dbt contracts](https://docs.getdbt.com/docs/collaborate/govern/model-contracts) with explicit `data_type` declarations on every column, which guarantees that downstream consumers see a stable schema.

**What belongs here:** Business logic, calculated metrics, KPI definitions, dimensional conformance, report-level aggregations.

**What does not belong here:** Raw source references, staging-layer cleanup, or cross-system entity resolution (that belongs in integration).

## Getting Started

### Prerequisites

- [Python 3.10+](https://www.python.org/downloads/)
- [Git](https://git-scm.com/downloads)
- Windows 11 with PowerShell

### Setup

Clone the repository and create a Python virtual environment:

```powershell
git clone https://github.com/<your-org>/dbt-dcr-analytics.git
cd dbt-dcr-analytics

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Install dbt packages and load seed data:

```powershell
dbt deps
dbt seed
```

Build the full project:

```powershell
dbt build
```

The `profiles.yml` included in the repository points to a local DuckDB file at `target/dcr_analytics.duckdb` and attaches all 10 source databases from `source_data/duckdb/`. No external database server or credentials are needed.

### Verifying the Setup

After `dbt build` completes, confirm that models materialized and tests passed:

```powershell
dbt ls --resource-type model | Measure-Object -Line
dbt ls --resource-type test | Measure-Object -Line
```

You can also query the warehouse directly:

```powershell
dbt show --select int_parks --limit 5
```

### Running Tests

The project includes 745 data tests covering schema validation, nullness, uniqueness, referential integrity, and business rule enforcement. Run them with:

```powershell
dbt test
```

For automated CI-like testing with linting and governance scoring, use [nox](https://nox.thea.codes/):

```powershell
nox -s ci       # Run full CI pipeline: deps → seed → build → lint → score → check
nox -s lint     # Lint all SQL
nox -s score    # Run dbt-score governance validation
```

See `noxfile.py` for individual session definitions. You can also run sessions individually: `nox -s build`, `nox -s test`, etc.

### Exporting Data

To export all mart model data to CSV and Parquet files:

```powershell
python -m scripts.export --format both --select fct_reservations
```

Use `--format csv` or `--format parquet` for a single format, or omit `--select` to export all marts. Outputs go to the `output/` directory.

## AI-Assisted Development

This project includes configuration for AI-assisted code generation using [Claude Code](https://claude.com/claude-code) and [Gemini](https://gemini.google.com/app):

- **`.agent/`** — Shared governance rules and dbt skills (SSoT for both Claude and Gemini)
- **`.claude/`** — Claude Code agent definitions and local configuration
- **`.gemini/`** — Gemini CLI and Antigravity settings
- **`.ai/prompts/`** — System prompts for dbt-implementer and spec-planner agents

These directories are optional and do not affect local development. Remove them if you are not using an AI assistant. See [CLAUDE.md](CLAUDE.md) and [GEMINI.md](GEMINI.md) for agent-specific instructions.

## PowerShell Basics

This project uses PowerShell as its primary shell on Windows. If you are more familiar with Bash, cmd, or another terminal, the following tips cover the patterns that come up most often when working with dbt and Python on Windows.

### Running Commands

PowerShell commands work like most shells — type the command, press Enter. Chaining works with `;` (run sequentially regardless of success) or `&&` (run the next command only if the previous one succeeded, available in PowerShell 7+):

```powershell
dbt build --select int_parks; dbt-score lint --select int_parks
```

### Setting Environment Variables

Environment variables are set per-session using `$env:`. They do not persist after you close the terminal. The most common one in this project is `PYTHONUTF8`, which prevents encoding errors in console output:

```powershell
# Set for the current session
$env:PYTHONUTF8=1

# Set inline for a single command (semicolon separates the two statements)
$env:PYTHONUTF8=1; python -m scripts.reviewer --select int_parks
```

In Bash or Git Bash, the equivalent is `PYTHONUTF8=1 python -m scripts.reviewer --select int_parks` — the variable is prefixed directly to the command.

### Virtual Environment Activation

Python virtual environments are activated differently depending on the shell:

```powershell
# PowerShell
.\.venv\Scripts\Activate.ps1

# Git Bash
source .venv/Scripts/activate

# cmd
.venv\Scripts\activate.bat
```

If you see an error about execution policies when activating in PowerShell, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once to allow local scripts.

### Path Separators

PowerShell accepts both forward slashes (`/`) and backslashes (`\`) in file paths, so `models/staging/vistareserve` and `models\staging\vistareserve` both work. Most examples in this README use backslash-free paths for readability.

### Piping and Filtering Output

PowerShell's pipeline passes objects rather than text, which changes how filtering works compared to Bash. A few patterns that come up in this project:

```powershell
# Count lines of output (equivalent to wc -l in Bash)
dbt ls --resource-type model | Measure-Object -Line

# Filter output to lines containing a keyword (equivalent to grep)
dbt ls --resource-type model | Select-String "staging"

# View only the first N lines (equivalent to head)
dbt ls --resource-type model | Select-Object -First 10
```

### Navigating the Terminal

These patterns apply regardless of which shell you use — PowerShell, Git Bash, or the VS Code integrated terminal.

**Moving through text on the command line:**

| Action | Shortcut |
|---|---|
| Move cursor one word left | `Ctrl+Left Arrow` |
| Move cursor one word right | `Ctrl+Right Arrow` |
| Jump to the beginning of the line | `Home` |
| Jump to the end of the line | `End` |
| Delete the word before the cursor | `Ctrl+Backspace` |
| Delete the word after the cursor | `Ctrl+Delete` |

**Working with command history:**

| Action | Shortcut |
|---|---|
| Previous command | `Up Arrow` |
| Next command (after scrolling up) | `Down Arrow` |
| Search command history | `Ctrl+R`, then start typing |
| Accept the history search match | `Enter` or `Right Arrow` |
| Cancel history search | `Escape` |

History search is one of the most useful habits to build. If you ran a long `dbt build --select` command earlier in the session, pressing `Ctrl+R` and typing `build` will find it — no need to retype or scroll.

**Stopping and clearing:**

| Action | Shortcut |
|---|---|
| Cancel a running command | `Ctrl+C` |
| Clear the screen | `cls` (PowerShell) or `clear` (Bash) |
| Close the terminal | `exit` |

### Common Gotchas

- **Single vs. double quotes:** PowerShell interpolates variables inside double quotes (`"$variable"`) but not inside single quotes (`'$variable'`). When passing literal strings to dbt or Python, single quotes are safer.
- **Tab completion:** PowerShell supports tab completion for file paths, commands, and parameters. Press Tab to cycle through matches.
- **Long-running commands:** If `dbt build` is taking longer than expected, `Ctrl+C` cancels it cleanly. dbt will finish the current model before stopping.
- **Copy and paste in the terminal:** In the VS Code integrated terminal, `Ctrl+C` copies selected text when text is highlighted, and sends an interrupt signal when nothing is selected. `Ctrl+V` pastes. In standalone PowerShell windows, right-click pastes by default.

## VS Code for This Project

VS Code is the recommended editor for this project, and a few of its features are worth knowing even if you primarily work in another editor. The shortcuts below assume the default Windows keybindings.

### Opening and Navigating Files

| Action | Shortcut | Notes |
|---|---|---|
| Open a file by name | `Ctrl+P` | Type a partial filename — `int_parks` finds `int_parks.sql` and its YAML |
| Switch between open tabs | `Ctrl+Tab` | Hold Ctrl and press Tab repeatedly to cycle |
| Close the current tab | `Ctrl+W` | |
| Reopen a recently closed tab | `Ctrl+Shift+T` | |
| Go to a specific line number | `Ctrl+G` | Useful when a test failure or linter reports a line number |
| Open the file explorer sidebar | `Ctrl+Shift+E` | |

`Ctrl+P` is the single most efficient way to open files in this project. Typing `stg_vista` narrows to all VistaReserve staging models; typing `_models.yml` narrows to all YAML property files. You can also type `:` after the filename to jump to a specific line — `int_parks.sql:15` opens the file at line 15.

### Searching Across the Project

| Action | Shortcut | Notes |
|---|---|---|
| Search in the current file | `Ctrl+F` | |
| Search and replace in the current file | `Ctrl+H` | |
| Search across all files | `Ctrl+Shift+F` | The most useful search in a dbt project |
| Search by symbol (function, model name) | `Ctrl+Shift+O` | In SQL files, this finds CTE names |

When searching across all files (`Ctrl+Shift+F`), use the "files to include" field to scope the search. For example, entering `models/integration` in that field limits results to integration models. This is helpful when searching for a column name that appears in many layers — you often want to see where it is defined in integration, not every staging model that sources it.

### Working with the Terminal

| Action | Shortcut | Notes |
|---|---|---|
| Toggle the integrated terminal | `` Ctrl+` `` | Opens or focuses the terminal panel |
| Create a new terminal instance | `` Ctrl+Shift+` `` | Useful for running dbt in one terminal and linting in another |
| Switch between terminal instances | `Ctrl+Page Up` / `Ctrl+Page Down` | When you have multiple terminals open |
| Split the terminal | `Ctrl+Shift+5` | Side-by-side terminals in the same panel |
| Maximize/restore the terminal panel | Double-click the panel title bar | Gives more room for long dbt output |

A common workflow is to keep two terminals open: one for `dbt build` and `dbt show` commands, and another for linting and governance checks. This avoids the need to scroll back through output to find a previous command's results.

### Editing

| Action | Shortcut | Notes |
|---|---|---|
| Move a line up or down | `Alt+Up` / `Alt+Down` | Reorder SQL columns or CTE clauses without cut-and-paste |
| Duplicate a line | `Shift+Alt+Down` | Useful when adding similar column definitions in YAML |
| Delete a line | `Ctrl+Shift+K` | |
| Toggle line comment | `Ctrl+/` | Comments or uncomments the selected lines |
| Select the next occurrence of the current word | `Ctrl+D` | Builds a multi-cursor selection — rename a column alias in several places at once |
| Select all occurrences of the current word | `Ctrl+Shift+L` | |
| Undo | `Ctrl+Z` | |
| Redo | `Ctrl+Y` or `Ctrl+Shift+Z` | |
| Indent / outdent selected lines | `Tab` / `Shift+Tab` | |

`Ctrl+D` deserves special mention. If you need to rename a CTE alias or column name that appears multiple times in a SQL file, place your cursor on the word and press `Ctrl+D` repeatedly — each press selects the next occurrence and creates an additional cursor. Then type the new name once, and all occurrences update simultaneously. `Ctrl+Shift+L` does the same thing but selects every occurrence in the file at once.

### Side-by-Side Editing

When writing or reviewing dbt models, it is often helpful to see a model's SQL and its YAML properties file at the same time. To open a file in a split view:

1. Open the SQL file (e.g., `int_parks.sql`) with `Ctrl+P`.
2. Open the YAML file (e.g., `_models.yml`) with `Ctrl+P`.
3. Drag the YAML tab to the right side of the editor, or right-click the tab and select "Split Right."

This layout makes it straightforward to verify that every column in the SQL's final `SELECT` appears in the YAML's `columns:` list — a check that prevents contract mismatches at build time.

## Common dbt Commands

### Everyday Commands

```powershell
# Build everything: run models + run tests in dependency order
dbt build

# Run only models (skip tests)
dbt run

# Run only tests
dbt test

# Build a specific model and its tests
dbt build --select int_parks

# Preview model output without materializing
dbt show --select int_parks --limit 10

# Compile SQL without executing (useful for reviewing generated SQL)
dbt compile --select fct_reservations
```

### Selection Syntax

dbt's [node selection](https://docs.getdbt.com/reference/node-selection/syntax) is one of its most useful features, and newer users often underuse it:

```powershell
# Build one model and everything downstream of it
dbt build --select int_parks+

# Build one model and everything upstream of it
dbt build --select +fct_reservations

# Build a model with both upstream and downstream
dbt build --select +int_parks+

# Build all models in a directory
dbt build --select models/staging/vistareserve

# Build all models with a specific tag
dbt build --select tag:revenue

# Exclude specific models from a run
dbt build --exclude fct_pos_transactions

# Build only models that have changed since the last run (state comparison)
dbt build --select state:modified --defer --state target/
```

### Inspecting and Debugging

```powershell
# List all models in the project
dbt ls --resource-type model

# List models in a specific layer
dbt ls --select models/integration

# Show the compiled SQL for a model (helpful for debugging Jinja)
dbt compile --select fct_reservations
# Then inspect: target/compiled/dcr_analytics/models/.../fct_reservations.sql

# Preview upstream model output before writing downstream SQL
dbt show --select int_contacts --limit 1

# Generate and serve the documentation site
dbt docs generate
dbt docs serve
```

### Seed and Source Commands

```powershell
# Load all seed CSVs into the warehouse
dbt seed

# Load a specific seed
dbt seed --select source_system_registry

# Check source freshness (where configured)
dbt source freshness
```

### Tips for Newer Users

- **Use `dbt build` instead of `dbt run` followed by `dbt test`.** `dbt build` runs models and their tests in dependency order, so a failing test on an upstream model prevents downstream models from running on bad data.
- **Use `dbt show` before writing downstream models.** Running `dbt show --select <upstream_model> --limit 1` lets you see the actual column names and sample data. This prevents mismatches between what you think a model produces and what it actually produces.
- **Use `dbt compile` to debug Jinja.** If a model with macros or `ref()` calls is not behaving as expected, `dbt compile` writes the fully rendered SQL to `target/compiled/`. Read that file to see exactly what SQL dbt will execute.
- **Use `--select` with directory paths for batch operations.** Running `dbt build --select models/staging/vistareserve` is often more practical than listing individual model names.
- **Explore `dbt ls` for discovery.** `dbt ls --resource-type source` lists all declared sources; `dbt ls --select +fct_reservations` shows the full upstream lineage of a model.
- **The `+` operator is directional.** A plus sign *before* the model name (`+model`) means upstream dependencies. A plus sign *after* (`model+`) means downstream dependents. Both (`+model+`) means the full lineage in both directions.

## Scripts and Tools

The `scripts/` directory contains Python utilities that support development, governance, and data discovery. Activate the virtual environment before running any script.

### scripts.reviewer — Automated Governance Gate

The primary quality gate. Runs sqlfluff, dbt build, dbt-score, dbt-project-evaluator, and a suite of custom static analysis checks against one or more models.

```powershell
$env:PYTHONUTF8=1; python -m scripts.reviewer --select int_parks
$env:PYTHONUTF8=1; python -m scripts.reviewer --select models/integration
$env:PYTHONUTF8=1; python -m scripts.reviewer --branch feature/my-branch
```

The `PYTHONUTF8=1` environment variable is needed on Windows to prevent encoding errors in the rich console output.

What it checks:
- **sqlfluff lint** — formatting compliance (zero violations required)
- **dbt build** — model compilation and schema test passage
- **dbt-score** — documentation quality scoring (minimum 5.0)
- **dbt-project-evaluator** — DAG structure and naming convention rules
- **Manifest analysis** — YAML/SQL column alignment, CTE structure, layer-specific rules
- **CDM conformance** — column mapping to Common Data Model entity catalogs

### scripts.reviewer.qualitative — Qualitative Review

Evaluates the standards that automated linters cannot check: meaningful names, description quality, and business rule design. Operates in two modes.

```powershell
# Generate a review checklist for an AI agent or manual review
python -m scripts.reviewer.qualitative --select int_parks --agent

# Export structured YAML review files for batch processing
python -m scripts.reviewer.qualitative --select models/integration --export-yaml

# Interactive CLI review (prompts you step-by-step)
python -m scripts.reviewer.qualitative --select int_parks
```

#### Sending a Review to Gemini via the Clipboard

After generating an agent checklist, you can pipe the file directly into the Windows clipboard and paste it into [Gemini](https://gemini.google.com/app) in Chrome for a qualitative peer review. This is useful when you want a second opinion on description quality, business rule design, or CDM mapping decisions that automated tools cannot evaluate.

```powershell
python -m scripts.reviewer.qualitative --select int_parks --agent; Get-Content tmp/review_int_parks.md | Set-Clipboard
```

The script writes its checklist to `tmp/review_<model>.md`, and `Set-Clipboard` loads the file into the clipboard. Open Chrome, navigate to [gemini.google.com/app](https://gemini.google.com/app), and paste with `Ctrl+V`.

For batch reviews, use `--export-yaml` and copy each model file individually:

```powershell
python -m scripts.reviewer.qualitative --select models/integration --export-yaml; Get-Content tmp/reviews/int_financial_transactions.yaml | Set-Clipboard
```

In Gemini, a useful prompt framing is: *"You are reviewing a dbt integration model against the DCR Analytics project standards. Here is the review checklist — please evaluate each item and flag any FAIL or NEEDS-ATTENTION findings with your reasoning."* Paste the checklist content immediately after the prompt.

### scripts.inspect — Source Data Discovery

Profiles a source table before writing staging models. Reports row counts, column schemas, uniqueness and cardinality analysis, null distributions, date ranges, and sample rows.

```powershell
# List all tables in a source database
python -m scripts.inspect --type duckdb --conn source_data/duckdb/dcr_rev_01_vistareserve.duckdb

# Profile a specific table
python -m scripts.inspect --type duckdb --conn source_data/duckdb/dcr_rev_01_vistareserve.duckdb --table main.reservations
```

### scripts.profiler — Source and Model Profiling

A statistical profiler for dbt sources and models. Unlike `scripts.inspect`, the profiler uses dbt's selector syntax so you can profile any node the same way you reference it in `dbt build` — no need to know the underlying file path or schema name. By default it runs a fast warehouse-side SQL query to produce per-column statistics with no large data transfer. Pass `--full-profile` to enable ydata-profiling with correlations and distributions.

```powershell
# Profile a staging model — terminal output (default)
$env:PYTHONUTF8=1; python -m scripts.profiler.cli --select stg_geoparks__parks_master

# Profile a staging model and write a Markdown report
$env:PYTHONUTF8=1; python -m scripts.profiler.cli --select stg_vistareserve__reservations --output markdown

# Profile a mart model with all output formats and a larger sample
$env:PYTHONUTF8=1; python -m scripts.profiler.cli --select fct_reservations --output all --sample 5000

# Generate an HTML report with PII redacted in sample rows (for LLM-safe sharing)
$env:PYTHONUTF8=1; python -m scripts.profiler.cli --select int_employees --output html --sanitize-pii
```

Run the profiler as a module (`python -m scripts.profiler.cli`) from the project root — this ensures the `scripts` package is importable. The `PYTHONUTF8=1` prefix is required on Windows to prevent encoding errors in the rich console output. In Git Bash use `PYTHONUTF8=1 python -m scripts.profiler.cli ...` instead.

#### Output modes

| Mode | Output | Description |
|---|---|---|
| `terminal` | Console | Per-column stats (null rate, distinct count, min/max/avg, top values) with candidate key and PII panels |
| `markdown` | `tmp/profile_<model>.md` | Full statistics in Markdown, suitable for committing or pasting into a review |
| `html` | `tmp/profile_<model>.html` | Interactive HTML report with distributions, correlations, and sample rows (requires `--full-profile`) |
| `llm` | Console | Structured context block formatted for pasting into an LLM |
| `all` | All four | Equivalent to `--output terminal,markdown,html,llm` |

#### Options

| Flag | Default | Description |
|---|---|---|
| `--select` / `-s` | required | dbt node selector — model name, `source:<src>.<table>`, or any valid dbt selector |
| `--output` / `-o` | `terminal` | Comma-separated output modes (see table above) |
| `--sample N` | `1000` | Number of rows to sample |
| `--full-profile` | off | Enable ydata-profiling correlations and interactions (slower) |
| `--env` | `local` | `local` for DuckDB, `prod` for BigQuery |
| `--sanitize-pii` | off | Redact PII values in output (markdown and HTML); for LLM-safe sharing |
| `--verbose` | off | Show full tracebacks on error |

#### dbt Signals

The profiler emits four signal types that surface potential staging issues:

| Signal | What it means |
|---|---|
| `CAST_HINT` | A VARCHAR column appears to contain numeric or date values — consider casting in staging |
| `RENAME_HINT` | A column uses camelCase, Hungarian notation, or an ambiguous generic name |
| `UNUSED_COLUMN` | A column has a constant value or very high null rate — consider dropping in staging |
| `NULL_PATTERN` | A column shows a null distribution pattern worth documenting |

#### PII Detection

PII detection runs in two passes. Pass 1 flags columns whose names match known patterns (`email`, `ssn`, `phone`, `first_name`, `address`, etc.). Pass 2 uses [Presidio](https://microsoft.github.io/presidio/) to scan sample values in any unflagged string columns. If `presidio-analyzer` or the `en_core_web_lg` spaCy model is not installed, the profiler falls back gracefully to name-heuristic detection only. In terminal mode, PII columns are highlighted but not redacted. Use `--sanitize-pii` when generating markdown or HTML output intended for sharing with LLMs or external reviewers.

#### Prerequisites

The profiler requires a compiled manifest (`target/manifest.json`). If the manifest is absent or older than `dbt_project.yml`, the profiler runs `dbt parse` automatically. Markdown and HTML output require `ydata-profiling`; terminal output uses `skimpy`. Both are included in `requirements.txt`. Full PII value scanning additionally requires:

```powershell
pip install "presidio-analyzer>=2.2"
python -m spacy download en_core_web_lg
```

### scripts.cdm — CDM Catalog Search

Searches the full Microsoft Common Data Model column catalog using keyword and fuzzy matching. Useful when mapping staging columns to CDM entity attributes.

```powershell
# Search for columns related to a concept
python -m scripts.cdm reservation status

# Require all keywords to match
python -m scripts.cdm park name --all

# Filter to a specific CDM entity
python -m scripts.cdm amount --entity FinancialTransaction
```

### scripts.reviewer summarize — Review Aggregator

Aggregates review YAML files (from `scripts.reviewer.qualitative --export-yaml`) into a single Markdown summary report showing failure trends and rule-by-rule breakdowns.

```powershell
python -m scripts.reviewer summarize --input tmp/reviews
```

### scripts.governance.parse_standards — Standards JSON Builder

Parses the 103 governance rules from `reference/dbt_project_standards.md` into a structured JSON file used by the review scripts. Run this if the standards document changes.

```powershell
python -m scripts.governance.parse_standards
```

## Linting and Governance

The project enforces code quality through three complementary tools, each covering a different surface area.

### sqlfluff — SQL Formatting

[sqlfluff](https://sqlfluff.com/) enforces consistent SQL formatting: lowercase keywords, line length limits, indentation, and alias conventions. Configuration lives in `.sqlfluff` at the project root.

```powershell
# Lint a specific directory
sqlfluff lint models/staging/vistareserve

# Lint a specific file
sqlfluff lint models/integration/int_parks.sql

# Auto-fix formatting violations
sqlfluff fix models/staging/vistareserve
```

Key configuration choices:
- **Dialect:** DuckDB
- **Templater:** dbt (so Jinja `{{ ref() }}` and `{{ source() }}` resolve correctly)
- **Max line length:** 120 characters
- **Keyword casing:** lowercase

When linting as part of a phase gate, scope the lint to the layer under review — not the full `models/` directory. Running `sqlfluff lint models/` during a staging review will surface violations in integration and mart models that are not part of the current scope.

### dbt-score — Documentation Quality

[dbt-score](https://dbt-score.readthedocs.io/) evaluates documentation completeness and quality. Every model must score at least **5.0** (out of 10) to pass. Configuration lives in `pyproject.toml`.

```powershell
# Score all models
dbt-score lint

# Score specific models (uses dbt selection syntax)
dbt-score lint --select models/integration
```

The scoring rules include four project-specific rules defined in `scripts/governance/dbt_score_rules.py`:

| Rule | What It Checks |
|---|---|
| `no_test_rationale_in_description` | Descriptions must not contain test-justification language ("unique", "not_null", "fan-out", etc.) |
| `mart_contract_enforced` | `fct_` and `dim_` models must have `contract: { enforced: true }` |
| `mart_columns_have_data_type` | All columns in mart models must declare a `data_type` |
| `no_per_model_yaml` | Models must not use a YAML file named `<model_name>.yml`; use `_models.yml` instead |

### dbt-project-evaluator — DAG Structure

[dbt-project-evaluator](https://github.com/dbt-labs/dbt-project-evaluator) validates the project DAG: naming conventions, directory placement, dependency direction, and structural patterns. It runs as part of `dbt build` via three custom fact models in `models/project_evaluator/`.

The project also maintains a `seeds/dbt_project_evaluator_exceptions.csv` for documented, intentional deviations from the evaluator's default rules.

### scripts.reviewer — All Three Combined

In practice, you rarely need to run these tools individually. `scripts.reviewer` orchestrates all three — plus additional static analysis — into a single pass:

```powershell
$env:PYTHONUTF8=1; python -m scripts.reviewer --select int_parks
```

## Data Quality and DAMA Dimensions

This project uses the [DAMA Data Management Body of Knowledge](https://www.dama.org/cpages/body-of-knowledge) (DMBOK) framework to organize data quality practices. The six DAMA data quality dimensions provide a shared vocabulary for what "quality" means at each layer of the pipeline, and the project's 103 governance standards trace directly to these dimensions.

### The Six Dimensions

**Completeness** — Are all expected records and fields present? A customer record missing a name, or a union that silently drops rows from one source, are completeness failures.

**Uniqueness** — Is each entity represented exactly once at the expected grain? Duplicate surrogate keys in an integration model or a mart fact table with fan-out from a bad join are uniqueness failures.

**Validity** — Do values fall within expected ranges and formats? A latitude of 999.0, a reservation status of "XYZZY", or a negative occupancy count are validity failures.

**Consistency** — Do related fields and cross-system records agree? A park that exists in VistaReserve but not in GeoParks, or a reservation whose departure date precedes its arrival date, are consistency failures.

**Accuracy** — Does the data reflect real-world truth? A revenue summary that does not reconcile with its underlying transactions, or a KPI calculation that uses the wrong formula, are accuracy failures.

**Timeliness** — Is the data current enough for its intended use? Source tables that have not been refreshed within expected windows, or crosswalk tables with stale mappings, are timeliness failures.

### How Dimensions Map to dbt Tests

Each dimension translates into specific dbt testing patterns. The project standards encode these mappings directly — each rule's name includes the DAMA dimension(s) it targets.

| Dimension | dbt Testing Patterns | Example |
|---|---|---|
| Completeness | `not_null` tests on critical columns, `expect_table_row_count_to_be_between` on union models, `not_null` with `severity: warn` and `mostly` thresholds on nullable fields | Every integration model's surrogate key is tested `not_null` |
| Uniqueness | `unique` tests on primary keys, `dbt_utils.unique_combination_of_columns` for composite keys | `unique` on `park_sk` in `int_parks` |
| Validity | `accepted_values` for enumerated fields, `dbt_expectations.expect_column_values_to_be_between` for numeric ranges, regex tests for format validation | GPS coordinates bounded to ±90 latitude, ±180 longitude |
| Consistency | `relationships` tests for foreign key integrity, singular reconciliation tests, date ordering tests | `assert_revenue_sums_balance.sql` verifies mart aggregates match fact-level sums |
| Accuracy | [dbt unit tests](https://docs.getdbt.com/docs/build/unit-tests) on business logic, singular reconciliation tests | Unit tests on KPI calculations in mart models |
| Timeliness | `dbt source freshness` with `warn_after` / `error_after` thresholds, staleness bounds on crosswalk update timestamps | VistaReserve sources have freshness checks; TrafficCount sources have demo-appropriate thresholds |

### What the Pipeline Can and Cannot Control

A dbt pipeline can enforce structure, test assertions, and surface problems — but it cannot fix data that was never captured correctly at the point of entry. This distinction matters because many of the quality risks in a public sector data environment originate upstream, in how source systems are configured, how consistently they are used, and whether the people entering data have feedback on what happens when a field is left blank or a value is entered outside its expected range.

Some source systems impose strong constraints at the point of entry — required fields, picklist validation, referential integrity checks — and the data that arrives in the pipeline reflects that discipline. Other systems, particularly those designed to minimize friction for field staff or seasonal workers, accept nearly any input and rely on downstream review that may or may not happen. Legacy systems often have constraints that were appropriate when they were built but have not evolved with the data they now carry; newer pilot systems may not yet have governance controls in place because the priority was deployment speed over data discipline.

What this means for analysts working in this project: the tests and contracts you see in the dbt layer are the last line of defense, not the first. They tell you where quality is being measured and where it is not. A passing test suite does not mean the data is accurate in an absolute sense — it means the data meets the assertions that have been written so far. A `not_null` test on a customer name column confirms that the field is populated, but it cannot confirm that the name is spelled correctly or belongs to the right person. An `accepted_values` test on a status field confirms that every value falls within a known set, but it cannot confirm that the status was updated at the right time by the right person in the source system.

The sections below describe what each layer of the pipeline contributes to quality enforcement, and — just as importantly — what each layer depends on but cannot verify.

### How Each Layer Contributes

Quality enforcement is cumulative. Each layer adds dimension coverage that the previous layer cannot provide, and each layer inherits assumptions about the data it receives.

#### Sources

**What this layer does:** Timeliness checks via `dbt source freshness`. This is the only layer where freshness can be evaluated, because staging models are views that reflect source state at query time. Source YAML declarations also document the expected schema, owner, and loader for each table — making it possible to trace a column back to its origin system and the team responsible for it.

**What this layer depends on:** Source systems delivering data on their expected schedule, with the schema they have documented. When a source system changes a column name, adds a field, or stops populating a table, the pipeline will surface the break — but the root cause is upstream. Analysts should treat source freshness failures as signals to investigate whether a system load failed, a vendor changed an API, or a batch process was delayed, rather than assuming the pipeline itself is broken.

**What this layer cannot verify:** Whether the data in the source tables is accurate, complete, or consistently entered. A source table can be perfectly fresh and structurally intact while containing records that were entered incorrectly, entered late, or never entered at all. Systems that do not enforce required fields at the point of entry — like the GrantTrack Excel workbook or BioSurvey's Access database — can deliver structurally valid rows where critical fields are blank or contain placeholder values.

#### Staging

**What this layer does:** Establishes uniqueness and basic validity. Every staging model tests `unique` and `not_null` on the natural key, which confirms that rows from the source are not duplicated and that the identifier the source system assigns is always present. Type casting in the SQL — converting a `VARCHAR` date to a proper `DATE`, or an integer ID to a `VARCHAR` for consistent joining — catches malformed values that would otherwise propagate silently. If a value cannot be cast, the model fails, and the failure points directly to the problematic source record.

**What this layer depends on:** Source systems assigning meaningful, stable natural keys. Most enterprise systems (VistaReserve, InfraTrak, PeopleFirst) handle this well. Legacy systems and spreadsheet-based workflows are less predictable — LegacyRes uses format-era-dependent IDs, and GrantTrack's row identity depends on a combination of columns that may not be unique if an analyst accidentally duplicates a row in the workbook.

**What this layer cannot verify:** Whether a record that exists in the source should exist, or whether a record that should exist is missing. Staging tests confirm structural integrity — "every row has a key, and no key is repeated" — but they do not know whether 100 reservations is the right number for a given day, or whether a missing work order means the work was not done or the work order was never created. Analysts writing staging tests should focus on protecting downstream models from structural corruption, and should use `severity: warn` for fields where blanks are a known characteristic of the source system rather than a sign of breakage.

#### Integration

**What this layer does:** Uniqueness on surrogate keys, completeness via row count guards on union models, consistency via relationship tests between integration entities, and validity via CDM `accepted_values` on enumerated fields. Integration is where cross-system problems become visible — a park that exists in one source but not another, an asset whose identifier format does not match the crosswalk, or a union of two sources that produces fewer rows than expected.

Row count bounds (`expect_table_row_count_to_be_between`) on union models serve a specific purpose: if a source feed fails silently and delivers zero rows, the union still succeeds but the row count drops. The bounds catch this. They should be set wide enough to accommodate normal variation but narrow enough to catch a missing source.

**What this layer depends on:** Crosswalk tables and shared identifiers being maintained. The VistaReserve-to-GeoParks asset crosswalk, for example, has not been updated since 2022 — meaning that assets registered in either system after that date cannot be matched at the record level. Integration models that join across systems are only as current as the least-maintained crosswalk they depend on. Relationship tests between integration entities (`relationships` tests on foreign keys like `_park_sk` or `_contact_sk`) confirm that a foreign key value exists in the referenced model, but they cannot confirm that the match is semantically correct if the crosswalk that produced the key is stale.

**What this layer cannot verify:** Whether the business meaning of a field is consistent across the sources being combined. Two systems may both have a `status` column with a value of "Active," but "Active" in VistaReserve means a reservation is currently checked in, while "Active" in InfraTrak means an asset is in service. CDM column mapping standardizes the names; it does not standardize the semantics unless the integration SQL explicitly recodes the values. Analysts writing integration models should document these semantic differences in the model's YAML description and, where the SPEC calls for it, apply `case` expressions that normalize values into a shared domain.

#### Marts

**What this layer does:** All six dimensions converge. Contracts enforce structural consistency — every mart model declares its columns and data types, and a mismatch between the SQL output and the contract fails the build. Unit tests verify accuracy of business logic by asserting that known inputs produce expected outputs. Relationship tests confirm dimensional integrity — every foreign key in a fact table points to a real row in its dimension. Reconciliation tests (singular SQL tests in `tests/marts/`) validate that aggregated metrics balance against their underlying facts.

**What this layer depends on:** Integration models delivering semantically clean, correctly keyed data. A mart model that calculates revenue per park trusts that `_park_sk` in the fact table correctly identifies the park, that the revenue amount was correctly converted from the source system's format, and that no duplicate transactions inflated the total. If any of those assumptions are wrong, the mart will produce a structurally valid, contract-compliant result that is nonetheless incorrect.

**What this layer cannot verify:** Whether the business rules encoded in the SQL match the business rules that the organization actually follows. A KPI formula can be implemented exactly as specified in the SPEC and still be wrong if the SPEC misunderstands how the business calculates that metric. Unit tests confirm that the code does what the code says; they do not confirm that what the code says is what the business means. Analysts writing or reviewing mart models should verify KPI definitions with the business owners who use them, not just with the SPEC that documents them.

### Source System Quality Characteristics

The 10 source systems in this project span a wide range of data maturity, and the quality risks each one introduces are shaped by how the system was built, when it was deployed, and how much governance its operators have in place. Understanding these patterns helps analysts anticipate where problems are likely to appear — and where a passing test suite may be masking gaps that the pipeline cannot detect.

**Enterprise SaaS platforms** (VistaReserve, InfraTrak, PeopleFirst) generally enforce constraints at the point of entry: required fields, picklist validation, referential integrity between related tables. The data that arrives from these systems tends to be structurally clean. The quality risks are subtler — duplicate customer records created by front-desk staff who cannot find an existing profile (VistaReserve's 18–22% duplicate rate), or assets registered inconsistently because the onboarding process varies by region (InfraTrak covers only 28 of 50 parks).

**Statewide mandated systems** (StateGov Financials, PeopleFirst) are well-governed but operationally constrained. Their schemas reflect the needs of the agencies that built them, not necessarily the needs of downstream analytics. StateGov's general ledger aggregates daily transactions into monthly batches, losing the daily detail that revenue analysis needs. PeopleFirst tracks duty stations at the organizational unit level, not the park level — so joining employees to parks is an approximation, not a precise mapping. These are not data entry errors; they are design decisions made for a different purpose.

**Legacy and decommissioned systems** (LegacyRes, StateGov's COBOL layer, BioSurvey's Access database) carry the longest history and the most inconsistency. Date formats change across export eras. Identifiers follow conventions that no longer match current systems. Mixed-entity tables store different observation types in the same columns, relying on implicit conventions that were understood by the original users but are not documented. The pipeline can cast and rename these columns, but it cannot reconstruct the context that was lost when the system's original operators retired or moved on.

**Spreadsheet and manual-entry systems** (GrantTrack) have the least structural governance. There are no enforced constraints on what values can be entered, no referential integrity between sheets, and no audit trail for changes. The 2–5% reconciliation gap between GrantTrack and StateGov Financials is a known, persistent condition — not a bug to be fixed, but a reality to be documented and monitored. Analysts working with grant data should treat `severity: warn` tests as the appropriate signal level for fields where manual entry introduces expected variation.

**Air-gapped systems** (RangerShield) present a different challenge entirely. The data is structurally clean within its own domain, but it cannot be joined to any other system electronically. All cross-domain data use goes through manual extraction and sanitization, which introduces both latency and the possibility of transcription errors. The pipeline treats RangerShield data as self-contained — integration models that consume it do not attempt cross-system joins, and any analytical connection to other domains (like mapping incidents to parks) depends on location text matching rather than shared keys.

**IoT and pilot systems** (TrafficCount) are the newest and least proven. Sensor coverage is limited to roughly 15% of parks, and the vehicle occupancy multiplier used to estimate visitor counts has not been validated since 2019. The data itself is structurally reliable — sensors produce consistent, timestamped records — but the derived metrics (estimated visitors from vehicle counts) depend on assumptions that analysts should understand before using them in reports. Row count tests and freshness checks confirm that sensor data is flowing; they do not confirm that the counts are representative of actual visitation patterns across the full park system.

### Analyst Responsibilities for Data Quality

The governance toolchain — sqlfluff, dbt-score, dbt-project-evaluator, and `scripts.reviewer` — automates roughly 47% of the project's 103 standards. The remaining 53% depend on the judgment of the person writing or reviewing the model. Automated tools can confirm that a test exists; they cannot confirm that the right test exists, or that the test is sufficient for the risk it is meant to address.

When writing or modifying a model, consider the following responsibilities as part of the work — not as a separate review step, but as part of how the model is designed.

**Understand the source before writing the model.** Run `scripts.inspect` on the source table to see its actual column types, cardinality, null distribution, and sample values, or run the profiler (`python -m scripts.profiler.cli`) against an existing source or model node using dbt selector syntax for deeper statistical analysis and automatic dbt Signals. Read the Data Inventory entry for the source system to understand its known quality issues. A staging model for a table with a 20% null rate on a critical field needs a different testing strategy than one for a table where that field is always populated.

**Choose test severity based on what the source system can guarantee.** A `not_null` test with `severity: error` is appropriate when the source system enforces the field as required — a null value genuinely indicates a pipeline break or a system failure. The same test with `severity: warn` is appropriate when the source system allows blanks and blanks are a known, expected condition — walk-up park visitors who are not required to provide contact information, seasonal employees whose certification records have not yet been entered, or grants whose compliance deadlines have not been set because the award is still in negotiation.

**Document what you cannot test.** If a column's accuracy depends on a business process that happens outside the pipeline — a park ranger entering incident locations as narrative text, a grants analyst manually reconciling spreadsheet totals against the general ledger, a seasonal worker estimating headcounts — note this in the model's YAML description or in a `meta:` block. Future analysts and reviewers need to understand not just what the tests cover, but what the tests cannot cover and why.

**Monitor warn-level tests over time.** A `severity: warn` test that fires occasionally is doing its job — it surfaces a known condition without blocking the build. A `severity: warn` test that fires on every run may indicate that the condition has worsened, that the threshold needs adjustment, or that the source system's behavior has changed. Treat persistent warnings as signals worth investigating, not as background noise to ignore.

**Verify business logic with the people who use it.** Unit tests on mart KPI calculations confirm that the SQL produces the expected output for a given input. They do not confirm that the formula is correct from the business's perspective. Before marking a mart model as complete, verify the business rules — not just the SQL — with the domain experts who will consume the output. This is especially important for calculations that combine data from multiple source systems, where the interaction between systems can produce results that are technically correct but operationally misleading.

### Contributing Quality Tests

When adding or modifying a model, follow this workflow to identify which quality tests are needed:

1. **Identify the grain.** What is one row in this model? The primary key column(s) must have `unique` and `not_null` tests. For composite keys, use `dbt_utils.unique_combination_of_columns`. Run the profiler (`$env:PYTHONUTF8=1; python -m scripts.profiler.cli --select <model>`) first — its `CAST_HINT` and `UNUSED_COLUMN` signals often surface candidates for additional tests before you write a single line of YAML.

2. **Identify the dimension.** For each column, ask which DAMA dimension is most at risk:
   - A column that could be null when it should not be → **Completeness** → `not_null`
   - A column with a fixed set of valid values → **Validity** → `accepted_values`
   - A numeric column with a meaningful range → **Validity** → `expect_column_values_to_be_between`
   - A foreign key to another model → **Consistency** → `relationships`
   - A date pair that must be ordered → **Consistency** → `expect_column_pair_values_A_to_be_greater_than_B`

3. **Choose the severity.** Use `severity: error` for tests that indicate broken data (duplicated keys, null surrogate keys). Use `severity: warn` for tests that flag data quality issues worth monitoring but that should not block a build (e.g., optional fields with known gaps, source systems with incomplete coverage).

4. **Add the test to the `_models.yml` file** in the appropriate directory. Place tests under the column they validate. Document the DAMA dimension in a `meta:` block if the mapping is not obvious.

5. **Verify with `scripts.reviewer`.** Run the governance checker to confirm the new tests pass and the model's score has not dropped.

```powershell
$env:PYTHONUTF8=1; python -m scripts.reviewer --select <your_model>
```

### Reconciliation Tests

For mart models that aggregate data, add singular reconciliation tests in `tests/marts/`. These are standalone SQL files that return rows only when an assertion fails — for example, when a report-level total does not match the sum of its underlying fact records. Reconciliation tests target the **Accuracy** dimension and serve as end-to-end validation that business logic is correct.

See `tests/marts/assert_revenue_sums_balance.sql` for a working example.

## Git Workflow

### Branching

Create a feature branch for each unit of work. Branch names should describe the change in lowercase with hyphens:

```powershell
# Create and switch to a new branch
git checkout -b feat/add-int-work-orders

# Other common prefixes
git checkout -b fix/fct-reservations-null-amount
git checkout -b refactor/staging-vistareserve-cleanup
git checkout -b docs/update-data-dictionary
```

Keep branches short-lived. A branch that touches one or two models and their YAML properties is easier to review than a branch that rewrites an entire layer. When a branch grows beyond its original scope, consider splitting it.

### Making Commits

Stage specific files rather than using `git add .`, which can accidentally include scratch files, DuckDB lock files, or temporary checker output:

```powershell
# Stage specific model and YAML files
git add models/integration/int_work_orders.sql models/integration/_models.yml

# Review what will be committed
git status
git diff --staged

# Commit with a descriptive message
git commit -m "feat(integration): add int_work_orders joining InfraTrak and GeoParks work requests"
```

Commit messages should start with a type prefix that describes the nature of the change:

| Prefix | Use |
|---|---|
| `feat` | New models, tests, macros, or seeds |
| `fix` | Bug fixes in SQL logic, YAML corrections, broken tests |
| `refactor` | Restructuring without changing behavior |
| `docs` | Documentation, descriptions, or README changes |
| `chore` | Dependency updates, config changes, tooling |

Include the layer or domain in parentheses when it helps clarify scope: `feat(staging): add stg_granttrack__match_fund_transactions` or `fix(marts/revenue): correct reservation amount aggregation`.

### Working with Branches

```powershell
# See all local branches
git branch

# Switch between branches
git checkout main
git checkout feat/add-int-work-orders

# Pull the latest changes from main before starting work
git checkout main
git pull
git checkout -b feat/my-new-branch

# Merge main into your branch to stay current
git checkout feat/my-new-branch
git merge main

# Delete a branch after it has been merged
git branch -d feat/add-int-work-orders
```

### Before Pushing

Run the governance checker on any models you changed before pushing your branch. This catches formatting, documentation, and structural issues before they reach review:

```powershell
$env:PYTHONUTF8=1; python -m scripts.reviewer --select <your_model>
```

If the checker passes, push your branch:

```powershell
git push -u origin feat/add-int-work-orders
```

### Pull Requests

When opening a pull request, include which models were added or changed, whether `dbt build` and `scripts.reviewer` pass, and any governance decisions worth noting (CDM exceptions, severity choices, known data quality gaps). Reviewers should be able to understand the scope and rationale without reading every line of SQL.

### Copying Files into an Existing Repository

To adopt part of this project — for example, the shared agent rules in `.agent/rules/` or the `scripts/` toolchain — into a repository you already own, use `git archive` to extract a specific directory as a tarball and pipe it into the target location:

```powershell
# Export a single directory from this repo into an existing repo
git -C C:\path\to\dbt-dcr-analytics archive HEAD .agent/rules/ | tar -x -C C:\path\to\your-repo
```

Replace `.agent/rules/` with whichever path you want to copy. The directory structure is preserved. Then stage and commit in the target repo:

```powershell
cd C:\path\to\your-repo
git add .agent/rules/
git commit -m "chore: adopt DCR Analytics agent rules"
```

To copy the scripts toolchain, copy the whole `scripts/` directory — the sub-packages (`reviewer/`, `profiler/`, `inspect/`, etc.) must be copied together with `_core/` since they share internal imports:

```powershell
git -C C:\path\to\dbt-dcr-analytics archive HEAD scripts/ | tar -x -C C:\path\to\your-repo
```

If `tar` is not available, use `Copy-Item` directly and then `git add`:

```powershell
Copy-Item -Recurse C:\path\to\dbt-dcr-analytics\.agent\rules\ C:\path\to\your-repo\.agent\rules\
```

## Project Standards

The 103 governance rules in [reference/dbt_project_standards.md](reference/dbt_project_standards.md) define what "done" looks like for every file in the project. The document is organized by the type of work it governs — cross-model formatting, CTE structure, layer-specific SQL conventions, YAML properties, and testing expectations — so that contributors can evaluate their own work before it reaches review, and reviewers can assess completeness against a shared standard rather than individual preference.

Each rule has an ID (e.g., `ALL-CTE-01`, `STG-YML-03`, `MRT-YML-04`) and is tagged as either **Automated** (enforced by sqlfluff, dbt-score, dbt-project-evaluator, or `scripts.reviewer`) or **Manual** (requires human judgment during review). The automated toolchain covers roughly 47% of the rules; the remaining 53% — meaningful names, description quality, business rule test design — are evaluated through `scripts.reviewer` and peer review.

Rules that govern data quality testing include parenthetical DAMA dimension labels (e.g., "Uniqueness, Completeness") so that the connection between a governance rule and the quality dimension it protects is traceable at the rule level. See the [Data Quality and DAMA Dimensions](#data-quality-and-dama-dimensions) section for how these dimensions translate into dbt testing patterns.

Contributors should read this document before writing or reviewing models. The standards are not suggestions — they are the shared definition of quality for the project.

## Project Structure

```
dbt-dcr-analytics/
├── models/
│   ├── staging/                  # Views: one subdirectory per source system
│   │   ├── vistareserve/         #   stg_vistareserve__reservations, etc.
│   │   ├── geoparks/             #   stg_geoparks__parks_master, etc.
│   │   ├── infratrak/            #   stg_infratrak__assets, etc.
│   │   ├── stategov/             #   stg_stategov__general_ledger, etc.
│   │   ├── granttrack/           #   stg_granttrack__active_awards, etc.
│   │   ├── biosurvey/            #   stg_biosurvey__flora_fauna_surveys, etc.
│   │   ├── peoplefirst/          #   stg_peoplefirst__employees, etc.
│   │   ├── rangershield/         #   stg_rangershield__incidents, etc.
│   │   ├── trafficcount/         #   stg_trafficcount__vehicle_counts, etc.
│   │   └── legacyres/            #   stg_legacyres__reservations, etc.
│   ├── integration/              # Tables: CDM-aligned entity models
│   │   ├── int_parks.sql         #   Park entity (3 sources)
│   │   ├── int_contacts.sql      #   Contact entity
│   │   ├── int_transactions.sql  #   Transaction entity
│   │   └── ...
│   ├── marts/                    # Tables: business domain models
│   │   ├── revenue/              #   dim_customers, fct_reservations, rpt_park_revenue_summary
│   │   ├── finance/              #   dim_vendors, fct_expenditures
│   │   ├── operations/           #   fct_incidents_and_maintenance
│   │   ├── attendance/           #   fct_visitation
│   │   ├── core/                 #   dim_assets, dim_date, dim_employees
│   │   └── reporting/            #   rpt_agency_performance
│   └── project_evaluator/        # DAG validation models
├── seeds/                        # Reference CSVs and CDM catalog seeds
├── tests/                        # Singular SQL tests (reconciliation, FK validation)
├── macros/                       # Reusable SQL macros
├── scripts/                      # Python governance and discovery tools
│   ├── _core/                    #   Shared connectors, renderers, and selector
│   ├── reviewer/                 #   Automated + qualitative model review
│   ├── profiler/                 #   Column-level statistical profiling
│   ├── grain/                    #   Key discovery and join cardinality
│   ├── llm_context/              #   LLM context generation and CDM advisor
│   ├── scaffold/                 #   Model scaffolding
│   ├── preflight/                #   Pre-build compile + lint + test
│   ├── governance/               #   Standards parsing and dbt-score rules
│   ├── cdm/                      #   CDM catalog search
│   ├── export/                   #   Mart data export to CSV/Parquet
│   └── inspect/                  #   Source table profiling and discovery
├── analyses/                     # Ad hoc analytical queries
├── reference/                    # Project documentation, standards, and specs
│   ├── dbt_project_standards.md  #   103 governance rules
│   ├── SPEC_vertical_slice_revenue.md
│   └── business_artifacts/       #   Upstream business documents (read-only)
├── source_data/
│   ├── duckdb/                   # 10 source .duckdb files
│   └── cdm_metadata/             # Microsoft CDM entity and column definitions
├── plugins/                      # Custom sqlfluff plugin
├── dbt_project.yml
├── profiles.yml
├── packages.yml
├── pyproject.toml                # dbt-score configuration
├── .sqlfluff                     # sqlfluff configuration
└── requirements.txt
```

## Resources

- [dbt documentation](https://docs.getdbt.com/)
- [dbt-duckdb adapter](https://github.com/duckdb/dbt-duckdb)
- [sqlfluff](https://sqlfluff.com/)
- [dbt-score](https://dbt-score.readthedocs.io/)
- [dbt-project-evaluator](https://github.com/dbt-labs/dbt-project-evaluator)
- [Microsoft Common Data Model](https://learn.microsoft.com/en-us/common-data-model/)
- [DAMA DMBOK](https://www.dama.org/cpages/body-of-knowledge)
- [dbt Discourse](https://discourse.getdbt.com/) — community Q&A
- [dbt Community Slack](https://community.getdbt.com/) — live discussion

## Credits

This project was built with [Claude Code](https://claude.com/claude-code) and [Google Gemini](https://gemini.google.com/app), demonstrating how AI-assisted development can accelerate dbt project scaffolding while maintaining governance, testing, and documentation standards. Cross-agent coordination via [Anthropic's Agent SDK](https://github.com/anthropics/anthropic-sdk-python) and Google's Antigravity enables shared governance rules and prompts across different AI assistants.

The synthetic source data is generated using [Mimesis](https://mimesis.name/). The governance toolchain includes [dbt-score](https://github.com/mkdocs-plugins/dbt-score), [dbt-project-evaluator](https://github.com/dbt-labs/dbt-project-evaluator), and [sqlfluff](https://github.com/sqlfluff/sqlfluff).

Inspired by real-world challenges in public sector analytics, this project demonstrates best practices for:
- Standardized dbt project structure across 10 heterogeneous source systems
- Governance automation with linting, scoring, and custom checkers
- CDM conformance and cross-system entity reconciliation
- Comprehensive data quality testing across the pipeline
- Local-first development with DuckDB (no external infrastructure needed)
