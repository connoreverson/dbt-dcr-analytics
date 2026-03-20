# Scripts Directory Redesign — Design Specification

**Date:** 2026-03-20
**Status:** Draft
**Audience:** Connor (project lead) + analyst team (VS Code, dbt-core, BigQuery)

## Problem Statement

The `scripts/` directory grew organically into 8 flat scripts plus a well-structured `profiler/` sub-package. The team needs tooling that:

1. Guides analysts toward entity-first modeling instead of report-driven development
2. Catches grain errors, join fan-outs, and integration model anti-patterns before review
3. Works against both DuckDB (Connor's local dev) and BigQuery (team's production target)
4. Produces LLM-friendly output analysts can paste into Gemini for modeling assistance
5. Scales to tables with tens of thousands to millions of rows

The team's primary anti-patterns:

- **Report-driven development:** They go straight from source tables to dashboard-shaped models, skipping dimensional modeling. They don't identify the business entity they're modeling, don't consider CDM alignment, and build single-source pass-through integration models without surrogate keys or union-ready structure.
- **Page-shaped facts:** They build one fact model per dashboard page instead of modeling the underlying business event. Facts embed descriptive attributes (park names, customer details) directly instead of joining to dimensions.
- **Skipping dimensions:** They treat dimensions as optional enrichments rather than first-class entities. Descriptive attributes are duplicated across every fact row.
- **Pass-through reports:** They create report models that consume a single fact without aggregation or multi-table combination, adding indirection without value.
- **Duplicate facts:** Multiple fact models capture the same business event at different grains, when a single fact + report model would suffice.

## Audience and Workflow

**Same codebase, different workflows:**

- **Analysts** run dbt-core locally in VS Code against BigQuery. They use `new-model` (guided intake), `preflight` (self-check before PR), and `profiler` (source exploration). They have Google Workspace AI Pro (Gemini web UI) for LLM assistance.
- **Connor** uses all tools including `reviewer` (PR-level governance review), `grain` (standalone analysis), `cdm-match` (entity discovery), and `scaffold` (direct model/test generation).

## Implementation Phases

The packages are built in the following order. Phase numbers reflect build priority based on team impact and dependency ordering. The labels (F+E, G, etc.) reference the original brainstorming priority ranking where F=join cardinality, E=grain verification, G=LLM context, D=test scaffolding, B=preflight, C=reviewer, A=profiler performance.

| Phase | Package | Original Priority | Rationale |
|---|---|---|---|
| 0 | `_core/` | (prerequisite) | Shared infrastructure must exist before downstream packages |
| 1 | `grain/` | F+E | Highest-impact: catches the exact fan-out and grain errors plaguing the team |
| 2 | `llm_context/` | G | Primary analyst workflow entry point; depends on CDM seeds |
| 3 | `scaffold/` | D | Generates starter files; called by `llm_context/new_model` |
| 4 | `preflight/` | B | Orchestrates grain + scaffold + lint; depends on phases 1-3 |
| 5 | `reviewer/` | C | Connor's tooling; migration of existing scripts |
| 6 | `profiler/` refactor | A | Performance fix + `_core/` integration; lowest urgency |
| 7 | Migrate remaining scripts | — | `governance/`, `cdm/`, `export/`, `inspect/` |

Each phase is independently shippable. The team can start using `grain/` and `llm_context/` before later phases exist.

## Directory Structure

