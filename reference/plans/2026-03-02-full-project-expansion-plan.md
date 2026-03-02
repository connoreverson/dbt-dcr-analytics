# Full Project Expansion Implementation Plan

> **For agent execution:**
> - **Claude Code:** Use the `executing-plans` skill to implement this plan task-by-task. Invoke the `dbt-implementer` subagent (`.claude/agents/dbt-implementer.md`) for all model-building work in Phases 1–3. Auto-run all dbt/lint/review commands per `.claude/settings.local.json` allowlist.
> - **Antigravity:** Invoke the designated workflow files via `@` import (`@/02_build_source_and_staging.md`, `@/03_build_integration.md`, `@/04_build_marts.md`). `// turbo-all` handles auto-approve for all safe commands.

**Source Specification:** `reference/data_inventory_summary.md` and `reference/dbt_project_standards.md`
**Goal:** Expand the project horizontally from a single vertical slice (Revenue & Reservations) to encompass all 10 inventoried DCR systems, layering staging, integration, and marts sequentially.
**Architecture:** Medallion-style dbt pipeline (Sources -> Base/Staging -> Integration with CDM mapping -> Marts), with strict relational boundary enforcement.
**Tech Stack:** `dbt-core`, `dbt-duckdb`, `sqlfluff`, `dbt-score`, `dbt-project-evaluator`, Python 3.10+
**Success Criteria:**
- All 10 sources successfully staged.
- Comprehensive integration layer built with mapped Microsoft CDM entities or documented `CDM_EXCEPTION` extensions.
- Fact and dimension marts built across the enterprise data model.
- 100% compliance with `reference/dbt_project_standards.md` (sqlfluff, dbt-score passes).

### Agent Invocation Reference

Each task in this plan includes an **Agent Invocation** block specifying how both Claude Code and Antigravity should execute it. The conventions are:

| Platform | Model-building tasks | Governance tasks | CDM exception tasks |
|---|---|---|---|
| **Claude Code** | `dbt-implementer` subagent | `linting-and-governance-verification` skill | `cdm-exception-request` skill |
| **Antigravity** | `@/0X_workflow.md` import | `@/05_run_compliance_checks.md` import | `@/.agent/skills/cdm-exception-request/SKILL.md` import |

---

## Phase 0: Workflow Enhancements (Pre-Implementation)

To maximize agent effectiveness and minimize human intervention for both Claude Code and Antigravity, the following updates must be made *before* layer expansion begins.

### Task 0.1: Remove Mid-Phase Human Gates from Workflow 03

The only workflow with a blocking mid-phase human gate is `.agent/workflows/03_build_integration.md`, Step 1, which reads: _"do NOT auto-run. Present the generated files to the user for review before proceeding."_ Workflows 02 and 04 already defer human review to the end of the phase.

**Files:**
- Modify: `.agent/workflows/03_build_integration.md`

**Step 1:** Rewrite Step 1 of Workflow 03 to remove the "do NOT auto-run" instruction. Replace with: _"Generate SQL and YAML files, then auto-run `dbt build` and `sqlfluff fix`/`lint` iteratively. Defer human review to the end-of-phase qualitative peer review (Step 6)."_
**Step 2:** Verify that `.claude/settings.local.json` allowlist covers all commands the expansion will need. If new systems introduce new script paths or tool invocations, add them before Phase 1 begins.
**Step 3:** Verify that `.gemini/settings.json` `includeDirectories` covers any new reference files added for the expansion (e.g., new CDM exception documents).

### Task 0.2: Implement Automated CDM Entity Identification Strategy

Per Operating Principle 14, CDM metadata must be queried via dbt seeds and SQL — not via standalone Python scripts.

**Files:**
- Add macro: `macros/identify_candidate_cdm.sql`
- Optionally add analysis: `analyses/cdm_entity_coverage.sql`

**Step 1:** Create a dbt macro (`identify_candidate_cdm`) that accepts an integration model name, queries the CDM catalog seeds (`seeds/cdm_catalogs/*`) via `dbt run-operation`, compares the model's column list against catalog entity schemas, and ranks candidates by column coverage percentage.
**Step 2:** Define rule: When building an integration model, run `dbt run-operation identify_candidate_cdm --args '{model_name: "int_xxx"}'` first. If the top candidate entity matches <50% semantically or misses critical domain features, the agent should run the `cdm-exception-request` skill (Claude Code) or read `@/.agent/skills/cdm-exception-request/SKILL.md` (Antigravity) to generate a `reference/CDM_EXCEPTION_<model>.md` file before moving on.

