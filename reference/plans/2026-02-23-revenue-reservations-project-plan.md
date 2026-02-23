# Revenue & Reservations Project Plan

**Source Specification:** `reference/SPEC_vertical_slice_revenue.md`
**Goal:** Prove the foundational analytical architecture end-to-end by unifying VistaReserve POS and reservation data with GeoParks geospatial references — establishing the pattern for all future data source integration.
**Architecture:** The pipeline flows unidirectionally from source schemas (Layer 1) to staging and base models where data is standardized (Layers 2 and 3); from there, it coalesces into CDM-conforming integration models (Layer 4) before terminating in dimensional marts (Layer 5) for business consumption. This layered design creates clear boundaries between system extraction, semantic harmonization, and metric provision.
**Tech Stack:** Python 3.10+, dbt-core, dbt-duckdb, sqlfluff, dbt-score.
**Success Criteria:**
- `dbt build --full-refresh` completes with 0 errors and 0 test failures.
- sqlfluff linting passes on all SQL files with 0 violations.
- dbt-score evaluations pass for all models.
- dbt-project-evaluator identifies 0 DAG and 0 naming violations.
- All models produce rows.
- The `int_parks` model yields exactly 50 rows (one per park unit).
- Revenue reconciliation succeeds: the report total balances against the sum of the reservations and POS fact models.

---

## Open Questions

Before proceeding with Phase 4, the following open questions from the specification must be resolved or actively mitigated:

1. **Park ID reconciliation strategy:** Should `int_parks` join GeoParks and VistaReserve parks on a deterministic attribute match (park name similarity, region + ordinal), or rely on the stale `asset_crosswalk`, or require a manually curated seed file mapping the two ID systems?
    - *Impact:* Blocks `int_parks` and cascades to every downstream model.
    - *Resolution plan:* Resolve before starting Phase 4. The initial recommendation is to consume the stale crosswalk as a base model with explicit warnings, but engineering and business teams should finalize the approach during Phase 3.
2. **Revenue batch grain:** Are `revenue_batch` records individual transactions or aggregated batch summaries?
    - *Impact:* Determines integration model count and fact model structure.
    - *Resolution plan:* Engineering should resolve this through data profiling at the start of Phase 3 to inform whether batches can be unioned with POS transactions.
3. **PII handling policy:** Customer profiles contain personal data (names, addresses, potentially payment info). Should the dbt project apply column-level masking, exclude these columns at staging, or handle sensitivity classification separately?
    - *Impact:* Affects `stg_vistareserve__customer_profiles` column selection.
    - *Resolution plan:* Defer final policy to a separate workstream but include the columns for now to prove end-to-end flow.
4. **CDM FunctionalLocation vs. Territory for parks:** The preliminary mapping uses FunctionalLocation from the Asset manifest, but Territory from applicationCommon or Account from nonProfitCore could also fit.
    - *Impact:* Determines `int_parks` column definitions.
    - *Resolution plan:* Engineering must confirm the choice during the Phase 4 CDM mapping.
5. **Snapshot cadence:** The `snp_vistareserve__inventory_assets` snapshot needs a run schedule, but this is a local development project without a scheduler.
    - *Impact:* Low; pattern demonstration only.
    - *Resolution plan:* Document the snapshot but do not actively schedule it.

---

## Phase 0: Project Initialization

Establish the environment and repository structure that will govern all future analytical development.

### Task 0.1: Initialize Python Environment and Core Tooling

**Files:**
- Modify: `requirements.txt`

**Steps:**
1. Create a Python virtual environment in the project root: `python -m venv .venv`
2. Activate the environment (e.g., `source .venv/bin/activate` or `.venv\Scripts\activate`).
3. Create `requirements.txt` and define versions for `dbt-core`, `dbt-duckdb`, `sqlfluff`, `sqlfluff-templater-dbt`, and `dbt-score`.
4. Install dependencies: `pip install -r requirements.txt`.

**Verification:**
- `dbt --version` runs successfully.
- `sqlfluff --version` runs successfully.