```
scripts/
├── _core/                      # Shared infrastructure
│   ├── __init__.py
│   ├── config.py               # Env detection, manifest resolution, project paths
│   ├── selector.py             # Shared dbt selector resolution (all packages delegate here)
│   ├── connectors/             # DuckDB + BigQuery database access
│   │   ├── __init__.py
│   │   ├── base.py             # Abstract base (extracted from profiler)
│   │   ├── duckdb.py           # DuckDB connector (extracted from profiler)
│   │   └── bigquery.py         # BigQuery connector (extracted from profiler)
│   ├── renderers/              # Output formatting
│   │   ├── __init__.py
│   │   ├── terminal.py         # Rich-based terminal output
│   │   ├── markdown.py         # Markdown files
│   │   ├── html.py             # Standalone HTML reports
│   │   └── llm.py              # NEW: structured LLM-pasteable output
│   └── models.py               # Shared dataclasses
│
├── profiler/                   # Source profiling (existing, refactored in phase 6)
│   ├── cli.py                  # Adds 'llm' as fourth output mode after _core/ extraction
│   ├── analyzers/
│   │   ├── stats.py            # Two-tier: quick SQL queries or full ydata-profiling
│   │   ├── dbt_signals.py
│   │   └── pii.py
│   ├── selector.py             # Delegates to _core/selector.py after refactor
│   ├── sanitizer.py
│   └── models.py
│   # NOTE: connectors/ and renderers/ move to _core/ in phase 0.
│   # Profiler imports from _core/ after phase 6 refactor.
│
├── grain/                      # Grain verification + join cardinality + layer-specific lint
│   ├── __init__.py
│   ├── cli.py                  # Entry: python -m scripts.grain --select <model>
│   ├── key_discovery.py        # Candidate PK detection via analytical queries
│   ├── join_analysis.py        # sqlglot AST parsing + cardinality queries
│   ├── integration_lint.py     # Single-source, no SK, pass-through, no CDM checks
│   └── mart_lint.py            # Wide facts, missing dims, pass-through reports, duplicate grain
│
├── llm_context/                # LLM context generation + CDM advisor + guided intake
│   ├── __init__.py
│   ├── cli.py                  # Entry: python -m scripts.llm_context <subcommand>
│   ├── new_model.py            # Guided intake questionnaire (questionary-based)
│   ├── model_context.py        # Summarize existing model for LLM consumption
│   ├── source_context.py       # Summarize source tables for LLM consumption
│   └── cdm_advisor.py          # Three-tier CDM entity matching
│
├── scaffold/                   # Test and model scaffolding
│   ├── __init__.py
│   ├── cli.py                  # Entry: python -m scripts.scaffold <subcommand>
│   ├── test_scaffold.py        # Generate missing YAML tests as copy-pasteable YAML
│   ├── integration_scaffold.py # Generate integration model SQL + YAML skeleton
│   └── mart_scaffold.py        # Generate fact/dimension/report SQL + YAML skeletons
│
├── preflight/                  # Analyst self-check before PR
│   ├── __init__.py
│   ├── cli.py                  # Entry: python -m scripts.preflight --select <model>
│   └── checks.py               # Orchestrates grain + lint + test coverage + YAML alignment
│
├── reviewer/                   # Connor's review tooling
│   ├── __init__.py
│   ├── cli.py                  # Entry: python -m scripts.reviewer --select <model>
│   ├── automated.py            # From check_model.py
│   ├── qualitative.py          # From review_model.py
│   └── summarize.py            # From summarize_reviews.py
│
├── governance/                 # Standards parsing + dbt-score rules
│   ├── __init__.py
│   ├── parse_standards.py      # From parse_standards.py (unchanged)
│   └── dbt_score_rules.py      # From dbt_score_rules.py (unchanged)
│
├── cdm/                        # CDM search (power-user, standalone)
│   ├── __init__.py
│   └── search.py               # From search_cdm.py
│
├── export/                     # Mart data export
│   ├── __init__.py
│   └── cli.py                  # From export_mart_data.py
│
└── inspect/                    # Source table inspection
    ├── __init__.py
    └── cli.py                  # From inspect_source.py
```

**Migration:** Profiler's connectors and renderers move to `_core/` in phase 0. Profiler imports from `_core/` after phase 6 refactor. All flat root-level scripts move into their respective sub-packages in phase 7. No flat scripts remain at the `scripts/` root (only `__init__.py`).

## Shared Infrastructure: `_core/`

### `config.py`

- Detect environment: DuckDB (local) vs BigQuery (prod) from `profiles.yml`
- Resolve manifest path, ensure it exists (run `dbt parse` if stale)
- Resolve database connection parameters

**Manifest staleness heuristic:** manifest.json is considered stale if its mtime is older than the most recent mtime of any `.sql` or `.yml` file under `models/`. When stale or absent, `config.py` runs `dbt parse` automatically. If `dbt parse` fails (network issues, profile misconfiguration, syntax errors), the tool exits with a clear error message: "Manifest is stale and `dbt parse` failed: {error}. Run `dbt parse` manually to diagnose." No silent fallback.

