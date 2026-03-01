---
description: Build Source and Staging
---

# 02: Build Source and Staging

// turbo

## Prerequisites
- Workflow 01 complete (environment active, seeds loaded)

## Steps
1. Run skill `using-dbt-for-analytics-engineering` for source/staging layer
   - Selector: `models/staging`
2. Run skill `linting-and-governance-verification`
   - Scope: full-project sweep (`models/staging`)
   - Use the 3-tool sequence (sqlfluff → dbt-score → dbt-project-evaluator)
3. Gate: all checks pass before proceeding to Workflow 03