**Standards Compliance:**
- ALL-CFG-03 (Package Version Pinning)

### Task 0.2: Scaffold the dbt Project

**Files:**
- Create: `dbt_project.yml`
- Create: `profiles.yml`
- Create: `packages.yml`

**Steps:**
1. Initialize the dbt project structure manually or via `dbt init`, naming it `dcr_analytics`.
2. Configure `dbt_project.yml` with layer-specific materialization defaults (staging: view, integration: table, marts: table).
3. Draft `profiles.yml` pointing to the analytical DuckDB database and attaching the specified source databases (`dcr_rev_01_vistareserve.duckdb`, `dcr_geo_01_geoparks.duckdb`).
4. Define package dependencies in `packages.yml`: `dbt_utils`, `dbt_expectations`, `dbt_project_evaluator`, `audit_helper`, `codegen`. Pin all versions.
5. Run `dbt deps` to pull packages.

**Verification:**
- `dbt debug` connects to the DuckDB profile without errors.

**Standards Compliance:**
- ALL-CFG-01, ALL-CFG-03

### Task 0.3: Configure Governance Tooling

**Files:**
- Create: `.sqlfluff`
- Create: `.sqlfluffignore`
- Create/Modify: `pyproject.toml` (or `dbt_score.yml`)

**Steps:**
1. Detail `.sqlfluff` configuration to enforce formatting rules: `max_line_length = 80`, `capitalisation_policy = lower`, explicit joins, and descriptive table aliases.
2. Setup `dbt-score` rules in `pyproject.toml` targeting `has_description`, `has_unique_test`, `has_not_null_test`, and any custom severity checks.

**Verification:**
- `sqlfluff lint` runs against the empty project structure.
- `dbt-score score` evaluates without syntax errors in the configuration files.

**Standards Compliance:**
- ALL-FMT-02, ALL-FMT-03, ALL-FMT-04, ALL-FMT-05, ALL-FMT-06, ALL-FMT-07, YML-DOC-01

---

## Phase 1: Source Definitions

Register the authoritative data structures of our upstream dependencies.

### Task 1.1: VistaReserve Source Definition

**Files:**
- Create: `models/staging/vistareserve/_sources.yml`

**Steps:**
1. Document the 7 VistaReserve tables (`parks`, `customer_profiles`, `inventory_assets`, `reservations`, `pos_transactions`, `revenue_batch`, `asset_crosswalk`).
2. Include table descriptions, freshness blocks (warn_after, error_after), and column-level tests (`unique`, `not_null` on PKs, and `relationships` on FKs).
3. Use data from the Data Inventory to write substantive descriptions outlining each table's purpose.

**Verification:**
- `dbt source freshness` runs successfully.

**Standards Compliance:**
- SRC-YML-01, SRC-YML-02, SRC-YML-03, SRC-YML-04, SRC-YML-05, SRC-YML-06

### Task 1.2: GeoParks Source Definition

**Files:**
- Create: `models/staging/geoparks/_sources.yml`

**Steps:**
1. Document the `parks_master` table.
2. Define freshness with wide thresholds supporting the 1–3 year update lag.
3. Include primary key tests on the park identifier.

**Verification:**
- `dbt compile` succeeds.

**Standards Compliance:**
- SRC-YML-01, SRC-YML-02, SRC-YML-03, SRC-YML-04, SRC-YML-05

---

## Phase 2: Base Models

Isolate complex deduplication and transformation logic prior to staging.

### Task 2.1: Base VistaReserve Customer Profiles

**Files:**
- Create: `models/staging/vistareserve/base/base_vistareserve__customer_profiles.sql`

**Steps:**
1. Read from `{{ source('vistareserve', 'customer_profiles') }}`.
2. Implement deduplication logic leveraging a window function (`ROW_NUMBER()` partitioned by the business key, ordered by `updated_at` descending).
3. Select only the most recent version of each customer record.

**Verification:**
- Query output shows distinct customers corresponding to the deduplication criteria.

**Standards Compliance:**
- SQL-BASE-01, SQL-BASE-02, SQL-BASE-05, SQL-BASE-09