### `selector.py`

Shared dbt selector resolution. All packages delegate `--select` parsing to this module rather than reimplementing it. Supported syntax:

- Model name: `fct_reservations`, `int_parks`
- Source selector: `source:peoplefirst.employees`
- Graph operators: `+int_parks+`, `int_parks+`
- Tag selector: `tag:revenue`

Implementation delegates to `dbtRunner.invoke(["ls", "--select", ...])` (same approach as the existing profiler `selector.py`). Returns `SelectionTarget` objects from `_core/models.py`.

### `connectors/`

Extracted from `profiler/connectors/`. Same `BaseConnector` ABC with one addition:

**New abstract method:** `run_query(sql: str) -> pd.DataFrame` — executes arbitrary analytical SQL and returns results. Used by `grain/` for cardinality queries and by the profiler's quick mode for warehouse-side statistics. Both `DuckDBConnector` and `BigQueryConnector` must implement this method as part of the phase 0 extraction.

The existing `get_schema()` and `get_sample()` methods remain unchanged.

### `renderers/`

Extracted from `profiler/renderers/`. Same terminal/markdown/html renderers plus:

- New `llm.py` renderer: structured markdown optimized for LLM consumption. Concise, labeled sections, no decorative formatting. Includes suggested prompts.
- All packages use `--output terminal|markdown|html|llm` consistently, including the profiler after its phase 6 refactor.

### `models.py`

Shared dataclasses: `SelectionTarget`, `ColumnDef` (moved from profiler). New dataclasses as needed by downstream packages.

## Package Specifications

### Phase 1: `grain/` — Grain Verification, Join Cardinality, Integration Lint

**CLI:**
```bash
python -m scripts.grain --select fct_reservations
python -m scripts.grain --select int_grant_applications --output markdown
```

**`key_discovery.py`** — Candidate Primary Key Detection

Input: A dbt model selector (resolved via `_core/selector.py`).
Process:
1. Resolve the model via manifest, query the materialized table (or `dbt show`)
2. **Pruning strategy for column combinations:**
   - Single-column sweep first: compute `COUNT(DISTINCT col) / COUNT(*)` for every column
   - Only columns with individual uniqueness ratio > 0.5 are eligible for combination testing
   - Test 2-column combinations of eligible columns only (cap at 50 combinations)
   - 3-column combinations only if no 1- or 2-column candidate achieves uniqueness ratio >= 0.99
   - Use `APPROX_COUNT_DISTINCT` (BigQuery) / `approx_count_distinct` (DuckDB) for the initial sweep; exact `COUNT(DISTINCT ...)` only for top candidates
3. Rank candidates by uniqueness ratio (1.0 = perfectly unique)
4. Cross-reference against the model's YAML: does a `unique` or `unique_combination_of_columns` test exist on the identified key?

Output: Ranked candidate keys with uniqueness ratios and test coverage status.

**`join_analysis.py`** — Join Cardinality Checker

Input: A dbt model selector.
Process:
1. Load compiled SQL from `target/compiled/`
2. Parse with sqlglot — walk AST for JOIN nodes, extract join type (LEFT/INNER/etc.) and ON conditions
3. Resolve parent models from `depends_on` in manifest
4. For each join, query both sides to determine cardinality: count distinct join key values on each side, classify as one-to-one / one-to-many / many-to-one / many-to-many
5. For LEFT JOINs where right side is one-to-many: flag as fan-out risk
6. Compare model output row count to driving table row count — if larger, identify which join caused the expansion

Output: Per-join cardinality classification with fan-out warnings.

**`integration_lint.py`** — Integration Model Anti-Pattern Detection

Runs automatically when `--select` target is an `int_` model. Checks:

| Check | Detection Method | Source |
|---|---|---|
| Single-source | `depends_on` has only 1 staging parent | manifest |
| No surrogate key | No column ending in `_sk` in output | query |
| Pass-through | Output columns are 1:1 renames of input columns | sqlglot AST comparison |
| No CDM mapping | No `cdm_entity` in YAML `meta:` block | manifest |
| No intake metadata | No `intake_completed: true` in YAML `meta:` block | manifest |

