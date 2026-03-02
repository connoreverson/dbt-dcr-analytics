---
description: Build Integration
---

# 03: Build Integration

// turbo-all

## Prerequisites
- Workflow 02 complete (staging models passing)

## Steps
1. Run skill `using-dbt-for-analytics-engineering` for integration layer
   - Selector: `integration.*`
   - This step involves authoring SQL and YAML — do NOT auto-run. Present
     the generated files to the user for review before proceeding.

2. Enumerate integration models using dbt ls (safe, read-only)
   - Command: `dbt ls --select integration.* --resource-types model --output name`
   - Capture the output model names. Use this list — not glob or filesystem
     scanning — for all subsequent per-model steps. This is the canonical
     source of model names.

3. Run skill `linting-and-governance-verification`
   - Scope: full-layer sweep (`models/integration`)
   - Use the 3-tool sequence (sqlfluff → dbt-score → dbt-project-evaluator)
   - Note: Do NOT run `check_model.py` across multiple models using a wildcard selector like `integration.*`. The script performs separate dbt invocations per model checks, which is extremely slow due to repeated boot overhead. Only use `check_model.py` for single-model iterations.

4. If CDM validation fails (SQL-INT-03 or SQL-INT-05):
   - Run skill `cdm-exception-request`

5. Gate: all linting and governance checks pass before continuing.

6. Request Qualitative Peer Review (Principle 9)
   - For each model name from the `dbt ls` output in Step 2, run:
     `python scripts/review_model.py --select <model_name> --agent`
   - Do NOT use `glob`, filesystem scanning, or $() substitution to find
     model names — use only the Step 2 dbt ls output.
   - Collect all generated `tmp/review_<model_name>.md` files, compile the
     findings, and present them to the user for final approval.