# DCR Analytics — dbt Public Sector Example

This is an example project demonstrating how a state government agency — the Department of Conservation and Recreation (DCR) — might build a governed, tested, and documented analytical data platform using dbt and DuckDB. The project models 10 synthetic source systems spanning reservations, finance, asset management, law enforcement, human capital, biological surveys, and visitor counting; then transforms them through a three-layer dbt pipeline into business-ready marts.

The source data is entirely synthetic, generated with Python and [Mimesis](https://mimesis.name/) to simulate realistic data quality issues that public sector organizations encounter: stale crosswalks, regional coverage gaps, mixed identifier formats, and legacy system quirks. The governance toolchain — sqlfluff, dbt-score, and dbt-project-evaluator — enforces 103 project standards that map to [DAMA data quality dimensions](#data-quality-and-dama-dimensions), making this a practical reference for teams that need to balance compliance with usability.

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
- [VS Code](https://code.visualstudio.com/) with the [dbt Power User](https://marketplace.visualstudio.com/items?itemName=innoverio.vscode-dbt-power-user) extension (recommended)
- [Git](https://git-scm.com/downloads)
- Windows 11 with PowerShell

### Setup

Clone the repository and create a Python virtual environment:

```powershell
git clone https://github.com/<your-org>/dbt-public-sector-example.git
cd dbt-public-sector-example

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

### check_model.py — Automated Governance Gate

The primary quality gate. Runs sqlfluff, dbt build, dbt-score, dbt-project-evaluator, and a suite of custom static analysis checks against one or more models.

```powershell
$env:PYTHONUTF8=1; python scripts/check_model.py --select int_parks
$env:PYTHONUTF8=1; python scripts/check_model.py --select models/integration --json
$env:PYTHONUTF8=1; python scripts/check_model.py --select int_parks --output tmp/results.json
```

The `PYTHONUTF8=1` environment variable is needed on Windows to prevent encoding errors in the rich console output.

What it checks:
- **sqlfluff lint** — formatting compliance (zero violations required)
- **dbt build** — model compilation and schema test passage
- **dbt-score** — documentation quality scoring (minimum 5.0)
- **dbt-project-evaluator** — DAG structure and naming convention rules
- **Manifest analysis** — YAML/SQL column alignment, CTE structure, layer-specific rules
- **CDM conformance** — column mapping to Common Data Model entity catalogs

### review_model.py — Qualitative Review

Evaluates the standards that automated linters cannot check: meaningful names, description quality, and business rule design. Operates in two modes.

```powershell
# Generate a review checklist for an AI agent or manual review
python scripts/review_model.py --select int_parks --agent

# Export structured YAML review files for batch processing
python scripts/review_model.py --select models/integration --export-yaml

# Interactive CLI review (prompts you step-by-step)
python scripts/review_model.py --select int_parks
```

### inspect_source.py — Source Data Discovery

Profiles a source table before writing staging models. Reports row counts, column schemas, uniqueness and cardinality analysis, null distributions, date ranges, and sample rows.

```powershell
# List all tables in a source database
python scripts/inspect_source.py --type duckdb --conn source_data/duckdb/dcr_rev_01_vistareserve.duckdb

# Profile a specific table
python scripts/inspect_source.py --type duckdb --conn source_data/duckdb/dcr_rev_01_vistareserve.duckdb --table main.reservations
```

### search_cdm.py — CDM Catalog Search

Searches the full Microsoft Common Data Model column catalog using keyword and fuzzy matching. Useful when mapping staging columns to CDM entity attributes.

```powershell
# Search for columns related to a concept
python scripts/search_cdm.py reservation status

# Require all keywords to match
python scripts/search_cdm.py park name --all

# Filter to a specific CDM entity
python scripts/search_cdm.py amount --entity FinancialTransaction
```

### summarize_reviews.py — Review Aggregator

Aggregates review YAML files (from `review_model.py --export-yaml`) into a single Markdown summary report showing failure trends and rule-by-rule breakdowns.

```powershell
python scripts/summarize_reviews.py --input_dir tmp/reviews --output_file tmp/review_summary.md
```

### parse_standards.py — Standards JSON Builder

Parses the 103 governance rules from `reference/dbt_project_standards.md` into a structured JSON file used by the review scripts. Run this if the standards document changes.

```powershell
python scripts/parse_standards.py
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

The scoring rules include four project-specific rules defined in `scripts/dbt_score_rules.py`:

| Rule | What It Checks |
|---|---|
| `no_test_rationale_in_description` | Descriptions must not contain test-justification language ("unique", "not_null", "fan-out", etc.) |
| `mart_contract_enforced` | `fct_` and `dim_` models must have `contract: { enforced: true }` |
| `mart_columns_have_data_type` | All columns in mart models must declare a `data_type` |
| `no_per_model_yaml` | Models must not use a YAML file named `<model_name>.yml`; use `_models.yml` instead |

### dbt-project-evaluator — DAG Structure

[dbt-project-evaluator](https://github.com/dbt-labs/dbt-project-evaluator) validates the project DAG: naming conventions, directory placement, dependency direction, and structural patterns. It runs as part of `dbt build` via three custom fact models in `models/project_evaluator/`.

The project also maintains a `seeds/dbt_project_evaluator_exceptions.csv` for documented, intentional deviations from the evaluator's default rules.

### check_model.py — All Three Combined

In practice, you rarely need to run these tools individually. `check_model.py` orchestrates all three — plus additional static analysis — into a single pass:

```powershell
$env:PYTHONUTF8=1; python scripts/check_model.py --select int_parks
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

### How Each Layer Contributes

Quality enforcement is cumulative — each layer adds dimension coverage that the previous layer cannot provide.

**Sources:** Timeliness checks via `dbt source freshness`. This is the only layer where freshness can be evaluated, because staging models are views that reflect source state at query time.

**Staging:** Uniqueness (`unique` + `not_null` on the natural key) and basic validity (type casting catches malformed values). Staging tests protect the rest of the pipeline from source-level problems.

**Integration:** Uniqueness on surrogate keys, completeness via row count guards on union models, consistency via relationship tests between integration entities, and validity via CDM `accepted_values` on enumerated fields.

**Marts:** All six dimensions converge. Contracts enforce structural consistency. Unit tests verify accuracy of business logic. Relationship tests confirm dimensional integrity. Reconciliation tests (singular SQL tests in `tests/marts/`) validate that aggregated metrics balance against their underlying facts.

### Contributing Quality Tests

When adding or modifying a model, follow this workflow to identify which quality tests are needed:

1. **Identify the grain.** What is one row in this model? The primary key column(s) must have `unique` and `not_null` tests. For composite keys, use `dbt_utils.unique_combination_of_columns`.

2. **Identify the dimension.** For each column, ask which DAMA dimension is most at risk:
   - A column that could be null when it should not be → **Completeness** → `not_null`
   - A column with a fixed set of valid values → **Validity** → `accepted_values`
   - A numeric column with a meaningful range → **Validity** → `expect_column_values_to_be_between`
   - A foreign key to another model → **Consistency** → `relationships`
   - A date pair that must be ordered → **Consistency** → `expect_column_pair_values_A_to_be_greater_than_B`

3. **Choose the severity.** Use `severity: error` for tests that indicate broken data (duplicated keys, null surrogate keys). Use `severity: warn` for tests that flag data quality issues worth monitoring but that should not block a build (e.g., optional fields with known gaps, source systems with incomplete coverage).

4. **Add the test to the `_models.yml` file** in the appropriate directory. Place tests under the column they validate. Document the DAMA dimension in a `meta:` block if the mapping is not obvious.

5. **Verify with `check_model.py`.** Run the governance checker to confirm the new tests pass and the model's score has not dropped.

```powershell
$env:PYTHONUTF8=1; python scripts/check_model.py --select <your_model>
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
$env:PYTHONUTF8=1; python scripts/check_model.py --select <your_model>
```

If the checker passes, push your branch:

```powershell
git push -u origin feat/add-int-work-orders
```

### Pull Requests

When opening a pull request, include which models were added or changed, whether `dbt build` and `check_model.py` pass, and any governance decisions worth noting (CDM exceptions, severity choices, known data quality gaps). Reviewers should be able to understand the scope and rationale without reading every line of SQL.

## Project Standards

The 103 governance rules in [reference/dbt_project_standards.md](reference/dbt_project_standards.md) define what "done" looks like for every file in the project. The document is organized by the type of work it governs — cross-model formatting, CTE structure, layer-specific SQL conventions, YAML properties, and testing expectations — so that contributors can evaluate their own work before it reaches review, and reviewers can assess completeness against a shared standard rather than individual preference.

Each rule has an ID (e.g., `ALL-CTE-01`, `STG-YML-03`, `MRT-YML-04`) and is tagged as either **Automated** (enforced by sqlfluff, dbt-score, dbt-project-evaluator, or `check_model.py`) or **Manual** (requires human judgment during review). The automated toolchain covers roughly 47% of the rules; the remaining 53% — meaningful names, description quality, business rule test design — are evaluated through `review_model.py` and peer review.

Rules that govern data quality testing include parenthetical DAMA dimension labels (e.g., "Uniqueness, Completeness") so that the connection between a governance rule and the quality dimension it protects is traceable at the rule level. See the [Data Quality and DAMA Dimensions](#data-quality-and-dama-dimensions) section for how these dimensions translate into dbt testing patterns.

Contributors should read this document before writing or reviewing models. The standards are not suggestions — they are the shared definition of quality for the project.

## Project Structure

```
dbt-public-sector-example/
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