Each finding is a warning with an explanation of why it matters and a command to fix it.

**Note on intake metadata:** The intake check looks for `meta: { intake_completed: true }` in the model's YAML entry, not for a file on disk. This is set by `new_model.py` when it generates the YAML snippet, and persists in version control. Existing `int_*` models built before this tooling will not have this metadata — the check produces a low-severity suggestion ("Consider running `python -m scripts.llm_context new-model` to document this model's entity and grain"), not a warning. This avoids false warnings on the 7+ existing integration models.

**`mart_lint.py`** — Mart Model Anti-Pattern Detection

Runs automatically when `--select` target is a `fct_`, `dim_`, or `rpt_` model. Detects the specific anti-patterns documented in the team's issue trends: page-shaped facts, skipped dimensions, pass-through reports, and duplicate grains.

**Fact model checks (`fct_`):**

| Check | What it detects | Method |
|---|---|---|
| Wide fact | Fact has multiple non-key, non-measure string columns that look like descriptive attributes (e.g., `park_name`, `customer_email`, `region`) without corresponding dimension FK columns | Query output columns; flag string columns matching `_name`, `_email`, `_address`, `_description`, `_region`, `_type` patterns where no corresponding `_sk` or `_id` FK exists for that entity |
| No dimension joins | Fact doesn't join to any `dim_` model | `depends_on` in manifest — check for any node with `dim_` prefix |
| Embedded dimensions | Fact contains columns that belong in a dimension — descriptive attributes duplicated per event row | Column name heuristic cross-referenced with existing dimension columns: if `dim_parks` has `park_name` and the fact also has `park_name` without joining to `dim_parks`, flag it |
| Duplicate grain | Another `fct_` model has the same candidate primary key pattern (same business event modeled twice) | Cross-reference `key_discovery` results across all `fct_` models in the project |
| Missing date dimension join | Fact has date columns but no join to `dim_date` | `depends_on` check + column inspection for `_date`, `_at`, `_on` suffixes |

For each finding, the output explains what to do:
- Wide fact → "These columns should live in dimension tables. Consider: [specific dimension suggestions based on existing dims and column names]"
- No dimension joins → "Fact models should join to dimensions for descriptive attributes, not carry them inline."
- Embedded dimensions → "dim_parks already has park_name — join via parks_sk instead of embedding"
- Missing date dimension → "Add date_key and join to dim_date for calendar/fiscal attributes"

**Dimension model checks (`dim_`):**

| Check | What it detects | Method |
|---|---|---|
| Not referenced | No `fct_` or `rpt_` model joins to this dimension | Reverse `depends_on` lookup across all mart models |
| Duplicate entity | Another `dim_` model covers the same entity (high column name overlap) | Column name similarity across all `dim_` models |
| Missing surrogate key | No `_sk` column in output | Query output columns |

**Report model checks (`rpt_`):**

| Check | What it detects | Method |
|---|---|---|
| Single-fact pass-through | Report only consumes one `fct_` model and doesn't aggregate | `depends_on` count (only 1 `fct_` parent) + sqlglot AST check for GROUP BY |
| No aggregation | Report has no GROUP BY clause — it's passing data through without changing the grain | sqlglot AST inspection |
| Grain same as source fact | Report output row count equals input fact row count — no grain change occurred | Query both and compare |

For single-fact pass-throughs, the output suggests: "This report only consumes fct_reservations without aggregation. Consider whether your BI tool can join the fact to its dimensions directly — a report model earns its place when it combines multiple facts or aggregates to a different grain."

### Phase 2: `llm_context/` — LLM Context Generation, CDM Advisor, Guided Intake

**CLI:**
```bash
python -m scripts.llm_context new-model              # Guided intake questionnaire
python -m scripts.llm_context cdm-match --concept "grant application"
python -m scripts.llm_context cdm-match --concept "grant application" \
  --source-columns "app_id, applicant_name, grant_type, amount_requested, status"
python -m scripts.llm_context model-summary --select int_parks
python -m scripts.llm_context source-summary --select source:peoplefirst.employees
```

**`new_model.py`** — Guided Intake Questionnaire

Interactive questionary-based workflow. The intake branches based on the target layer.

