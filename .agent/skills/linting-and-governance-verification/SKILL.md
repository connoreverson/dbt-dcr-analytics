---
name: linting-and-governance-verification
description: Use when running Phase 7 governance verification — sqlfluff lint, dbt-score, and dbt-project-evaluator. Covers the correct command sequence, Windows-specific workarounds, acceptable violation patterns, and remediation workflows. Recurs with every vertical slice.
user-invocable: false
metadata:
  author: dcr-analytics
---

# Linting and Governance Verification

Runs three governance tools in sequence. Each has Windows-specific behaviors documented here.

There are two verification paths depending on the scope of work:

- **Single-model checks (during development):** `python scripts/check_model.py --select <model_name>` — this runs sqlfluff, dbt build, dbt-score, and dbt-project-evaluator checks internally. Use this when iterating on a specific model. It replaces running the three tools separately for per-model work.
- **Qualitative Code Review (during development):** `python scripts/review_model.py --select <model_name> --agent` — this fetches the automated results from `check_model.py` and generates a checklist template in `tmp/review_<model_name>.md` containing the qualitative/manual rules that linters cannot check. LLMs MUST run this, read the template, and fill it out. Humans can run without the `--agent` flag for an interactive prompt.
- **Full-project sweeps (phase gates):** The existing 3-tool sequence (sqlfluff fix+lint → dbt-score lint → dbt-project-evaluator build) remains the correct approach for validating all models at once, since `check_model.py` is model-scoped. Always run in this order: **sqlfluff → dbt-score → dbt-project-evaluator**.

**Auto-Run Policy:** All linting and governance tools (`sqlfluff`, `dbt-score`, `dbt-project-evaluator`) are completely safe and MUST be auto-run using `SafeToAutoRun: true` (or the equivalent automation flag). Do not stop to ask the user for permission to execute these commands. Collect all output and present the findings at the end.

## 1. sqlfluff

### Workflow

Always run `fix` before `lint`. Most violations are auto-remediable; `lint` after `fix` shows only the residuals you must address manually.

**Scope to the layer under review.** Phase-gate linting must target only the layer being gated — not `models/` (the whole project). Using `models/` during a staging or integration phase gate surfaces pre-existing violations from other layers and creates noise that makes it unclear whether the current phase is actually clean.

```bash
# Phase 1 gate (staging)
sqlfluff fix models/staging/ --dialect duckdb --templater dbt
sqlfluff lint models/staging/ --dialect duckdb --templater dbt

# Phase 2 gate (integration)
sqlfluff fix models/integration/ --dialect duckdb --templater dbt
sqlfluff lint models/integration/ --dialect duckdb --templater dbt

# Phase 3 gate (marts)
sqlfluff fix models/marts/ --dialect duckdb --templater dbt
sqlfluff lint models/marts/ --dialect duckdb --templater dbt

# Phase 4 final sweep only — use full project scope
sqlfluff fix models/ --dialect duckdb --templater dbt
sqlfluff lint models/ --dialect duckdb --templater dbt
```

### Common Unfixable Violations

| Rule | Cause | Fix |
|------|-------|-----|
| RF04 | CDM field name collides with SQL keyword (e.g., `name`) | Add `-- noqa: RF04` inline suppression on the offending line |
| LT05 | Comment line over 80 chars — sqlfluff does not rewrap comments | Manually rewrap the comment block so every line is ≤80 chars |

### RF04 Example

```sql
source_assets.asset_id as name,  -- noqa: RF04
```

### LT05 Example — Rewrapping

Wrong (line over 80 chars):
```sql
-- GeoParks is designated the system of record, so its attributes win in the event of a tie.
```

Correct (rewrapped):
```sql
-- GeoParks is designated the system of record, so its attributes win
-- in the event of a tie.
```

For multi-line block comments, rewrap the entire block:
```sql
/*
    Open Question #1: Park ID Reconciliation
    Due to the lack of a unified crosswalk ID between GeoParks and
    VistaReserve, we are heuristically deduplicating based on fuzzy
    string matching of the park names (stripping punctuation/casing).
    GeoParks is designated the system of record, so its attributes win
    in the event of a tie.
*/
```

---

## 2. dbt-score

### Correct Command (v0.6.0)

The command is `dbt-score lint`. The `score` subcommand does not exist in v0.6.0.

```bash
# Standard run (may fail with UnicodeEncodeError on Windows — see below)
dbt-score lint

# Windows workaround: dbt-score outputs emoji badges that cp1252 cannot encode
PYTHONIOENCODING=utf-8 python -m dbt_score lint
```