### Task 0.3: Verify Source Data Completeness

Before staging any system, confirm that the generated DuckDB files contain all tables listed in the Data Inventory's "Key tables" section.

**Step 1:** For each of the 8 new systems, run `dbt show --inline "select table_name from information_schema.tables where table_schema = '<schema>'" --limit 50` (or the DuckDB equivalent) and cross-reference against `reference/data_inventory_summary.md`.
**Step 2:** If any expected tables are missing from a DuckDB file, flag the gap and generate the missing source data before proceeding to staging.

**Agent Invocation:**
- **Claude Code:** Auto-run via `dbt show --inline` queries. No subagent needed — this is reconnaissance.
- **Antigravity:** Auto-run via `// turbo-all`. Use `@reference/data_inventory_summary.md` as the cross-reference.

---

## Phase 1: Build Source and Staging (Horizontal Expansion)

Implement all remaining 8 source systems by following the staging workflow. GeoParks (DCR-GEO-01) staging is partially complete (`stg_geoparks__parks_master` exists) but the Data Inventory lists additional key tables (infrastructure features, natural resources, cultural resources, recreational features) that may need staging if downstream integration or mart models require them. Evaluate during Phase 2 and backfill if needed.

### Task 1.1: Stage LegacyRes_Archive (DCR-REV-02)
**Action:** Unpack historical reservations, handle varying date formats (MMDDYYYY, YYYY-MM-DD), unpack pipe-delimited guest info.
**Verification:** `dbt build --select staging.legacyres.*` passes.
**Agent Invocation:**
- **Claude Code:** `dbt-implementer` subagent. Auto-run all dbt commands per allowlist.
- **Antigravity:** `@/02_build_source_and_staging.md`

### Task 1.2: Stage StateGov Financials (DCR-FIN-01)
**Action:** Stage mainframe COBOL outputs (general ledger, vendors). Parse pipe-delimited memo fields and split string accounts.
**Verification:** `dbt build --select staging.stategov.*` passes.
**Agent Invocation:**
- **Claude Code:** `dbt-implementer` subagent.
- **Antigravity:** `@/02_build_source_and_staging.md`

### Task 1.3: Stage GrantTrack_Excel_Master (DCR-FIN-02)
**Action:** Unpivot fiscal-year columns, clean mixed date formats, handle exploded string lists (comma/pipe delimited names).
**Verification:** `dbt build --select staging.granttrack.*` passes.
**Agent Invocation:**
- **Claude Code:** `dbt-implementer` subagent.
- **Antigravity:** `@/02_build_source_and_staging.md`

### Task 1.4: Stage InfraTrak Lifecycle (DCR-AST-01)
**Action:** Stage JSON/EAM subsets. Map assessment scores and unify physical infrastructure references.
**Verification:** `dbt build --select staging.infratrak.*` passes.
**Agent Invocation:**
- **Claude Code:** `dbt-implementer` subagent.
- **Antigravity:** `@/02_build_source_and_staging.md`

### Task 1.5: Stage RangerShield CAD/RMS (DCR-LES-01)
**Action:** Standardize restricted CJIS air-gapped models (dummy/mock data patterns applied). Extract text-blob locations to descriptive addresses.
**Verification:** `dbt build --select staging.rangershield.*` passes.
**Agent Invocation:**
- **Claude Code:** `dbt-implementer` subagent.
- **Antigravity:** `@/02_build_source_and_staging.md`

### Task 1.6: Stage BioSurvey_Legacy (DCR-NRM-01)
**Action:** Clean multi-era MS Access types. Split mixed-entity observation table (flora/fauna/water) into separate staging models.
**Verification:** `dbt build --select staging.biosurvey.*` passes.
**Agent Invocation:**
- **Claude Code:** `dbt-implementer` subagent.
- **Antigravity:** `@/02_build_source_and_staging.md`