**Common questions (all layers):**

1. "What data are you working with?" — source system and table names
2. "What does each row represent?" — plain English grain statement
3. "What happens to this thing over time?" — multiple choice: static reference, lifecycle with statuses, point-in-time measurement, one-time event/transaction
4. "Who or what is involved?" — related entities
5. "What questions should the data answer?" — business questions (not report names)

**Layer selection:**

6. "Which layer is this model for?" — multiple choice:
   - Staging (cast/rename from source)
   - Integration (normalize an entity across systems)
   - Mart (business-facing: fact, dimension, or report)

**Integration branch:** Proceeds to CDM entity matching and integration model scaffolding as described above.

**Mart branch — model type classification:**

7. "What kind of mart model is this?" — multiple choice with explanations:
   - "A business event that happened (transaction, booking, inspection, measurement)" → FACT
   - "A descriptive entity (a park, a person, an asset, a date)" → DIMENSION
   - "A summary that combines multiple facts or aggregates to a different grain" → REPORT
   - "Not sure" → tool explains the distinction with concrete examples from the project, then re-asks

**Mart branch — FACT path:**

8. Tool queries existing `fct_` models in the project and displays them with their grain statements.
   "Do any of these existing facts already capture the same business event?"
   - If yes → "You may need a REPORT model that aggregates the existing fact, not a new fact. Let's explore that path instead." Redirects to REPORT path.
   - If no → proceeds

9. "What dimensions describe this event?" — checklist:
   - Who (a person, customer, or organization)
   - Where (a park, facility, or location)
   - When (a date or time period)
   - What (an asset, product, or item)

   For each selected dimension category, tool checks for existing `dim_` models:
   - If exists → "dim_parks exists — your fact should join via parks_sk, not embed park attributes"
   - If missing → "No customer dimension exists yet. Consider building dim_customers first, or flag this as a dependency."

   Output: fact model skeleton with surrogate key FKs to existing dimensions, measures only (no embedded descriptive columns), and TODO comments for missing dimensions. Note: the scaffold will generate FK references to dimensions that may not exist yet (e.g., `customer_sk` referencing `dim_customers`). This is intentional — the SQL will fail at `dbt build` time, which surfaces the missing dependency naturally. The TODO comments and the intake's "missing dimension" warning make this explicit.

**Mart branch — DIMENSION path:**

8. Tool queries existing `dim_` models and displays them.
   "Does your entity overlap with any of these?"
   - If yes → "Consider extending the existing dimension rather than creating a new one."
   - If no → proceeds to scaffold a dimension with surrogate key, descriptive attributes, and derived classifications.

**Mart branch — REPORT path:**

8. "Which existing fact tables does this report combine or aggregate?" — checklist of all `fct_` models in the project.

9. "What grain does the report aggregate to?" — free text (e.g., "park + month")

10. Tool validates the report earns its place:
    - If only one fact selected and no aggregation grain differs from the fact's grain → "This report only passes through a single fact. Consider whether your BI tool can do this join directly. Proceed anyway?"
    - If multiple facts or different grain → proceeds to scaffold a report model with per-fact CTEs and a final join.

**Output (all paths):**
- Model SQL skeleton appropriate to the layer and type
- YAML snippet with grain description, core tests, and `meta: { intake_completed: true, intake_date: "YYYY-MM-DD", model_type: "fact|dimension|report|integration" }`
- LLM context block (copy-paste ready for Gemini)
- Intake answers saved as `meta:` fields in the generated YAML (version-controlled, co-located with model)

**`cdm_advisor.py`** — Three-Tier CDM Entity Matching

**Tier 1 — Synonym Map (fast, curated, high precision):**
- Seed CSV `seeds/cdm_catalogs/cdm_concept_synonyms.csv` maps business concepts to CDM entities
- Columns: `concept`, `cdm_entity`, `confidence_note`
- `confidence_note` explains *why* the concept maps (teaching moment)
- Lookup: tokenize input, fuzzy match against `concept` column

**Tier 2 — CDM Description Search (broader recall):**

The existing column catalog CSVs (`seeds/cdm_catalogs/column_catalog_*.csv`) contain per-column descriptions but no entity-level descriptions. Tier 2 works as follows:

