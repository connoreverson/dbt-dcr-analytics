---
name: running-dbt-commands
description: Use when executing dbt commands via CLI - running models, tests, builds, compiles, or show queries. Use when unsure which dbt executable to use or how to format command parameters.
user-invocable: false
metadata:
  author: dbt-labs
---

# Running dbt Commands

## Preferences

1. **Use MCP tools if available** (`dbt_build`, `dbt_run`, `dbt_show`, etc.) - they handle paths, timeouts, and formatting automatically
2. **Use `build` instead of `run` or `test`** - `test` doesn't refresh the model, so testing a model change requires `build`. `build` does a `run` and a `test` of each node (model, seed, snapshot) in the order of the DAG
3. **Always use `--quiet`** with `--warn-error-options '{"error": ["NoNodesForSelectionCriteria"]}'` to reduce output while catching selector typos
4. **Always use `--select`** - never run the entire project without explicit user approval

## Virtual Environment Activation (Shell-Aware)

This project runs in **Git Bash** (`/usr/bin/bash`). Activate the venv with:

```bash
source .venv/Scripts/activate
```

If running in PowerShell (not this project's default), use dot-sourcing instead:

```powershell
. .\.venv\Scripts\Activate.ps1; dbt build --select my_model
```

Do NOT use any of these alternatives — they have all failed in practice:
- `& .\.venv\Scripts\Activate.ps1` (call operator — drops env vars)
- `.venv\Scripts\dbt.exe` (direct invocation — missing PATH context)
- `$env:PATH += ...` (PATH manipulation — unreliable)
- Using the `.ps1` form in Git Bash — Bash strips backslashes; fails silently if dbt is already on PATH

For `dbt init`, always use `--skip-profile-setup` (not `--no-interactive`, which does not exist).

## Quick Reference

```bash
# Standard command pattern
dbt build --select my_model --quiet --warn-error-options '{"error": ["NoNodesForSelectionCriteria"]}'

# Preview model output
dbt show --select my_model --limit 10

# Run inline SQL query
dbt show --inline "select * from {{ ref('orders') }}" --limit 5

# With variables (JSON format for multiple)
dbt build --select my_model --vars '{"key": "value"}'

# Full refresh for incremental models
dbt build --select my_model --full-refresh

# List resources before running
dbt list --select my_model+ --resource-type model
```

## dbt CLI Flavors

Three CLIs exist. **Ask the user which one if unsure.**

| Flavor | Location | Notes |
|--------|----------|-------|
| **dbt Core** | Python venv | `pip show dbt-core` or `uv pip show dbt-core` |
| **dbt Fusion** | `~/.local/bin/dbt` or `dbtf` | Faster and has stronger SQL comprehension |
| **dbt Cloud CLI** | `~/.local/bin/dbt` | Go-based, runs on platform |

**Common setup:** Core in venv + Fusion at `~/.local/bin`. Running `dbt` uses Core. Use `dbtf` or `~/.local/bin/dbt` for Fusion.

## Selectors

**Always provide a selector.** Graph operators:

| Operator | Meaning | Example |
|----------|---------|---------|
| `model+` | Model and all downstream | `stg_orders+` |
| `+model` | Model and all upstream | `+dim_customers` |
| `+model+` | Both directions | `+orders+` |
| `model+N` | Model and N levels downstream | `stg_orders+1` |

```bash
--select my_model              # Single model
--select staging.*             # Path pattern
--select fqn:*stg_*            # FQN pattern
--select model_a model_b       # Union (space)
--select tag:x,config.mat:y    # Intersection (comma)
--exclude my_model             # Exclude from selection
```

**Resource type filter:**
```bash
--resource-type model
--resource-type test --resource-type unit_test
```

Valid types: `model`, `test`, `unit_test`, `snapshot`, `seed`, `source`, `exposure`, `metric`, `semantic_model`, `saved_query`, `analysis`

## List

Use `dbt list` to preview what will be selected before running. Helpful for validating complex selectors.

```bash
dbt list --select my_model+              # Preview selection
dbt list --select my_model+ --resource-type model  # Only models
dbt list --output json                   # JSON output
dbt list --select my_model --output json --output-keys unique_id name resource_type config
```

**Available output keys for `--output json`:**
`unique_id`, `name`, `resource_type`, `package_name`, `original_file_path`, `path`, `alias`, `description`, `columns`, `meta`, `tags`, `config`, `depends_on`, `patch_path`, `schema`, `database`, `relation_name`, `raw_code`, `compiled_code`, `language`, `docs`, `group`, `access`, `version`, `fqn`, `refs`, `sources`, `metrics`

## Show

Preview data with `dbt show`. Use `--inline` for arbitrary SQL queries.

```bash
dbt show --select my_model --limit 10
dbt show --inline "select * from {{ ref('orders') }} where status = 'pending'" --limit 5
```

**Important:** Use `--limit` flag, not SQL `LIMIT` clause.

## Variables

Pass as STRING, not dict. No special characters (`\`, `\n`).

```bash
--vars 'my_var: value'                              # Single
--vars '{"k1": "v1", "k2": 42, "k3": true}'         # Multiple (JSON)
```

## Analyzing Run Results

After a dbt command, check `target/run_results.json` for detailed execution info:

```bash
# Quick status check
cat target/run_results.json | jq '.results[] | {node: .unique_id, status: .status, time: .execution_time}'

# Find failures
cat target/run_results.json | jq '.results[] | select(.status != "success")'
```

**Key fields:**
- `status`: success, error, fail, skipped, warn
- `execution_time`: seconds spent executing
- `compiled_code`: rendered SQL
- `adapter_response`: database metadata (rows affected, bytes processed)

## Defer (Skip Upstream Builds)

Reference production data instead of building upstream models:

```bash
dbt build --select my_model --defer --state prod-artifacts
```

**Flags:**
- `--defer` - enable deferral to state manifest
- `--state <path>` - path to manifest from previous run (e.g., production artifacts)
- `--favor-state` - prefer node definitions from state even if they exist locally

```bash
dbt build --select my_model --defer --state prod-artifacts --favor-state
```

## Static Analysis (Fusion Only)

Override SQL analysis for models with dynamic SQL or unrecognized UDFs:

```bash
dbt run --static-analysis=off
dbt run --static-analysis=unsafe
```

## Redirecting dbt Output on Windows

dbt output sometimes contains characters the terminal cannot display. When you need to capture output for debugging:

```bash
# Git Bash: redirect to file
dbt build --select my_model > tmp/output.txt 2>&1
```

```powershell
# PowerShell: redirect and re-encode to UTF-8
. .\.venv\Scripts\Activate.ps1; dbt build --select my_model > tmp_output.txt; Get-Content tmp_output.txt | Out-File -Encoding utf8 tmp_output_utf8.txt
```

Always clean up tmp files when done.

## Seed Operations

- When copying CSV files from external directories into `seeds/`, verify the filenames are snake_case before running `dbt seed`
- Use `dbt seed --full-refresh` after renaming seed files or changing column types to force a clean reload
- If `dbt seed` fails on a large CSV, check for BOM markers (UTF-8-sig encoding) — DuckDB handles these but error messages may be misleading
- After renaming seed files, update all `ref()` calls and `dbt_project.yml` column type overrides to match the new names

## Inspecting Upstream Models Before Writing Downstream

Before writing a mart model that consumes an integration model, always inspect the integration model's actual output first. This prevents column name mismatches and contract errors.

```bash
# Inspect column names and sample data from an integration model
dbt show --select int_parks --limit 1

# Inspect multiple upstream models in JSON for easier column name extraction
dbt show --select int_contacts --limit 1 --output json
```

**Do NOT use Python one-liners** (`python -c "import duckdb; ..."`) to inspect model schemas. Use `dbt show` — it runs the model through dbt's compilation and gives you the actual output columns. If you need source table schemas, use the `codegen` package's `generate_source` or `generate_base_model` macros.

**Do NOT guess column names** from the SPEC or from integration model SQL. The `generate_cdm_projection` macro may rename columns in ways that differ from the raw staging column names. Always verify with `dbt show`.

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Using `test` after model change | Use `build` - test doesn't refresh the model |
| Running without `--select` | Always specify what to run |
| Using `--quiet` without warn-error | Add `--warn-error-options '{"error": ["NoNodesForSelectionCriteria"]}'` |
| Running `dbt` expecting Fusion when we are in a venv | Use `dbtf` or `~/.local/bin/dbt` |
| Adding LIMIT to SQL in `dbt_show` | Use `limit` parameter instead |
| Vars with special characters | Pass as simple string, no `\` or `\n` |
| Activating venv in Git Bash with `.ps1` syntax | Use `source .venv/Scripts/activate` — Bash cannot execute `.ps1` files; failure is silent if dbt is on PATH |
| Running dbt in PowerShell with `&` operator | Use dot-sourcing: `. .\.venv\Scripts\Activate.ps1; dbt ...` to preserve the PATH |
| Initializing a dbt project programmatically | Use `dbt init <project_name> --skip-profile-setup` to avoid interactive prompts hanging the terminal |
| Retrying the same failing command 3+ times | Stop after 2 failures. Re-read the relevant operating principle or skill doc. If no principle covers the situation, ask the user |
| Using Python scripts to bulk-modify SQL/YAML files | Never open a file for writing before reading all contents into memory. Prefer dbt macros, analysis files, or editor operations instead |
| Creating ad-hoc Python scripts for file generation | Use dbt macros (run-operation) or analysis files. If the user provides a macro, use it — do not create a parallel mechanism |
| Using grep/Python to query CDM metadata | Load CDM metadata as dbt seeds and query via SQL or macros within the dbt framework |
| Using `python -c "import duckdb; ..."` to inspect schemas | Use `dbt show --select <model> --limit 1` instead. It compiles through dbt and shows actual output columns |
| Writing YAML columns without verifying SQL output | Run `dbt show` on the model first, then write YAML columns to match the observed output |

## Governance Tools

For full workflows and Windows-specific workarounds, see `.agent/skills/linting-and-governance-verification/SKILL.md`. Quick reference:

### sqlfluff

```bash
# Run fix first (auto-remediates most violations), then lint to see residuals
sqlfluff fix models/ --dialect duckdb --templater dbt
sqlfluff lint models/ --dialect duckdb --templater dbt
```

Unfixable residuals requiring manual attention: RF04 (keyword identifiers — add `-- noqa: RF04`), LT05 (comment lines over 80 chars — rewrap manually).

### dbt-score

```bash
# Correct command is "lint", not "score" (v0.6.0)
dbt-score lint

# Windows UnicodeEncodeError workaround (emoji output + cp1252 terminal)
PYTHONIOENCODING=utf-8 python -m dbt_score lint
```

### dbt-project-evaluator

```bash
dbt build --select package:dbt_project_evaluator --quiet
```

Windows false positive: on Git Bash, `HOME` has no backslashes, so `get_directory_pattern()` returns `/` while the manifest uses `\`. This empties `child_directory_path` and triggers false directory violations for all staging models/sources. Fix via `seeds/dbt_project_evaluator_exceptions.csv`.