### Task 1.7: Stage PeopleFirst HR (DCR-HCM-01)
**Action:** Stage positions, employee trees, benefits. Obfuscate PII.
**Verification:** `dbt build --select staging.peoplefirst.*` passes.
**Agent Invocation:**
- **Claude Code:** `dbt-implementer` subagent.
- **Antigravity:** `@/02_build_source_and_staging.md`

### Task 1.8: Stage TrafficCount_IoT (DCR-VUM-01)
**Action:** Ingest raw payloads. Retain multi-park grain for IoT devices.
**Verification:** `dbt build --select staging.trafficcount.*` passes.
**Agent Invocation:**
- **Claude Code:** `dbt-implementer` subagent.
- **Antigravity:** `@/02_build_source_and_staging.md`

### Task 1.9: Phase 1 Final Governance & Review
**Action:** Run the `linting-and-governance-verification` skill across all staging models (3-tool sequence: sqlfluff fix/lint, dbt-score lint, dbt-project-evaluator build). Address all violations. Then run `python scripts/review_model.py --select <model> --agent` for each new staging model and compile findings.
**Verification:** All three governance tools pass cleanly per the acceptance criteria in `.agent/skills/linting-and-governance-verification/SKILL.md`.
**Human Gate:** Present compiled review findings to user for final approval before proceeding to Phase 2.
**Agent Invocation:**
- **Claude Code:** Run `linting-and-governance-verification` skill. Auto-run all review scripts per allowlist.
- **Antigravity:** `@/05_run_compliance_checks.md`

---

## Phase 2: Build Integration Layer (Horizontal Expansion)

Integrate the disparate staging tables into cohesive, CDM-mapped entities using the integration workflow.

**Note on existing models:** The revenue slice already produced `int_contacts`, `int_customer_assets`, `int_parks`, `int_transactions`, and `int_visits`. The previously existing `int_reservations` was removed (see git history). Phase 2 tasks should extend `int_parks` (Task 2.1) and build new integration models alongside the existing ones. Do not duplicate or overwrite the existing revenue-slice integration models unless the expansion requires structural changes to them.

### Task 2.1: Extend Master Parks Integration
**Action:** Extend `int_parks` to join additional staging sources beyond the current GeoParks + VistaReserve pair. Incorporate `stg_infratrak__assets` (InfraTrak park-level records) to resolve identifier fragmentation. Handle stale (pre-2022) crosswalks.
**CDM Strategy:** `int_parks` already maps to a CDM exception entity. Verify the exception document (`reference/CDM_EXCEPTION_int_parks.md`) still covers the expanded column set. Update if needed.
**Agent Invocation:**
- **Claude Code:** `dbt-implementer` subagent. Run `dbt show --select int_parks --limit 1` first to inspect current output.
- **Antigravity:** `@/03_build_integration.md`

### Task 2.2: Financial Integration (`int_financials`)
**Action:** Build `int_financials` linking `stg_stategov` (SGF) object codes with `stg_granttrack` lifecycle funds.
**CDM Strategy:** Run `dbt run-operation identify_candidate_cdm --args '{model_name: "int_financials"}'` to evaluate candidate CDM entities. If no standard entity provides adequate coverage, run the `cdm-exception-request` skill to generate `reference/CDM_EXCEPTION_int_financials.md`.
**Agent Invocation:**
- **Claude Code:** `dbt-implementer` subagent. Use `cdm-exception-request` skill if CDM validation fails.
- **Antigravity:** `@/03_build_integration.md`. Read `@/.agent/skills/cdm-exception-request/SKILL.md` if CDM validation fails.

### Task 2.3: Asset Integration (`int_physical_assets`)
**Action:** Join infrastructure geometries (GeoParks) with EAM data (InfraTrak).
**CDM Strategy:** Run `dbt run-operation identify_candidate_cdm --args '{model_name: "int_physical_assets"}'`. Review `Asset.1.0` (FunctionalLocation). If coverage is insufficient, run the `cdm-exception-request` skill to generate `reference/CDM_EXCEPTION_int_physical_assets.md`.
**Agent Invocation:**
- **Claude Code:** `dbt-implementer` subagent. Use `cdm-exception-request` skill if CDM validation fails.
- **Antigravity:** `@/03_build_integration.md`. Read `@/.agent/skills/cdm-exception-request/SKILL.md` if CDM validation fails.