1. Tokenize input into keywords
2. **Derive entity-level context by aggregating column catalogs:** group columns by `cdm_entity_name`, concatenate their descriptions, and search this aggregated text for keyword matches. An entity where 5 column descriptions mention "application," "status," "request," "submitted" scores higher than one where only 1 column matches.
3. Additionally search individual column names and descriptions for keyword matches — if multiple columns in one entity match, boost that entity's score
4. Deduplicate against Tier 1 results

**Prerequisite seed:** `seeds/cdm_catalogs/entity_catalog.csv` with columns: `cdm_entity_name`, `entity_description`, `cdm_manifest`. This is a new deliverable — entity descriptions are richer and more useful for matching than aggregated column descriptions alone. When this seed exists, Tier 2 searches it directly. When it does not exist (before the seed is curated), Tier 2 falls back to the column-aggregation approach described above.

**Tier 3 — LLM Prompt Generation (fallback):**
- When Tier 1 and 2 produce weak/no results
- Generates a structured prompt the analyst can paste into Gemini
- Prompt frames the problem entity-first: describes the business process, lists source columns, asks which CDM entity to adapt or extend
- Includes extensibility question: "what other operations share this pattern?"

**Scoring when multiple tiers produce results:**
```
Final Score = (0.6 x synonym_match) + (0.3 x description_match) + (0.1 x column_overlap_bonus)
```

Column overlap bonus (optional, activated with `--source-columns`): checks which CDM entities have columns that semantically overlap with the analyst's source columns.

Output per candidate entity:
- Entity name + match score
- Entity description (from entity catalog if available, else derived from column descriptions)
- Core columns (10-15 commonly-mapped, not all 80)
- Column count (core vs total)
- Known uses in this project (existing `int_` models mapping to it)
- Why this entity fits (from synonym `confidence_note` or description match context)

**`model_context.py`** — Existing Model Summary for LLM

Input: dbt model selector (resolved via `_core/selector.py`).
Output: Structured markdown block containing layer, grain, parents, CDM entity, surrogate key, row count, column summary (keys/measures/attributes), and a suggested Gemini prompt pre-filled with the model's context.

**`source_context.py`** — Source Table Summary for LLM

Input: dbt source selector (resolved via `_core/selector.py`).
Output: Structured markdown block containing source system, table, row count, column list with types, candidate keys, and a suggested Gemini prompt for modeling decisions.

### Phase 3: `scaffold/` — Test and Model Scaffolding

**CLI:**
```bash
python -m scripts.scaffold tests --select stg_vistareserve__reservations
python -m scripts.scaffold tests --select stg_vistareserve__reservations --apply
python -m scripts.scaffold integration --entity "Request" \
  --sources stg_grantwatch__applications stg_grantwatch__amendments \
  --key application_id
```

**`test_scaffold.py`** — Generate Missing YAML Tests

Input: dbt model selector.

**Two modes:**
- `--dry-run` (default): prints suggested YAML to stdout for copy-paste review
- `--apply`: writes directly into the model's YAML file

When called by `preflight/`, it runs in dry-run mode and returns only the count of missing tests (no output).

Process:
1. Query materialized data (or `dbt show --limit 1000`)
2. Read existing YAML tests from manifest — know what's already covered
3. Per-column rules:
   - `_id` / `_sk` suffix → `not_null` + `unique` (if candidate key) or `not_null` + `relationships` (FK, parent from `depends_on`)
   - `_date` / `_at` / `_on` suffix → `not_null` where appropriate, `expect_column_values_to_be_between` for date ranges
   - Low cardinality categorical → `accepted_values` with observed values
   - Numeric measure → `expect_column_values_to_be_between` with observed min/max
4. Diff suggested vs existing — output only what's missing
5. Cite `dbt_project_standards.json` rule ID for each suggestion

Output: Copy-pasteable YAML with comments explaining each suggestion and the standard it satisfies. Already-tested columns noted as passing.

**`integration_scaffold.py`** — Generate Integration Model Skeleton

