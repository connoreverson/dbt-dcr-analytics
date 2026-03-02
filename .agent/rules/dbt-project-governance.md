---
activation: always_on
description: Governance constraints for the dbt analytical layer. Applied when planning, building, or reviewing dbt models, tests, seeds, and YAML files.
---

# dbt Project Governance

## Authoritative Documents

All dbt work must comply with two documents:

1. **`reference/dbt_project_standards.md`** — 103 rules covering naming, formatting, CTE design, testing, documentation, DAG hygiene, and layer-specific requirements. These rules are enforceable and verifiable.
2. **`reference/SPEC_vertical_slice_revenue.md`** — The implementation specification for the current vertical slice. Defines scope, layer-by-layer deliverables, CDM mappings, seeds, macros, tests, and success criteria.

When a decision is ambiguous, check the Standards first, then the SPEC, then ask the user.

## Layer Discipline

Models must follow the unidirectional flow: sources > staging (+ base) > integration > marts. Never skip layers. Never reference downstream.

| Layer | Prefix | Materialization | Schema |
|---|---|---|---|
| Staging | `stg_` | view | `staging` |
| Base | `base_` | view | `staging` |
| Integration | `int_` | table | `integration` |
| Fact | `fct_` | table | `marts_revenue` |
| Dimension | `dim_` | table | `marts_revenue` |
| Report | `rpt_` | table | `marts_revenue` |

## Naming Conventions

- File names: `{prefix}_{source}__{entity}.sql` (double underscore between source and entity)
- Plural phrasing: `stg_vistareserve__reservations` not `reservation`
- YAML property files: leading underscore (`_sources.yml`, `_models.yml`, `_seeds.yml`)
- No abbreviations under 20 characters

## Testing Requirements

- Every model must have at least one test per column that is a primary key, foreign key, or business-critical field
- Staging models: `unique` and `not_null` on surrogate keys; `accepted_values` on status/type columns
- Integration models: referential integrity tests to staging parents; row count tests via dbt_expectations
- Mart models: `unique` and `not_null` on dimension PKs; aggregation balance tests on facts

## Documentation Requirements

- Every model must have a `description` in its `_models.yml`
- Every column in staging and above must have a `description`
- Source tables must have `description` and `loaded_at_field` where applicable

### What Descriptions Must Contain

**Model descriptions** must answer three questions: (1) What business entity does this represent? (2) What is the grain — what does one row mean? (3) Where does the data come from?

**Column descriptions** must explain the business meaning of the column. For renamed or derived columns, briefly note the origin (e.g., "Park acreage as reported by GeoParks"). For foreign keys, name the target entity (e.g., "Reference to the park in int_parks").

### What Descriptions Must NOT Contain

Descriptions must never restate what tests do. Phrases like "Tests verify that the primary key is unique" or "protecting against fan-out" are test rationale, not data documentation. Anyone reading the YAML can see the tests — they do not need a prose restatement.

**Test rationale** belongs in a `meta:` block on the model or as an inline SQL comment in the model file. See ALL-TST-02 in `reference/dbt_project_standards.md`.

### Quick Self-Check

Before saving a `_models.yml` file, scan every description for these red-flag words: `unique`, `not_null`, `fan-out`, `deduplication`, `protecting against`, `tests verify`, `collision`. If any appear, move that sentence to a `meta: testing_rationale:` block.

## CDM Conformance

Integration models must map to Microsoft Common Data Model entities. The SPEC defines the mapping:

| Integration Model | CDM Entity |
|---|---|
| `int_parks` | Park (custom — see `reference/CDM_EXCEPTION_int_parks.md`) |
| `int_contacts` | Contact |
| `int_customer_assets` | CustomerAsset |
| `int_transactions` | Transaction |
| `int_reservations` | Visit |

Column names in integration models should align with CDM field names where practical, with deviations documented in the model's YAML description.

If no standard CDM entity provides both semantic correctness and adequate column coverage, file a `CDM_EXCEPTION_<model>.md` in `reference/` following the template established by `CDM_EXCEPTION_int_parks.md`. The custom entity must be cataloged in `seeds/cdm_catalogs/` and registered in `seeds/cdm_crosswalk.csv`. See the `cdm-exception-request` skill for the full process.

## Linting

> For per-model verification during development, run `python scripts/check_model.py --select <model_name>`. This consolidates sqlfluff, dbt build, dbt-score, and dbt-project-evaluator checks into a single command with a unified pass/fail summary.

- sqlfluff must pass on all SQL files before a model is considered complete
- dbt-score must meet minimum thresholds defined in the project configuration
- dbt-project-evaluator must report zero violations for naming and DAG rules

## Integration Model Discipline

Integration models are NOT rename-only passthroughs. If an integration model only renames columns from a single staging source, it is wrong. Every integration model must perform at least one of:

- **Union** data across multiple source systems (SQL-INT-08)
- **Join** to enrich records with data from other staging models (SQL-INT-10)
- **Deduplicate/harmonize** records from multiple sources (SQL-INT-11)
- **Generate a surrogate key** named `<entity>_sk` using `dbt_utils.generate_surrogate_key()` (SQL-INT-06)