### Task 2.4: Natural Resources & IoT Integration
**Action:** Integrate `stg_biosurvey` and `stg_trafficcount` models. Tie coordinates to `int_parks` via FK. Build separate models as appropriate (`int_ecological_surveys`, `int_visitor_counts`) — do not force unrelated domains into a single model.
**CDM Strategy:** Run CDM identification for each model. These are likely CDM exception candidates given the specialized domain columns.
**Agent Invocation:**
- **Claude Code:** `dbt-implementer` subagent. Use `cdm-exception-request` skill as needed.
- **Antigravity:** `@/03_build_integration.md`

### Task 2.5: HR & Law Enforcement Integrations
**Action:** Build `int_employees` from PeopleFirst staging models and `int_officer_activity` from RangerShield staging models. Isolate LE data to its own compliant integration point — do not join LE data with non-LE sources at this layer.
**CDM Strategy:** Run CDM identification for each. HR entities may partially map to CDM `Worker` or `Employee`. LE entities are almost certainly CDM exception candidates. Run the `cdm-exception-request` skill as needed.
**Agent Invocation:**
- **Claude Code:** `dbt-implementer` subagent. Use `cdm-exception-request` skill as needed.
- **Antigravity:** `@/03_build_integration.md`

### Task 2.6: GeoParks Staging Backfill Assessment
**Action:** GeoParks currently has only `stg_geoparks__parks_master`. The Data Inventory lists infrastructure features, natural resources, cultural resources, and recreational features as additional key tables. Assess whether any Phase 2 or Phase 3 models require these additional staging models. If yes, build them following the staging workflow before proceeding.
**Agent Invocation:**
- **Claude Code:** Reconnaissance via `dbt show --inline` queries against the GeoParks DuckDB. Build missing staging models with `dbt-implementer` subagent if needed.
- **Antigravity:** `@/02_build_source_and_staging.md` if backfill is needed.

### Task 2.7: Phase 2 Final Governance & Review
**Action:** Run the `linting-and-governance-verification` skill across all integration models (3-tool sequence). Then run `python scripts/review_model.py --select <model> --agent` for each integration model (use `dbt ls --select integration.* --resource-types model --output name` to enumerate models, per Workflow 03 Step 2). Compile findings.
**Verification:** All three governance tools pass cleanly. All CDM validation checks pass (`python scripts/check_model.py --select <model>` for each integration model).
**Human Gate:** Present compiled review findings and CDM coverage summary to user for final approval before proceeding to Phase 3.
**Agent Invocation:**
- **Claude Code:** Run `linting-and-governance-verification` skill. Auto-run all review and check scripts per allowlist.
- **Antigravity:** `@/05_run_compliance_checks.md`

---

## Phase 3: Build Marts Layer (Horizontal Expansion)

Build analytics-ready facts and dimensions referencing *only* the integration layer, adhering to the marts workflow.

**Note on existing models:** The revenue slice already produced `dim_customers`, `dim_parks`, `dim_reservation_inventory`, `fct_pos_transactions`, `fct_reservations`, and `rpt_park_revenue_summary` in `models/marts/revenue/`. Phase 3 tasks build new enterprise-wide dimensions and cross-domain facts. Where a new enterprise dimension overlaps with an existing revenue-slice dimension (e.g., `dim_parks` already exists), extend the existing model rather than creating a parallel one. New mart domains (operations, finance, attendance) should live in their own subdirectories under `models/marts/`.

### Task 3.1: Core Enterprise Dimensions
**Action:** Build enterprise dimensions that do not yet exist: `dim_date` (role-playing date dimension), `dim_assets` (from `int_physical_assets`), `dim_employees` (from `int_employees`), `dim_vendors` (from `int_financials` vendor data). Extend `dim_parks` to incorporate the expanded `int_parks` output from Task 2.1 if new columns were added.
**Verification:** `dbt build --select models/marts/` passes. All dimension PKs have `unique` + `not_null` tests.
**Agent Invocation:**
- **Claude Code:** `dbt-implementer` subagent. Run `dbt show --select <upstream_int_model> --limit 1` for each upstream model before writing SQL (Operating Principle 16).
- **Antigravity:** `@/04_build_marts.md`

