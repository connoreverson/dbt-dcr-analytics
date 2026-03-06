# DCR Analytics — Project Instructions for Claude Code

You are a data engineering agent working on the DCR Analytics project for the Department of Conservation and Recreation. This project has two phases: (1) synthetic source data generation using Python/DuckDB, and (2) a dbt analytical pipeline that transforms those sources into governed, CDM-conforming models.

## Project Structure

```
dbt-public-sector-example/
├── .agent/                    # Agent skills and rules (cross-compatible SSoT)
│   ├── rules/                 # Always-on and model-decision rules
│   └── skills/                # On-demand skill packages
├── .ai/                       # Shared prompts for cross-compatible agents
│   └── prompts/               # Agent system prompts (used by both Claude and Antigravity)
├── .claude/                   # Claude Code configuration
│   └── agents/                # Claude Code subagent definitions
├── .gemini/                   # Gemini CLI and Antigravity configuration
│   └── settings.json
├── reference/                 # All project documentation (not dbt docs/)
│   ├── SPEC_vertical_slice_revenue.md  # Master spec for Revenue & Reservations slice
│   ├── dbt_project_standards.md        # 103 governance rules for the dbt layer
│   ├── data_dictionary.md              # Column-level definitions
│   ├── architectural_review.md         # Source data readiness assessment
│   ├── project.md                      # Project framing and design decisions
│   ├── data_inventory_summary.md       # Condensed quick-reference for all 10 systems
│   └── business_artifacts/             # Read-only upstream business docs
│       ├── DCR Data Inventory.md
│       ├── DCR Business Glossary.md
│       └── data_lineage.csv
└── source_data/               # All external data inputs
    ├── duckdb/                # Generated .duckdb source files (one per system)
    └── cdm_metadata/          # Microsoft CDM entity definitions
        └── revenue_slice/     # Curated subset for this vertical slice
```

## Rules

Before writing code, read the relevant rule files from `.agent/rules/`. These are the project's SSoT for governance — shared across Claude Code and Antigravity.

| Rule File | Activation | When to Read |
|---|---|---|
| `.agent/rules/dbt-project-governance.md` | **Always-on** | All dbt work: layer discipline, naming, testing, CDM requirements |
| `.agent/rules/coding-standards.md` | On-demand | Writing Python or making general code convention decisions |
| `.agent/rules/schema-design.md` | On-demand | Designing schemas or writing DDL |
| `.agent/rules/data-generation.md` | On-demand | Generating synthetic source data |
| `.agent/rules/dcr-domain-knowledge.md` | On-demand | Business or domain-driven decisions |

Read `.agent/rules/dbt-project-governance.md` at the start of every session before touching any model, test, seed, or YAML file.

## Skills

On-demand skill packages live in `.agent/skills/`. Each skill directory contains a `SKILL.md` with step-by-step instructions. When a task matches a skill description, read the corresponding `SKILL.md` before proceeding.

| Skill | Directory | When to Use |
|---|---|---|
| Running dbt commands | `.agent/skills/running-dbt-commands/` | Any dbt CLI invocation |
| Planning from spec | `.agent/skills/planning-from-spec/` | Creating project plans from SPEC docs |
| Using dbt for analytics | `.agent/skills/using-dbt-for-analytics-engineering/` | General dbt model building |
| Adding dbt unit tests | `.agent/skills/adding-dbt-unit-test/` | Writing unit tests for models |
| Systematic debugging | `.agent/skills/systematic-debugging/` | Diagnosing failures |
| Troubleshooting dbt errors | `.agent/skills/troubleshooting-dbt-job-errors/` | dbt command failures |
| Building semantic layer | `.agent/skills/building-dbt-semantic-layer/` | Semantic layer configuration |
| Test-driven development | `.agent/skills/test-driven-development/` | TDD workflows |
| Writing plans | `.agent/skills/writing-plans/` | Writing structured execution plans |
| Executing plans | `.agent/skills/executing-plans/` | Following a plan step by step |
| Brainstorming | `.agent/skills/brainstorming/` | Design and ideation |
| Writing skills | `.agent/skills/writing-skills/` | Creating new skill packages |
| Writing system prompts | `.agent/skills/writing-system-prompts/` | Authoring agent instructions |
| Bootstrapping workspace | `.agent/skills/bootstrapping-agent-workspace/` | Setting up agent environments |
| Answering NL questions | `.agent/skills/answering-natural-language-questions-with-dbt/` | Business user queries |
| Configuring dbt MCP | `.agent/skills/configuring-dbt-mcp-server/` | MCP server setup |
| Fetching dbt docs | `.agent/skills/fetching-dbt-docs/` | Documentation retrieval |
| Linting and governance verification | `.agent/skills/linting-and-governance-verification/` | Phase 7: sqlfluff, dbt-score, dbt-project-evaluator |

