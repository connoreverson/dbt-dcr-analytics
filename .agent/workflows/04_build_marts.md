---
description: Build Marts
---

# 04: Build Marts

// turbo-all

## Prerequisites
- Workflow 03 complete (integration models passing)

## Steps
1. Run skill `using-dbt-for-analytics-engineering` for marts layer
   - Selector: `models/marts`
2. Run skill `linting-and-governance-verification`
   - Scope: full-layer sweep (`models/marts`)
   - Use the 3-tool sequence (sqlfluff → dbt-score → dbt-project-evaluator)
   - Note: Do NOT run `check_model.py` across multiple models using a wildcard selector. The script performs separate dbt invocations per model checks, which is extremely slow due to repeated boot overhead. Only use `check_model.py` for single-model iterations.
3. Gate: all linting and governance checks pass before continuing.
4. Request Qualitative Peer Review (Principle 9)
   - Automatically run `python scripts/review_model.py --select <model_name> --agent` for each mart model without asking for permission.
   - Present the compiled markdown findings to the user and ask for their final approval.