### Windows UnicodeEncodeError

**Symptom:** `UnicodeEncodeError: 'charmap' codec can't encode character '\U0001f4cb'`

**Root cause:** dbt-score outputs emoji badge characters. The Windows terminal uses cp1252 encoding, which cannot represent emoji.

**Fix:** Force UTF-8 output encoding:
```bash
PYTHONIOENCODING=utf-8 python -m dbt_score lint
```

This is a terminal encoding limitation, not a configuration error. Do not attempt to configure dbt-score to suppress emoji — the env var workaround is the correct fix.

### pyproject.toml Configuration (v0.6.0 Format)

Flat option names like `rule_severity_has_description` are silently ignored in v0.6.0. Use table block syntax:

```toml
[tool.dbt-score]
fail_any_model_under = 5.0

[tool.dbt-score.rules."dbt_score.rules.generic.has_description"]
severity = 3

[tool.dbt-score.rules."dbt_score.rules.generic.columns_have_description"]
severity = 3

[tool.dbt-score.rules."dbt_score.rules.generic.has_owner"]
severity = 1
```

If dbt-score silently ignores your severity settings, the pyproject.toml format is wrong — verify against the table block format above.

---

## 3. dbt-project-evaluator

### Running

```bash
dbt build --select package:dbt_project_evaluator --quiet
```

### Windows Path Separator False Positives

**Symptom:** `fct_model_directories` and `fct_source_directories` report rows with empty `child_directory_path` for all staging models and sources.

**Root cause:** `get_directory_pattern()` detects the OS via the `HOME` environment variable. On Windows + Git Bash, `HOME` is set to a Unix-style path (e.g., `/c/Users/user`) with no backslashes, so the macro returns `/` as the path separator. But the dbt manifest stores paths using `\` (Windows backslashes). This mismatch leaves `child_directory_path` empty, triggering false directory violations for all staging models and sources.

Diagnose with:
```bash
dbt show --inline "select resource_name, child_directory_path from {{ ref('fct_model_directories') }}" --limit 20
```

**Fix:** Add exceptions to `seeds/dbt_project_evaluator_exceptions.csv`:

```csv
fct_name,column_name,id_to_exclude,comment
fct_model_directories,resource_name,stg_vistareserve%,Windows path separator false positive: Git Bash HOME uses / but manifest uses \ causing empty directory_path extraction
fct_model_directories,resource_name,stg_geoparks%,Windows path separator false positive: Git Bash HOME uses / but manifest uses \ causing empty directory_path extraction
fct_source_directories,resource_name,vistareserve%,Windows path separator false positive: Git Bash HOME uses / but manifest uses \ causing empty directory_path extraction
fct_source_directories,resource_name,geoparks%,Windows path separator false positive: Git Bash HOME uses / but manifest uses \ causing empty directory_path extraction
```

Then disable the package's default empty exceptions seed in `dbt_project.yml`:

```yaml
seeds:
  dbt_project_evaluator:
    dbt_project_evaluator_exceptions:
      +enabled: false
```

**Do NOT** add a YAML entry for `dbt_project_evaluator_exceptions` in `_seeds.yml` — the package already defines it, and a second schema.yml entry causes a compile error.

### base_ Model Type Recognition

**Symptom:** `fct_model_naming_conventions` warns about `base_` models being classified as `other` type.

**Fix:** Add `base` to the `model_types` var in `dbt_project.yml`:

```yaml
vars:
  model_types: ['staging', 'intermediate', 'marts', 'other', 'base']
  base_prefixes: ['base_']
  base_folder_name: 'staging'
```

### Diagnosing Failures

To inspect what dbt-project-evaluator is seeing, query its output tables directly:

```bash
# Check directory path extraction
dbt show --inline "select resource_name, child_directory_path from {{ ref('fct_model_directories') }}" --limit 20

# Check DAG relationships
dbt show --inline "select * from {{ ref('int_all_dag_relationships') }} limit 5"

# See all violations in a specific fact table
dbt show --inline "select * from {{ ref('fct_model_naming_conventions') }}"
```

---

## Acceptance Criteria

A phase is complete when all three tools pass cleanly:

| Tool | Pass condition |
|------|----------------|
| `check_model.py` (per-model) | Exit code 0, zero FAIL results in summary |
| `sqlfluff lint` | Zero violations reported |
| `dbt-score lint` | All models ≥ configured threshold (default `fail_any_model_under = 5.0`) |
| `dbt build --select package:dbt_project_evaluator` | Completes with 0 warnings and 0 errors |