## Subagents

Specialized subagents are defined in `.claude/agents/`. Their core system prompts live in `.ai/prompts/` as the SSoT shared with Antigravity.

| Agent | File | Purpose |
|---|---|---|
| dbt Implementer | `.claude/agents/dbt-implementer.md` | Build dbt models per the SPEC, layer by layer |
| Spec Planner | `.claude/agents/spec-planner.md` | Convert SPEC documents into ordered project plans |

## Key References

Read these before making substantive decisions:

- `reference/business_artifacts/DCR Data Inventory.md` — Authoritative source for all 10 systems, their schemas, quality issues, and integration dependencies
- `reference/data_inventory_summary.md` — Condensed quick-reference for all 10 source systems
- `reference/dbt_project_standards.md` — 103 rules governing every layer of the dbt project
- `reference/SPEC_vertical_slice_revenue.md` — Complete specification for the first vertical slice (Revenue & Reservations)
- `source_data/cdm_metadata/revenue_slice/` — Curated CDM entity and column schemas for this slice (Asset, nonProfitCore, applicationCommon, Visits, cdmfoundation). Full library available in parent directory if needed.

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
10. **Qualitative Code Review.** For the 53% of standards that linters cannot check (meaningful names, substantive descriptions, business rule tests), you must actively self-reflect before saving files. At the end of major layer boundaries (Staging, Integration, Marts), you must invoke `python scripts/review_model.py --select <model> --agent`. Read the generated checklist template from `tmp/review_<model>.md`, fill it out noting PASS/FAIL and rationale, and optionally request a qualitative peer review from the user if you have questions. `reference/dbt_project_standards.json` is available if you need to double-check rule definitions.
10. **Virtual Environment Execution — Shell-Aware.** Before activating the Python virtual environment, identify the active shell. This project runs in **Git Bash** (`/usr/bin/bash`). In Git Bash, activate with: `source .venv/Scripts/activate`. If running in PowerShell, use dot-sourcing instead: `. .\.venv\Scripts\Activate.ps1`. Never use the PowerShell `.ps1` form in Git Bash — Bash strips backslashes and cannot execute `.ps1` files. This failure is silent when dbt/sqlfluff are already on PATH, masking the broken activation entirely. Do not use the call operator (`&`), `$env:PATH` manipulation, or direct executable invocation — all of these have failed in practice. When initializing a dbt project, always use `dbt init <project_name> --skip-profile-setup` — the `--no-interactive` flag does not exist and `--skip-profile-setup` is what prevents the interactive prompt from hanging. If a command fails, re-read this rule before trying alternatives.
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
24. **Auto-run safe automated commands.** When you need to execute routine commands during model authoring, debugging, or reviewing (e.g., `dbt compile`, `dbt build`, `dbt run`, `dbt test`, `dbt show`, `dbt ls`, `python scripts/check_model.py`, `python scripts/review_model.py`), ALWAYS set `SafeToAutoRun` or the equivalent tool parameter to `true`. This applies even if you need to prepend `.venv` activation commands. This prevents unnecessary permission prompts and makes compiling and evaluating models seamlessly efficient.
25. **Inspect sources automatically.** Before generating or checking staging models and performing data discovery, run `python scripts/inspect_source.py --type <duckdb|bigquery> --conn <path_to_db> --table <schema.table_name>` to understand table uniqueness, cardinality, and schemas.

## Technology Stack

| Component | Technology | Notes |
|---|---|---|
| Source databases | DuckDB (one .duckdb per system) | Generated by Python/mimesis |
| Data generation | Python 3.10+ with mimesis | Deterministic, seeded |
| Analytical layer | dbt-core + dbt-duckdb | All models view or table materialization |
| Linting | sqlfluff + sqlfluff-templater-dbt | Enforces formatting rules |
| Governance scoring | dbt-score | Enforces documentation and testing thresholds |
| DAG validation | dbt-project-evaluator | Enforces naming and dependency rules |
| Testing | dbt build (schema + data tests) | Plus singular tests for reconciliation |
| Packages | dbt_utils, dbt_expectations, audit_helper, codegen | All version-pinned |

## Project Status

DCR Analytics is a complete, reference-quality dbt project demonstrating integrated analytics across 10 source systems. The Revenue & Reservations vertical slice (the primary implementation focus) includes staging, integration, and mart models with comprehensive testing and documentation. For guidance on extending the project to additional vertical slices or business domains, consult the SPEC (`reference/SPEC_vertical_slice_revenue.md`) and the project standards (`reference/dbt_project_standards.md`).