If the model consumes only one staging source and the spec says it should consume multiple, consume all specified sources. If the spec identifies foreign key relationships (e.g., int_reservations should include FKs to int_contacts and int_customer_assets), implement those joins.

Before writing an integration model, re-read the SPEC's entry for that model to confirm: (1) which staging sources it consumes, (2) what transformations it performs, (3) what its output grain is, and (4) which CDM entity it maps to.

## Seed Naming and Completeness

- All seed filenames must be snake_case per ALL-FMT-05. Never use camelCase or mixed case (e.g., `column_catalog_asset.csv`, not `column_catalog_Asset.csv`).
- Before moving to the next phase, verify that all seeds listed in the SPEC are present. The SPEC defines specific required seeds — they are deliverables, not optional.
- Every seed must have a `_seeds.yml` entry with descriptions and data type overrides per SQL-SEED-05.

## Macro Completeness and Usage

- Before moving to the next phase, verify that all macros listed in the SPEC are present.
- If the user provides a macro (e.g., `generate_staging_model.sql`), use it. Do not create a parallel mechanism.
- Every macro must have a `_macros.yml` entry per MAC-YML-01/02/03.
- Every macro must validate its arguments per SQL-MAC-03.
- If a macro exists but is not called by any model, either wire it into the models or remove it. Orphaned macros are dead code.

## CDM Entity Mapping Compliance

- The SPEC defines which CDM entity each integration model maps to. Do not substitute a different CDM entity without explicit user approval and documented rationale.
- If the CDM catalog seeds do not contain the expected entity columns, flag this to the user rather than silently choosing a different entity.
- CDM column mappings must be semantically correct — do not map unrelated fields (e.g., `total_acres` to `yomi_name`) to satisfy column count requirements.

## YAML/SQL Consistency

Before saving a `_models.yml` file, verify that every column documented in the YAML actually exists in the model's SQL output. A YAML column that the SQL does not produce will cause contract errors and misleads readers.

## Qualitative Code Review (The 53%)

Because 53% of the dbt Project Standards govern *intent* and *semantics* (meaningful names, substantive descriptions, appropriate business logic tests), linters are insufficient. You must bridge this gap via two mechanisms:

1. **Pre-commit Self-Reflection:** Before saving a model or YAML file, explicitly evaluate whether your descriptions are substantive (not just restating the column name) and whether your tests cover the highest-risk business logic.
2. **Layer-Boundary Peer Reviews:** At the conclusion of the Staging, Integration, and Marts phases, you must pause execution and present the layer to the user for a qualitative code review. Do not proceed to the next layer until the user approves the semantics and logic of the current layer.

## Mart Model Pre-Flight Checklist

Before writing any mart model (fact, dimension, or report), complete these steps in order:

1. **Inspect upstream outputs.** Run `dbt show --select <integration_model> --limit 1` for every integration model the mart will consume. Record the actual column names.
2. **Check the SPEC entry.** Re-read the SPEC's section for the mart model. Confirm: required measures (facts), required enrichments (dimensions), required aggregations (reports), required dimension keys (facts).
3. **Write SQL against observed columns.** Use the column names from step 1, not guessed names. If an integration model column has a CDM name (e.g., `msnfp_amount_receipt`), rename it in the mart SQL — do not assume the integration model already renamed it.
4. **Write YAML in lockstep.** After each model's SQL is complete, write its YAML entry immediately. Compare column lists side by side before proceeding to the next model.
5. **Layer discipline check.** Verify every `ref()` in the SQL: facts and dimensions must consume integration models (or seeds for label enrichment). Reports must consume facts and dimensions. No model may reference staging directly.
6. **Forbidden patterns check.** Scan the SQL for: bare `union` (must be `union all`), `select distinct` (must not appear), subqueries (must be CTEs), single-letter aliases, `ref()` calls outside import CTEs.
7. **Description quality check.** Read every `description` in the YAML. If any mention `unique`, `not_null`, `fan-out`, `deduplication`, `tests verify`, or `protecting against`, move that text to `meta: testing_rationale:`.
8. **Test coverage check.** Verify: PK uniqueness + not_null on every model, FK `relationships` tests on every dimension key in facts, `meta: testing_rationale:` on every model, volumetric `dbt_expectations` tests on fact models.

## Spec Compliance Checklist

Before declaring any phase complete, verify against the SPEC:

1. **All deliverables present** — every model, seed, macro, test, and YAML file the SPEC lists for that phase exists
2. **All inputs consumed** — if the SPEC says a model consumes multiple staging sources, all are consumed
3. **All transformations applied** — surrogate keys generated, unions performed, joins completed, deduplication done
4. **All tests defined** — PK tests, FK relationship tests, business logic constraints, volumetric tests as specified
5. **CDM entity mapping matches** — the CDM entity and column mappings match the SPEC's mapping table
6. **No orphaned artifacts** — no unused macros, no duplicate YAML entries, no YAML/SQL mismatches

## Dependency Management

- **`requirements.txt` is read-only.** Do not add, remove, or modify packages in `requirements.txt`. If a new dependency is needed, ask the user.
- **Package installation is scoped.** Only run `pip install -r requirements.txt` to install dependencies. Never run `pip install <package>` directly — this prevents unvetted packages from entering the environment.
