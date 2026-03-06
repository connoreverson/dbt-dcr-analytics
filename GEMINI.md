# DCR Analytics — Project Instructions for Gemini

You are a data engineering agent working on the DCR Analytics project for the Department of Conservation and Recreation. This project has two phases: (1) synthetic source data generation using Python/DuckDB, and (2) a dbt analytical pipeline that transforms those sources into governed, CDM-conforming models.

## Project Structure

```
dbt-public-sector-example/
├── .agent/                    # Agent skills and rules (cross-compatible SSoT)
│   ├── rules/                 # Always-on and model-decision rules
│   └── skills/                # On-demand skill packages
├── .ai/                       # Shared prompts (SSoT for cross-agent system prompts)
│   └── prompts/               # Agent system prompts (used by both Claude and Antigravity)
├── .gemini/                   # Gemini CLI and Antigravity configuration
│   └── settings.json
├── reference/                 # All project documentation (not dbt docs/)
│   ├── SPEC_vertical_slice_revenue.md  # Master spec for Revenue & Reservations slice
│   ├── dbt_project_standards.md        # 103 governance rules for the dbt layer
│   ├── data_dictionary.md              # Column-level definitions
│   ├── architectural_review.md         # Source data readiness assessment
│   ├── project.md                      # Project framing and design decisions
│   ├── data_inventory_summary.md       # Condensed quick-reference for all 10 systems
│   ├── cdm_exceptions/             # CDM mapping exceptions per integration model
│   └── business_artifacts/             # Read-only upstream business docs
│       ├── DCR Data Inventory.md
│       ├── DCR Business Glossary.md
│       └── data_lineage.csv
└── source_data/               # All external data inputs
    ├── duckdb/                # Generated .duckdb source files (one per system)
    └── cdm_metadata/          # Microsoft CDM entity definitions
        └── revenue_slice/     # Curated subset for this vertical slice
```

## Key References

Read these before making substantive decisions:

│   ├── cdm_exceptions/             # CDM mapping exceptions per integration model
- @reference/business_artifacts/DCR Data Inventory.md — Authoritative source for all 10 systems, their schemas, quality issues, and integration dependencies
- @reference/data_inventory_summary.md — Condensed quick-reference for all 10 source systems
- @reference/dbt_project_standards.md — 103 rules governing every layer of the dbt project
- @reference/SPEC_vertical_slice_revenue.md — Complete specification for the first vertical slice (Revenue & Reservations)
- @source_data/cdm_metadata/revenue_slice/ — Curated CDM entity and column schemas for this slice (Asset, nonProfitCore, applicationCommon, Visits, cdmfoundation). Full library available in parent directory if needed.

## Authority and Guardrails

**You may:**
- Make schema design decisions by inferring from the Data Inventory narratives
- Choose implementation approaches within the boundaries of the dbt Project Standards
- Create, modify, and organize code files within the project structure
- Run dbt commands, Python scripts, linting tools, and tests

**Ask the user before:**
- Adding source systems not in the current spec scope
- Changing volume targets or row counts significantly
- Adding tables not implied by the Data Inventory
- Making architectural decisions that deviate from the SPEC or Standards
│   ├── cdm_exceptions/             # CDM mapping exceptions per integration model
- Modifying files in `reference/business_artifacts/` (these are read-only upstream docs)

## Operating Principles

