---
description: Build Source and Staging
---

# 02: Build Source and Staging

// turbo-all

## Prerequisites
- Workflow 01 complete (environment active, seeds loaded)

## Steps
1. Inspect the source data
   - Run `python -m scripts.inspect --type duckdb --conn path/to.duckdb` to understand the table schemas.
   - Run `python -m scripts.inspect --type duckdb --conn path/to.duckdb --table <schema>.<table_name>` to understand specific columns, cardinality, and data quality issues for a given table.
2. Run skill `using-dbt-for-analytics-engineering` for source/staging layer
   - Selector: `models/staging`
2. Run skill `linting-and-governance-verification`
   - Scope: full-project sweep (`models/staging`)
   - Use the 3-tool sequence (sqlfluff → dbt-score → dbt-project-evaluator)
3. Gate: all checks pass before proceeding to Workflow 03
4. Request Qualitative Peer Review (Principle 9)
   - Automatically run `python -m scripts.reviewer --select <model_name> --agent` for each staging model without asking for permission.
   - Present the compiled markdown findings to the user and ask for their final approval.
