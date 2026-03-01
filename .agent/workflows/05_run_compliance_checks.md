---
description: Run Compliance Checks
---

# 05: Run Compliance Checks

// turbo-all

## Prerequisites
- Workflows 02–04 complete (all layers built)

## Steps
1. Run skill `linting-and-governance-verification` at project scope
   - This runs the full 3-tool sequence across all models:
     sqlfluff fix + lint → dbt-score lint → dbt-project-evaluator build
   - Use this for project-wide sweeps; check_model.py is for
     single-model iteration during development
2. Review any WARN-level items from dbt-project-evaluator
   (especially fct_model_directories Windows false positives)
3. Gate: zero FAIL across all three tools
