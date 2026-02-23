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

## CDM Conformance

Integration models must map to Microsoft Common Data Model entities. The SPEC defines the mapping:

| Integration Model | CDM Entity |
|---|---|
| `int_parks` | FunctionalLocation |
| `int_contacts` | Contact |
| `int_customer_assets` | CustomerAsset |
| `int_transactions` | Transaction |
| `int_reservations` | Visit |

Column names in integration models should align with CDM field names where practical, with deviations documented in the model's YAML description.

## Linting

- sqlfluff must pass on all SQL files before a model is considered complete
- dbt-score must meet minimum thresholds defined in the project configuration
- dbt-project-evaluator must report zero violations for naming and DAG rules

## Qualitative Code Review (The 53%)

Because 53% of the dbt Project Standards govern *intent* and *semantics* (meaningful names, substantive descriptions, appropriate business logic tests), linters are insufficient. You must bridge this gap via two mechanisms:

1. **Pre-commit Self-Reflection:** Before saving a model or YAML file, explicitly evaluate whether your descriptions are substantive (not just restating the column name) and whether your tests cover the highest-risk business logic.
2. **Layer-Boundary Peer Reviews:** At the conclusion of the Staging, Integration, and Marts phases, you must pause execution and present the layer to the user for a qualitative code review. Do not proceed to the next layer until the user approves the semantics and logic of the current layer.