### Task 2.2: Base VistaReserve Asset Crosswalk

**Files:**
- Create: `models/staging/vistareserve/base/base_vistareserve__asset_crosswalks.sql`

**Steps:**
1. Read from `{{ source('vistareserve', 'asset_crosswalk') }}`.
2. Add a `days_since_last_update` column to convey staleness.
3. Append a `source_system` literal ('vistareserve').

**Verification:**
- Query output confirms the presence of the new metadata columns.

**Standards Compliance:**
- SQL-BASE-01, SQL-BASE-02, SQL-BASE-05, SQL-BASE-08

---

## Phase 3: Staging Models

Rename, cast, and standardize fields to prepare the data for integration.

### Task 3.1: Staging GeoParks

**Files:**
- Create: `models/staging/geoparks/stg_geoparks__parks_master.sql`
- Create: `models/staging/geoparks/_models.yml`

**Steps:**
1. Write the staging query for `parks_master`: standardize names, keep VARCHAR identifiers, and generate a surrogate hash key using `dbt_utils`.
2. Document the model in `_models.yml` with `unique` and `not_null` tests on the hash key and a substantive description.

**Verification:**
- `dbt run --select stg_geoparks__parks_master` succeeds.
- `sqlfluff lint` passes without violations.

**Standards Compliance:**
- SQL-STG-01 to SQL-STG-11, STG-YML-01 to STG-YML-03

### Task 3.2: Staging VistaReserve Foundation

**Files:**
- Create: `models/staging/vistareserve/stg_vistareserve__parks.sql`
- Create: `models/staging/vistareserve/stg_vistareserve__inventory_assets.sql`
- Create: `models/staging/vistareserve/stg_vistareserve__asset_crosswalks.sql`
- Modify: `models/staging/vistareserve/_models.yml`

**Steps:**
1. Develop staging queries for `parks`, `inventory_assets`, and `asset_crosswalks` (sourcing the crosswalk from its base model).
2. Cast the VistaReserve park ID from INTEGER to VARCHAR to align with GeoParks.
3. Parse any JSON metadata present in inventory assets.
4. Add all models to `_models.yml` with appropriate tests and descriptions.

**Verification:**
- All three models build successfully and pass column-level tests.

**Standards Compliance:**
- SQL-STG-07, SQL-STG-10, SQL-STG-12

### Task 3.3: Staging VistaReserve Subject and Financials

**Files:**
- Create: `models/staging/vistareserve/stg_vistareserve__customer_profiles.sql`
- Create: `models/staging/vistareserve/stg_vistareserve__reservations.sql`
- Create: `models/staging/vistareserve/stg_vistareserve__pos_transactions.sql`
- Create: `models/staging/vistareserve/stg_vistareserve__revenue_batches.sql`
- Modify: `models/staging/vistareserve/_models.yml`

**Steps:**
1. Develop staging models for the remaining VistaReserve entities, sourcing the customer profiles from its base model.
2. Standardize column naming and recast financial and timestamp fields.
3. Update `_models.yml` to define descriptions, business meaning, testing logic, and hash collisions where appropriate.

**Verification:**
- `dbt build --select tag:staging` runs successfully.
- `sqlfluff lint` passes on all staging SQL files.

**Standards Compliance:**
- STG-YML-04, ALL-TST-02

### Task 3.4: Staging Layer Qualitative Code Review

**Steps:**
1. Pause execution.
2. Request user review of the Phase 3 models spanning naming conventions, description substantiveness, and test rigor.
3. Proceed to Phase 4 only upon user approval.

---

## Phase 4: Integration Models

Align organizational entities into their authoritative Microsoft CDM form.

### Task 4.1: Integrate Parks dimension (int_parks)

**Files:**
- Create: `models/integration/int_parks.sql`
- Create: `models/integration/_models.yml`

