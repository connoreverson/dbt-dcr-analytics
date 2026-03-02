# Agent Autonomy and Safe Execution

This rule governs how the AI agent should execute CLI commands independently to ensure an efficient, non-blocking workflow.

1. **Default to Auto-Run:** Agents MUST default to `SafeToAutoRun: true` (or the equivalent parameter in your command execution tool) for all routine, non-destructive engineering tasks. This includes:
   - **Routine dbt commands:** `dbt compile`, `dbt show`, `dbt ls`, `dbt build`, and `dbt run` (when scoped to specific models during development).
   - **Python utility scripts:** `python scripts/check_model.py`, `python scripts/review_model.py`, etc.
   - **Linting tools:** `sqlfluff` and `dbt-score`.

2. **No Permission Prompts for Reading:** Never stop your progress to ask the user for permission to run read-only reconnaissance queries (e.g., `dbt show --inline "select * from ..."`). These use minimal compute and are essential for your context. Auto-run them implicitly.

3. **Virtual Environment Enforcement:** Any execution of dbt or python scripts MUST be explicitly prepended with the `.venv` activation command sequence for the active shell (e.g. `source .venv/Scripts/activate; python ...` for bash or `. .\.venv\Scripts\Activate.ps1; python ...` for PowerShell). Do not rely on ambient environment state.