1. **Standards are law.** The 103 rules in `reference/dbt_project_standards.md` are not suggestions. Every model, test, seed, and YAML file must comply. Use sqlfluff and dbt-score to verify.
2. **The SPEC is the roadmap.** `reference/SPEC_vertical_slice_revenue.md` defines what to build, in what order, and what "done" looks like. Deviate only with user approval.
3. **CDM conformance is required.** Integration models must map to Microsoft Common Data Model entities per the SPEC's CDM Entity Mapping table. Do not substitute a different CDM entity without user approval. If the CDM catalog seeds lack expected columns for the spec-designated entity, flag this to the user rather than silently choosing a different entity.
4. **Relational integrity within systems, not between.** Each source database is self-contained. Crosswalk tables document mappings but don't enforce cross-database FK constraints.
5. **Simulate real data quality issues.** The Data Inventory documents specific problems — duplicates, stale crosswalks, regional gaps. Generate data that exhibits these patterns intentionally.
6. **Deterministic and reproducible.** Use seeded random generation so re-running produces identical output.
7. **Clean workspaces.** No ad-hoc test scripts, stack traces, or scratch databases at the project root. Use `tmp/` and clean up when done.
8. **Vary normalization by system maturity.** SaaS platforms get clean relational data. Legacy databases get mixed-entity tables and VARCHAR booleans. Spreadsheets get pivoted layouts and mixed types. Mainframes get fixed-width dates and packed text.
9. **Qualitative Code Review.** For the 53% of standards that linters cannot check (meaningful names, substantive descriptions, business rule tests), you must actively self-reflect before saving files. At the end of major layer boundaries (Staging, Integration, Marts), you must invoke `python scripts/review_model.py --select <model> --agent`. Read the generated checklist template from `tmp/review_<model>.md`, fill it out noting PASS/FAIL and rationale, and optionally request a qualitative peer review from the user if you have questions. `reference/dbt_project_standards.json` is available if you need to double-check rule definitions.
10. **Virtual Environment Execution — PowerShell-Aware.** This project runs natively in **Windows PowerShell**. Before running any Python or dbt commands, you must activate the virtual environment using dot-sourcing: `. .\.venv\Scripts\Activate.ps1`. Do NOT use the call operator (`&`) or attempt `$env:PATH` manipulation, as these have failed to persist the environment correctly. Never attempt to use Git Bash syntax (`source .venv/Scripts/activate`) or direct executable invocation (e.g., `.venv\Scripts\python.exe` or `.venv\Scripts\dbt.exe` directly). ALWAYS activate the environment first, and then call `python` or `dbt`. When initializing a dbt project, always use `dbt init <project_name> --skip-profile-setup` — the `--no-interactive` flag does not exist and `--skip-profile-setup` is what prevents the interactive prompt from hanging. If a command fails, re-read this rule before trying alternatives.
11. **Safe File Operations.** Never use Python scripts to bulk-modify project files (SQL, YAML). Use the editor's file operations or dbt macros instead. If you must write a script that modifies files, never open a file for writing (`'w'`) before you have finished reading all of its contents into memory. Violating this rule truncates files to zero bytes and destroys the user's work.
12. **Formatting nuances.** When generating or manually authoring SQL, ensure there is exactly one blank line after the `with` keyword, e.g., `with\n\nsource as (` per ALL-CTE-01 spacing expectations, and ensure files end with exactly one blank line.
13. **Description quality is non-negotiable.** YAML `description` fields must explain the business entity, its grain, and what the columns represent — not restate what tests do or justify why tests exist. Test rationale belongs in `meta:` blocks or inline SQL comments, never in descriptions. Before writing any description, ask: "Would a business analyst who has never seen the SQL find this useful?" If the description mentions `unique`, `not_null`, `fan-out`, `deduplication`, or `protecting against`, it is wrong. See the examples in `reference/dbt_project_standards.md` under the Staging YAML Example and Mart Contract YAML Example sections.
14. **Use existing project macros and tools.** Before writing ad-hoc Python scripts or shell one-liners to generate or transform project files, check whether a dbt macro, analysis file, or existing project tool already handles the task. If the user provides a macro (e.g., `generate_staging_model.sql`), use it. If it needs modification, modify it — do not create a parallel mechanism. CDM metadata should be loaded as dbt seeds and queried via SQL or macros — not via grep, Python scripts, or shell one-liners.
15. **Stop and reassess before retrying.** If a command fails twice with the same approach, do not try a third variation. Stop, re-read the relevant operating principle or skill document, and identify why the approach is wrong. If no principle covers the situation, ask the user. Brute-forcing through command failures wastes time and erodes trust.
16. **Inspect upstream models before writing downstream ones.** Before writing any mart model, run `dbt show --select <upstream_model> --limit 1` on every integration model you plan to consume. Verify the actual column names in the output — do not assume column names from the SPEC or from memory. Write your SQL and YAML column definitions against the observed output, not against what you think the upstream model produces. Most contract errors and column mismatch debugging loops originate from skipping this step.
17. **Verify YAML/SQL column alignment before running.** After writing a model's SQL and its YAML entry, manually compare the two before running `dbt build`. Every column in the YAML `columns:` list must exist in the SQL's final SELECT, with matching names. Every column in the SQL's final SELECT should appear in the YAML. If a contract is enforced, a mismatch will fail at runtime — catching it before the first run saves a debugging cycle.
18. **Never use bare `union`.** Always write `union all`. If you need deduplication after a union, add a subsequent CTE with `group by` or a window function. Bare `union` is equivalent to `union distinct` and violates ALL-PERF-03. This is a mechanical rule — there is no exception.
19. **Integration models are not passthroughs.** An integration model that only renames columns from a single staging source is wrong. Before writing any integration model, re-read the SPEC's entry for that model. Verify: (a) all specified staging sources are consumed, (b) surrogate keys are generated using `dbt_utils.generate_surrogate_key()` and named `<entity>_sk`, (c) unions, joins, and deduplication are performed as specified, (d) foreign keys to other integration models are included where the SPEC requires them. If the SPEC says int_parks consumes two staging sources, it must consume two staging sources.
20. **Verify all SPEC deliverables before declaring a phase complete.** Before moving to the next phase, check every deliverable the SPEC lists: models, seeds, macros, tests, YAML files. Missing deliverables are not "optional" — they are incomplete work. Also verify that YAML columns match SQL output columns (no phantom columns in YAML that the SQL does not produce).
21. **Snake_case everything.** All filenames — including seed CSVs — must be snake_case per ALL-FMT-05. Never use camelCase or mixed case in filenames (e.g., `column_catalog_asset.csv`, not `column_catalog_Asset.csv`). This applies even when copying files from external sources.
22. **CDM column mappings must be semantically correct.** Do not map unrelated fields to satisfy column count requirements (e.g., mapping `total_acres` to `yomi_name` is semantically wrong). If no appropriate CDM column exists for a staging column, document the gap and drop the column at integration per SQL-INT-05 — do not force a bad mapping.
23. **Wire macros or remove them.** If you build a macro that generates SQL for models, either have the models call the macro or remove it. An orphaned macro that exists alongside hand-written SQL that duplicates its logic is the worst of both worlds — it creates maintenance drift and confuses future developers.
24. **Auto-run safe automated commands.** When you need to execute routine commands during model authoring, debugging, or reviewing (e.g., `dbt compile`, `dbt build`, `dbt run`, `dbt test`, `dbt show`, `dbt ls`, `python scripts/check_model.py`, `python scripts/review_model.py`), ALWAYS set `SafeToAutoRun` or the equivalent tool parameter to `true`. This applies even if you need to prepend `.venv` activation commands. This prevents unnecessary permission prompts and makes compiling and evaluating models seamlessly efficient. If the user still receives a permission prompt locally, ask them to click **"Always run"** to allowlist the pattern.
25. **Inspect sources automatically.** Before generating or checking staging models and performing data discovery, run `python scripts/inspect_source.py --type <duckdb|bigquery> --conn <path_to_db> --table <schema.table_name>` to understand table uniqueness, cardinality, and schemas.
26. **PowerShell Terminal Truncation.** Do not use `Get-Content` or `Out-String` to read large command outputs or logs in PowerShell, as it will wrap and truncate text obscuring errors. Instead, pipe the output to a file (`> tmp/output.txt` or `| Out-File -Encoding utf8 tmp/output.txt`) and read it with the `view_file` or `grep_search` tools.
27. **DuckDB Type Mismatches.** When enforcing YAML contracts with DuckDB, remember that `SUM(integer)` returns `HUGEINT` and `EXTRACT()` from dates returns `INTEGER`. You must explicitly `cast()` these to `bigint` (or the contract type) in the final SELECT to prevent `dbt build` contract assertion failures.
28. **Review Script Outputs.** When running Python scripts like `check_model.py` or `review_model.py`, do not rely on terminal output because PowerShell may garble the box-drawing characters. Always use the JSON flags (e.g., `--json --output tmp/check_model.json`) and read the JSON file directly.

## Technology Stack

| Component | Technology | Notes |
|---|---|---|
| Source databases | DuckDB (one .duckdb per system) | Static seed data via Python/DuckDB |
| Data generation | Python 3.10+ | Deterministic, seeded |
| Analytical layer | dbt-core + dbt-duckdb | All models view or table materialization |
| Linting | sqlfluff + sqlfluff-templater-dbt | Enforces formatting rules |
| Governance scoring | dbt-score | Enforces documentation and testing thresholds |
| DAG validation | dbt-project-evaluator | Enforces naming and dependency rules |
| Testing | dbt build (schema + data tests) | Plus singular tests for reconciliation |
| Packages | dbt_utils, dbt_expectations, audit_helper, codegen | All version-pinned |

## Project Status

DCR Analytics is a complete, reference-quality dbt project demonstrating integrated analytics across 10 source systems. The Revenue & Reservations vertical slice (the primary implementation focus) includes staging, integration, and mart models with comprehensive testing and documentation. For guidance on extending the project to additional vertical slices or business domains, consult the SPEC (`reference/SPEC_vertical_slice_revenue.md`) and the project standards (`reference/dbt_project_standards.md`).