### Task 3.2: Operations Fact (`fct_incidents_and_maintenance`)
**Action:** Relate `int_officer_activity` and InfraTrak work orders to `dim_parks`. Include dimension FKs with `relationships` tests. Add `dbt_expectations` volumetric test.
**Verification:** `dbt build --select fct_incidents_and_maintenance` passes.
**Agent Invocation:**
- **Claude Code:** `dbt-implementer` subagent.
- **Antigravity:** `@/04_build_marts.md`

### Task 3.3: Financial Fact (`fct_expenditures`)
**Action:** Summarize general ledger, match grants to spending. Handle "budget activity export mixes" correctly via dimensional grouping. Include dimension FKs to `dim_vendors`, `dim_parks`, `dim_date`. Add aggregation balance test and `dbt_expectations` volumetric test.
**Verification:** `dbt build --select fct_expenditures` passes.
**Agent Invocation:**
- **Claude Code:** `dbt-implementer` subagent.
- **Antigravity:** `@/04_build_marts.md`

### Task 3.4: Attendance Fact (`fct_visitation`)
**Action:** Merge VistaReserve check-ins with TrafficCount IoT aggregates (apply 2.7 occupancy multiplier correctly) into a daily/park grain. Include dimension FKs to `dim_parks`, `dim_date`. Add aggregation balance test and `dbt_expectations` volumetric test.
**Verification:** `dbt build --select fct_visitation` passes.
**Agent Invocation:**
- **Claude Code:** `dbt-implementer` subagent.
- **Antigravity:** `@/04_build_marts.md`

### Task 3.5: Reporting Mart (`rpt_agency_performance`)
**Action:** Marry financial, visitation, and incident measures together into the final agency dashboard query. Consumes only facts and dimensions — never staging or integration directly.
**Verification:** `dbt build --select rpt_agency_performance` passes.
**Agent Invocation:**
- **Claude Code:** `dbt-implementer` subagent.
- **Antigravity:** `@/04_build_marts.md`

### Task 3.6: Phase 3 Final Governance & Review
**Action:** Run the `linting-and-governance-verification` skill across all mart models (3-tool sequence). Verify ALL-PERF-03 (no bare unions) compliance. Run `python scripts/review_model.py --select <model> --agent` for each mart model and compile findings.
**Verification:** All three governance tools pass cleanly per the acceptance criteria in `.agent/skills/linting-and-governance-verification/SKILL.md`.
**Human Gate:** Present compiled review findings to user for final approval before proceeding to Phase 4.
**Agent Invocation:**
- **Claude Code:** Run `linting-and-governance-verification` skill. Auto-run all review scripts per allowlist.
- **Antigravity:** `@/05_run_compliance_checks.md`

---

## Phase 4: End-to-End Validation

### Task 4.1: Full Project Build
**Action:** Run `dbt build --full-refresh` across the entire project with the deterministic DuckDB datasets. This validates that all sources, staging, integration, and mart models compile and pass tests end-to-end.
**Verification:** Zero errors across all `dbt build` steps.
**Agent Invocation:**
- **Claude Code:** Auto-run. This is the only task where a project-wide `dbt build` (no `--select`) is appropriate.
- **Antigravity:** Auto-run via `// turbo-all`.

### Task 4.2: Row Count Reconciliation
**Action:** For each integration model, verify that row counts are plausible against the upstream staging models. Use `dbt show --inline "select count(*) from {{ ref('int_xxx') }}"` queries. Flag any model where the integration output has significantly more or fewer rows than expected given the staging inputs (indicating a fan-out, dropped join, or missing union arm).
**Verification:** No unexplained row count anomalies.
**Agent Invocation:**
- **Claude Code:** Auto-run `dbt show --inline` queries. No subagent needed.
- **Antigravity:** Auto-run via `// turbo-all`.

### Task 4.3: Final Governance Sweep
**Action:** Run Workflow 05 (`05_run_compliance_checks.md`) at full project scope. This is the final gate — all three governance tools must pass with zero failures across the entire project.
**Verification:** sqlfluff lint = zero violations. dbt-score lint = all models above threshold. dbt-project-evaluator = zero errors/warnings.
**Human Gate:** Present final governance results to user. This is the ship/no-ship decision point.
**Agent Invocation:**
- **Claude Code:** Run `linting-and-governance-verification` skill at project scope.
- **Antigravity:** `@/05_run_compliance_checks.md`