**Steps:**
1. Build `int_parks`. Union `stg_geoparks__parks_master` and `stg_vistareserve__parks`.
2. Apply the chosen reconciliation strategy (from Open Question 1) to match identical physical locations.
3. Prefer GeoParks as authoritative, mapping final columns exactly to the `FunctionalLocation` CDM entity definition.
4. Generate `parks_sk`, deduplicate rows, and drop any field outside the CDM bounds.
5. Define in `_models.yml` with strict surrogate key testing.

**Verification:**
- `int_parks` compiles and produces exactly 50 rows.
- Schema conformity aligns entirely with `FunctionalLocation` definitions sourced from `source_data/cdm_metadata/`.

**Standards Compliance:**
- SQL-INT-01 to SQL-INT-12, INT-YML-01 to INT-YML-03

### Task 4.2: Integrate Auxiliary Dimensions

**Files:**
- Create: `models/integration/int_contacts.sql`
- Create: `models/integration/int_customer_assets.sql`
- Modify: `models/integration/_models.yml`

**Steps:**
1. Build `int_contacts` (mapped to `Contact`) and `int_customer_assets` (mapped to `CustomerAsset`).
2. Add surrogate keys and filter out non-CDM columns.
3. Define models and PK tests in `_models.yml`.

**Verification:**
- Valid row counts observed using `dbt show`.

**Standards Compliance:**
- SQL-INT-05, SQL-INT-06

### Task 4.3: Integrate Transactions and Reservations

**Files:**
- Create: `models/integration/int_transactions.sql`
- Create: `models/integration/int_reservations.sql`
- Modify: `models/integration/_models.yml`

**Steps:**
1. Create `int_transactions` (mapped to `Transaction`); union POS transactions and revenue batches if profiling confirms compatible grain.
2. Create `int_reservations` (mapped to `Visit`).
3. Add foreign key tests in `_models.yml` referencing parent models per INT-YML-04.
4. Add cardinality and business logic tests per INT-YML-05 and INT-YML-06.

**Verification:**
- `dbt build --select models/integration` completes with no constraint failures.

**Standards Compliance:**
- INT-YML-04, INT-YML-05, INT-YML-06, INT-YML-08

### Task 4.4: Integration Layer Qualitative Code Review

**Steps:**
1. Pause execution.
2. Request user review of the Phase 4 models, specifically checking join logic, proper CDM schema alignment, and resolution of the Open Questions.
3. Proceed to Phase 5 only upon user approval.

---

## Phase 5: Mart Models

Shape data for downstream analytics utilizing explicit interface contracts.

### Task 5.1: Build Revenue Dimensions

**Files:**
- Create: `models/marts/revenue/dim_parks.sql`
- Create: `models/marts/revenue/dim_customers.sql`
- Create: `models/marts/revenue/dim_reservation_inventory.sql`
- Create: `models/marts/revenue/_models.yml`

**Steps:**
1. Construct dimensions consuming the corresponding `int_` models.
2. Bring in upstream descriptive fields from staging to enrich the CDM foundation.
3. Construct the YAML configuration enforcing public contracts (`contract: {enforced: true}` and data types per column).

**Verification:**
- `sqlfluff lint` passes across all dimension models.

**Standards Compliance:**
- SQL-DIM-01 to SQL-DIM-09, MRT-YML-01 to MRT-YML-05

### Task 5.2: Build Revenue Fact Models

**Files:**
- Create: `models/marts/revenue/fct_reservations.sql`
- Create: `models/marts/revenue/fct_pos_transactions.sql`
- Modify: `models/marts/revenue/_models.yml`

**Steps:**
1. Construct fact matrices mapping to integration keys.
2. Produce derived measures (e.g., nights stayed in reservations).
3. Secure the grain using explicit uniqueness testing in YAML, configuring strict contracts.

**Verification:**
- Validation tests pass covering foreign keys to the dimensional layer.

**Standards Compliance:**
- SQL-FCT-01 to SQL-FCT-08, MRT-YML-03 to MRT-YML-05

### Task 5.3: Build Park Revenue Summary Report

**Files:**
- Create: `models/marts/revenue/rpt_park_revenue_summary.sql`
- Modify: `models/marts/revenue/_models.yml`