Input: CDM entity name, source model names, primary key column.
Process:
1. Load CDM entity column catalog from seeds
2. Load source models' column lists from manifest
3. Generate SQL skeleton: surrogate key, CDM column mapping with inline comments, source-specific columns separated, union-ready CTE structure, `TODO` comments on unmapped columns
4. Generate YAML snippet: grain description, CDM entity in `meta:`, core tests, contract placeholder

Output: SQL file + YAML snippet saved to `tmp/scaffold/`. Also called by `new_model.py` after intake questionnaire (integration branch).

**`mart_scaffold.py`** — Generate Fact/Dimension/Report Model Skeletons

Called by `new_model.py` after the mart branch intake, or directly:

```bash
python -m scripts.scaffold fact --name fct_permits \
  --grain "one row per permit application" \
  --dimensions dim_parks dim_customers dim_date \
  --measures "permit_fee, processing_days"

python -m scripts.scaffold dimension --name dim_applicants \
  --grain "one row per applicant organization" \
  --key applicant_id

python -m scripts.scaffold report --name rpt_park_revenue_summary \
  --facts fct_reservations fct_pos_transactions \
  --grain "one row per park per month"
```

**Fact skeleton features:**
- Surrogate key FKs to specified dimensions (e.g., `parks_sk`, `customer_sk`, `date_key`)
- Measures only in the SELECT — no descriptive attribute columns
- CTE structure: one CTE per source, one for joins, one final SELECT
- YAML with contract enforced, dimension relationship tests, grain description
- Comment block at top: "This fact captures [grain]. Descriptive attributes come from dimensions, not from this table."

**Dimension skeleton features:**
- Surrogate key generation via `dbt_utils.generate_surrogate_key()`
- Descriptive attribute columns with TODO placeholders
- Derived classification stubs (e.g., `-- TODO: CASE WHEN ... END as size_tier`)
- YAML with contract enforced, unique/not_null on SK

**Report skeleton features:**
- One CTE per source fact with aggregation to the target grain
- Final CTE joins the aggregated facts
- YAML with grain description, note explaining why this report exists (multi-fact or grain change)
- Comment: "This report combines [N] fact tables at the [grain] grain. If consuming a single fact without aggregation, consider connecting your BI tool directly."

### Phase 4: `preflight/` — Analyst Self-Check

**CLI:**
```bash
python -m scripts.preflight --select int_grant_applications
```

**Process (sequential, short-circuits on critical failure):**
1. Compiles? — `dbt compile --select <model>`
2. Builds? — `dbt build --select <model>` (model + tests)
3. Grain — calls `grain/key_discovery`. Is PK unique and tested?
4. Join cardinality — calls `grain/join_analysis`. Any fan-outs?
5. **Layer-specific lint:**
   - If `int_` model → calls `grain/integration_lint` (single-source, no SK, pass-through, no CDM)
   - If `fct_` model → calls `grain/mart_lint` fact checks (wide fact, no dim joins, embedded dims, duplicate grain, missing date dim)
   - If `dim_` model → calls `grain/mart_lint` dimension checks (not referenced, duplicate entity, missing SK)
   - If `rpt_` model → calls `grain/mart_lint` report checks (single-fact pass-through, no aggregation, grain same as source)
   - If `stg_` or `base_` model → no layer-specific lint (staging correctness is covered by steps 1-4 and existing sqlfluff/dbt tests; a staging linter may be added in future iterations)
6. Test coverage — calls `scaffold/test_scaffold` in dry-run/count mode. How many suggested tests missing?
7. YAML/SQL alignment — columns in SQL output vs columns in YAML, flag mismatches

Output: Pass/fail with warnings. Warnings don't block. Each warning links to the command that fixes it.

**VS Code task:**
```jsonc
{
  "label": "Preflight: Current Model",
  "type": "shell",
  "command": "python -m scripts.preflight --select ${input:modelName}",
  "group": "test"
}
```

### Phase 5: `reviewer/` — Connor's Review Tooling

**CLI:**
```bash
python -m scripts.reviewer --select int_grant_applications
python -m scripts.reviewer --branch feature/grant-models
python -m scripts.reviewer summarize --input tmp/reviews/
```

Consolidates `check_model.py` → `automated.py`, `review_model.py` → `qualitative.py`, `summarize_reviews.py` → `summarize.py`.