**Steps:**
1. Aggregate facts incrementally to a park-month grain, consuming `fct_reservations`, `fct_pos_transactions`, and `dim_parks`.
2. Output summarized measures representing both total volume and average values.

**Verification:**
- Successfully compiles and generates a row-count congruent with active park-months.

**Standards Compliance:**
- SQL-RPT-01 to SQL-RPT-07

### Task 5.4: Marts Layer Qualitative Code Review

**Steps:**
1. Pause execution.
2. Request user review of the Phase 5 models, focusing on dimensional modeling standards, derived measure logic, and exposure configurations.
3. Proceed to Phase 6 only upon user approval.

---

## Phase 6: Seeds, Macros, and Singular Tests

Operationalize metadata and cross-pipeline intelligence.

### Task 6.1: Define Required Macros

**Files:**
- Create: `macros/generate_source_system_tag.sql`
- Create: `macros/clean_string.sql`
- Create: `macros/cast_park_id_to_varchar.sql`
- Create: `macros/_macros.yml`

**Steps:**
1. Author the three macros as declared to fulfill string manipulation, ID type conversion, and system tagging.
2. Document in `_macros.yml` identifying argument inputs.

**Verification:**
- Models using these macros compile without issues.

**Standards Compliance:**
- SQL-MAC-01 to SQL-MAC-04, MAC-YML-01 to MAC-YML-03

### Task 6.2: Implement Reference Seeds

**Files:**
- Create: `seeds/reservation_status_codes.csv`
- Create: `seeds/transaction_type_codes.csv`
- Create: `seeds/park_region_mappings.csv`
- Create: `seeds/source_system_registry.csv`
- Create: `seeds/_seeds.yml`

**Steps:**
1. Generate the CSV seed files defining categories mapped from specifications.
2. Register testing rules in `_seeds.yml` enforcing data type expectations.

**Verification:**
- `dbt seed` builds table schemas and populates with expected rows.

**Standards Compliance:**
- SQL-SEED-01 to SQL-SEED-05

### Task 6.3: Implement Singular Logic Tests

**Files:**
- Create: `tests/integration/assert_no_orphan_parks_in_reservations.sql`
- Create: `tests/integration/assert_park_ids_reconciled.sql`
- Create: `tests/marts/assert_revenue_sums_balance.sql`

**Steps:**
1. Establish tests designed to trip constraints when orphaned entities emerge.
2. Confirm revenue parity matching between fact aggregations (`fct` tables) and the summary layer (`rpt` table).

**Verification:**
- `dbt test --select tests` finishes cleanly.

**Standards Compliance:**
- SQL-TST-01 to SQL-TST-04

---

## Phase 7: Linting and Governance Verification

Solidify the boundary between automated tools and analytical judgment.

### Task 7.1: Evaluate Adherence Reports

**Steps:**
1. Run `sqlfluff lint` against the entire directory stack, remediating syntax issues or excessive lengths.
2. Execute `dbt-score score` to measure test-to-column ratio thresholds and description quality.
3. Trigger evaluations through `dbt-project-evaluator` identifying potential layer skews or reversed DAG dependencies.

**Verification:**
- All tools report healthy scores above predefined organizational norms.

---

## Phase 8: End-to-End Validation

Assert operational readiness for downstream customers.

### Task 8.1: Full Pipeline Verification

**Steps:**
1. Perform a clean build: `dbt build --full-refresh`.
2. Ensure row counts match SPEC metrics (e.g. exactly 50 distinct parks, exact transactional equivalence).
3. Validate output logs confirm no deprecated macros or configuration syntax warnings.

**Verification:**
- `dbt build` displays 0 errors.

---

## Implications and Recommendations

With the successful execution of this slice, DCR secures a replicable modeling architecture governing ten fragmented data sources. We advise establishing clarity on the customer PII extraction approach concurrent with Phase 3 to avoid refactoring customer integration pipelines later. Once the Revenue & Reservations domain matures and establishes trust, the blueprint created here will support the addition of the Finance vertical as its direct successor.