New `--branch` mode: uses `git diff main..HEAD --name-only` to find changed SQL/YAML, maps to model names, runs full check suite on each, produces consolidated report suitable for PR comment.

### Phase 6: `profiler/` — Performance Fix and `_core/` Integration

**Two-tier profiling:**

| Mode | When | Method | Speed |
|---|---|---|---|
| Quick (default) | All tables | SQL queries in warehouse: `COUNT DISTINCT`, null rates, min/max, avg, top-N values. No ydata-profiling. | Seconds |
| Deep (`--full-profile`) | On request | Current ydata-profiling path with `--sample` cap | Minutes |

Quick mode produces the same output structure renderers consume, populated via SQL instead of pandas. For BigQuery users, analytical queries run in the warehouse — no data transfer. Grain information (candidate keys) appears at the top of every profile output.

After this phase, the profiler:
- Imports connectors and renderers from `_core/` instead of its own copies
- Delegates selector resolution to `_core/selector.py`
- Adds `llm` as a fourth output mode
- The profiler's local `connectors/` and `renderers/` directories are removed

## New Dependencies

| Package | Used By | Purpose | Version Strategy |
|---|---|---|---|
| `sqlglot` | `grain/join_analysis.py` | SQL AST parsing for join extraction | `sqlglot` is NOT a transitive dependency of dbt-core in the current venv (verified). Add as explicit dependency: `sqlglot>=20.0` with no upper pin. If a future dbt-core version bundles sqlglot, test for compatibility before upgrading dbt. |
| `questionary` | `llm_context/new_model.py` | Interactive questionnaire | Already in requirements.txt |

No other new dependencies. All other packages (`rich`, `pandas`, `duckdb`, `dbt-core`, `ydata-profiling`) are already present.

## New Seed Files

| File | Purpose |
|---|---|
| `seeds/cdm_catalogs/cdm_concept_synonyms.csv` | Maps business concepts to CDM entity names with confidence notes. Version-controlled, manually curated, extensible by the team. |
| `seeds/cdm_catalogs/entity_catalog.csv` | CDM entity-level descriptions (name, description, manifest). Prerequisite for Tier 2 entity matching. Falls back to column-aggregation if absent. |

## VS Code Integration

`.vscode/tasks.json` provides button-click access to key commands:
- Preflight: Current Model
- Profile: Source Table
- New Model: Guided Intake
- Grain Check: Current Model

## Migration Details

### Phase 0: `_core/` Extraction

1. Create `scripts/_core/` directory structure
2. Copy `profiler/connectors/base.py`, `duckdb.py`, `bigquery.py` to `_core/connectors/`
3. **Add `run_query(sql: str) -> pd.DataFrame` abstract method to `BaseConnector`; implement in both `DuckDBConnector` and `BigQueryConnector`**
4. Copy `profiler/renderers/terminal.py`, `markdown.py`, `html.py` to `_core/renderers/`
5. Create `_core/renderers/llm.py`
6. Move `SelectionTarget`, `ColumnDef` to `_core/models.py`
7. Create `_core/selector.py` (extracted from profiler's `selector.py`)
8. Create `_core/config.py`
9. Update profiler imports to use `_core/` — profiler's local copies remain as thin wrappers until phase 6 full refactor

### Phases 1-4: New Packages

Built in order. Each phase produces a working sub-package with its own `cli.py`, tests, and documentation.

### Phase 5: Reviewer Migration

Move `check_model.py` → `reviewer/automated.py`, `review_model.py` → `reviewer/qualitative.py`, `summarize_reviews.py` → `reviewer/summarize.py`. Update imports. Add `--branch` mode.

### Phase 6: Profiler Refactor

Complete the profiler's migration to `_core/`. Remove profiler's local `connectors/` and `renderers/`. Add quick-mode SQL-based profiling. Add `llm` output mode.

### Phase 7: Remaining Scripts

Move `search_cdm.py` → `cdm/search.py`, `export_mart_data.py` → `export/cli.py`, `inspect_source.py` → `inspect/cli.py`, `parse_standards.py` → `governance/parse_standards.py`, `dbt_score_rules.py` → `governance/dbt_score_rules.py`. Remove flat scripts from `scripts/` root. Add VS Code tasks.
