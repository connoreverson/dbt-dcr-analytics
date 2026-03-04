# DAMA Data Quality Remediation — Implementation Tasks

**Created:** 2026-03-04
**Source:** `reference/plans/2026-03-04-dama-data-quality-remediation.md`
**Context:** [DAMA Data Quality Review](file:///C:/Users/conno/.gemini/antigravity/brain/9f10084a-a54e-4c27-a171-c4081ff2ec07/dama_data_quality_review.md) identified 15 action items across all six DAMA dimensions. This document provides self-contained implementation tasks.

> [!IMPORTANT]
> Before starting, read `reference/dbt_project_standards.md` and `reference/SPEC_vertical_slice_revenue.md`. Follow all operating principles in `GEMINI.md`, especially #1 (standards are law), #12 (formatting nuances), #13 (description quality), #17 (YAML/SQL alignment), and #24 (auto-run safe commands).

---

## Open Decisions (Ask the User)

These two questions were raised during the review and need answers before tasks 10 and 11 can proceed:

1. **Negative financial amounts** — Are negative `amount` values in `stg_stategov__general_ledger` valid (e.g., reversals/adjustments), or invalid data entry errors? Answer determines whether task 10 enforces `min_value: 0` or documents negatives as expected.
2. **Customer deduplication strategy** — Should `int_contacts` filter out merged duplicates using `merged_into_customer_id`, pass all profiles through with an `is_merged_duplicate` flag, or defer? Answer determines task 11 scope.

---

## Priority 1 — Structural Gaps

### Task 1: Add Contract Enforcement to Non-Revenue Mart Models

**Goal:** Prevent schema drift on 7 mart models that lack `contract: enforced: true`.

**Files to modify:**
- `models/marts/core/_core_models.yml` — add to `dim_date`, `dim_assets`, `dim_employees`
- `models/marts/finance/_finance_models.yml` — add to `dim_vendors`
- `models/marts/operations/_operations_models.yml` — add to `fct_incidents_and_maintenance`
- `models/marts/attendance/_attendance_models.yml` — add to `fct_visitation`
- `models/marts/reporting/_reporting_models.yml` — add to `rpt_agency_performance`

**Steps:**
1. For each model above, add `config: contract: enforced: true` under the model entry.
2. For each model, add `data_type:` to every column in the YAML.
3. To determine the correct data types, run `dbt show --select <model_name> --limit 1` and inspect the output column types.
4. After adding contracts, run `dbt build --select <model_name>` for each to verify no contract violations.

**Verification:** `dbt build` passes for all 7 models with contracts enforced.

---

### Task 2: Add Row Count Guards on Integration Unions

**Goal:** Detect upstream record loss or unexpected volume changes on 3 integration models that union multiple sources.

**Files to modify:**
- `models/integration/_models.yml`

**Steps:**
1. Add `dbt_expectations.expect_table_row_count_to_be_between` to each model's `tests:` block:
   - `int_parks`: `min_value: 40`, `max_value: 100` (50 known parks, with buffer)
   - `int_physical_assets`: `min_value: 10000`, `max_value: 20000` (2,602 InfraTrak + 10,913 GeoParks)
   - `int_ecological_surveys`: `min_value: 12000`, `max_value: 18000` (9,550 + 2,450 + 2,500 = 14,500)
2. Run `dbt build --select int_parks int_physical_assets int_ecological_surveys` to verify.

**Verification:** All 3 row count tests pass.

---

### Task 3: Add Relationship Tests on Remaining Marts

**Goal:** Close FK integrity gaps on mart models missing `relationships` tests.

**Files to modify:**
- `models/marts/reporting/_reporting_models.yml` — add `relationships` test on `rpt_agency_performance.parks_sk` → `ref('dim_parks').parks_sk`
- `models/marts/finance/_finance_models.yml` — verify `fct_expenditures` has `relationships` to `dim_vendors` (if `fct_expenditures` exists and references vendors)

**Steps:**
1. Open each YAML file and check if the `parks_sk` or `vendor_sk` column has a `relationships` test.
2. If missing, add:
   ```yaml
   tests:
     - relationships:
         to: ref('dim_parks')
         field: parks_sk
   ```
3. Run `dbt build --select rpt_agency_performance fct_expenditures` to verify.

**Verification:** Relationship tests pass.

---

## Priority 2 — Validity & Accuracy (Data Entry Controls)

### Task 4: Add `accepted_values` on Reservation Status

**File:** `models/staging/vistareserve/_vistareserve__models.yml`

**Steps:**
1. Find the `stg_vistareserve__reservations` model entry.
2. Add `accepted_values` test on the `reservation_status` column.
3. First, inspect actual values: run `dbt show --inline "select distinct reservation_status from {{ ref('stg_vistareserve__reservations') }}"`.
4. Use the observed values in the test. Expected: `['Confirmed', 'Cancelled', 'Completed', 'No-Show']` (verify against actual data).
5. Run `dbt test --select stg_vistareserve__reservations`.

---

### Task 5: Add Date Ordering Test on Reservations

**Files:**
- `models/staging/vistareserve/_vistareserve__models.yml`
- `models/marts/revenue/_models.yml`

**Steps:**
1. Add to `stg_vistareserve__reservations`:
   ```yaml
   tests:
     - dbt_expectations.expect_column_pair_values_A_to_be_greater_than_B:
         column_A: departure_date
         column_B: arrival_date
         or_equal: false
         config:
           severity: warn
   ```
2. Add same pattern to `fct_reservations` using `check_out_date` and `check_in_date`.
3. Run `dbt test --select stg_vistareserve__reservations fct_reservations`.

> [!NOTE]
> Check the exact dbt_expectations test name by running `dbt docs generate` or consulting the [dbt-expectations docs](https://github.com/calogica/dbt-expectations). The test may be `expect_column_pair_values_A_to_be_greater_than_B` or a similar variant.

---

### Task 6: Add FCI Score Range Test

**File:** `models/staging/infratrak/_infratrak__models.yml`

**Steps:**
1. Find the `stg_infratrak__condition_assessments` model.
2. Add to the `fci_score` column:
   ```yaml
   tests:
     - dbt_expectations.expect_column_values_to_be_between:
         min_value: 1
         max_value: 100
   ```
3. Run `dbt test --select stg_infratrak__condition_assessments`.

---

### Task 7: Add GPS Coordinate Bounds

**Files:**
- `models/staging/biosurvey/_biosurvey__models.yml` — `stg_biosurvey__flora_fauna_surveys` (latitude, longitude)
- `models/staging/infratrak/_infratrak__models.yml` — `stg_infratrak__assets` (latitude, longitude)

**Steps:**
1. For each latitude column, add:
   ```yaml
   tests:
     - dbt_expectations.expect_column_values_to_be_between:
         min_value: -90
         max_value: 90
         config:
           where: "latitude is not null"
   ```
2. For each longitude column, same with `min_value: -180`, `max_value: 180`.
3. Run `dbt test --select stg_biosurvey__flora_fauna_surveys stg_infratrak__assets`.

---

### Task 8: Add Email Format Validation

**File:** `models/staging/vistareserve/_vistareserve__models.yml`

**Steps:**
1. Add to the `email` column of `stg_vistareserve__customer_profiles`:
   ```yaml
   tests:
     - dbt_expectations.expect_column_values_to_match_regex:
         regex: "^[^@]+@[^@]+\\.[^@]+$"
         config:
           severity: warn
           where: "email is not null"
   ```
2. Run `dbt test --select stg_vistareserve__customer_profiles`.

---

### Task 9: Add Max Occupancy Positive-Value Check

**File:** `models/staging/vistareserve/_vistareserve__models.yml`

**Steps:**
1. Add to `max_occupancy` on `stg_vistareserve__inventory_assets`:
   ```yaml
   tests:
     - dbt_expectations.expect_column_values_to_be_between:
         min_value: 1
         max_value: 1000
   ```
2. Run `dbt test --select stg_vistareserve__inventory_assets`.

---

### Task 10: Clarify and Test Financial Amount Sign Conventions

**Depends on:** Open Decision #1 (negative amounts).

**Files:**
- `models/staging/stategov/_stategov__models.yml`
- `models/integration/_models.yml`

**Steps (if negatives are invalid):**
1. Add `expect_column_values_to_be_between` with `min_value: 0` on `amount` in `stg_stategov__general_ledger` and `int_financial_transactions`.

**Steps (if negatives are valid reversals):**
1. Add a comment in the staging SQL and a `meta:` note in the YAML documenting that negative amounts represent reversals.
2. Consider adding `expect_column_values_to_be_between` with a very wide range (e.g., -10000000 to 10000000) as a guard against implausible values.

---

## Priority 3 — Completeness & Deduplication

### Task 11: Formalize Customer Deduplication Strategy

**Depends on:** Open Decision #2 (dedup strategy).

**Files:**
- `models/integration/int_contacts.sql`
- `models/integration/_models.yml`

**Option A — Filter merged duplicates:**
1. Add a `where merged_into_customer_id is null` filter in `int_contacts.sql` to exclude profiles that have been merged into another.
2. Update YAML description to document this filter.
3. Update `int_contacts` row count tests accordingly.

**Option B — Pass through with flag:**
1. Add `is_merged_duplicate` column (boolean, true when `merged_into_customer_id is not null`) to `int_contacts.sql`.
2. Add column to YAML with description.
3. Update downstream marts to document expected behavior.

---

### Task 12: Add `not_null` Tests on Critical Dimension Attributes

**Files:**
- `models/marts/core/_core_models.yml`
- `models/marts/finance/_finance_models.yml`
- `models/marts/revenue/_models.yml`

**Steps:**
1. Add `not_null` tests (with `severity: warn` where the source is known to have gaps) on:
   - `dim_parks.park_name`
   - `dim_vendors.vendor_name`
   - `dim_customers.customer_name`
   - `dim_assets.feature_class`
   - `dim_employees.job_classification`
2. Run `dbt test --select dim_parks dim_vendors dim_customers dim_assets dim_employees`.

---

### Task 13: Add Completeness Thresholds on JSON-Extracted Fields

**File:** `models/staging/vistareserve/_vistareserve__models.yml`

**Steps:**
1. Add to `equipment_preference` and `accessibility_needs` on `stg_vistareserve__customer_profiles`:
   ```yaml
   tests:
     - dbt_expectations.expect_column_values_to_not_be_null:
         row_condition: "1=1"
         mostly: 0.3
         config:
           severity: warn
   ```
2. Add same pattern to `booking_source` on `stg_vistareserve__reservations`.
3. Run `dbt test --select stg_vistareserve__customer_profiles stg_vistareserve__reservations`.

> [!NOTE]
> The `mostly` threshold should be set based on expected null rates. `0.3` means "at least 30% non-null." Adjust after inspecting actual data with `dbt show`.

---

## Priority 4 — Timeliness (Demo-Ready)

### Task 14: Implement Demo-Friendly Freshness Checks

**Files:**
- `models/staging/trafficcount/_sources.yml`

**Steps:**
1. Add `loaded_at_field: _loaded_at` and `freshness:` block to all 4 TrafficCount tables:
   ```yaml
   tables:
     - name: sensor_locations
       loaded_at_field: _loaded_at
       freshness:
         warn_after: {count: 365, period: day}
         error_after: {count: 730, period: day}
   ```
2. Repeat for `vehicle_counts`, `pedestrian_cyclist_counts`, and `derived_visitor_metrics`.
3. VistaReserve already has freshness configured on 4 tables — verify those still work.
4. Run `dbt source freshness` and confirm it produces output for all 8 tables without errors.
5. Document in each source's `meta: freshness_policy:` block: "Demo threshold. Production recommendation: [specific value from existing freshness_policy text]."

**Verification:** `dbt source freshness` runs and reports status for 8 tables. No `error` status unless data is genuinely older than 2 years.

---

### Task 15: Add Staleness Test on Asset Crosswalk

**File:** `models/staging/vistareserve/_vistareserve__models.yml`

**Steps:**
1. Add to `stg_vistareserve__asset_crosswalks`:
   ```yaml
   tests:
     - dbt_expectations.expect_column_max_to_be_between:
         column_name: days_since_last_update
         min_value: 0
         max_value: 1825
         config:
           severity: warn
   ```
   (1825 days = 5 years, wide enough for the demo's 2022 staleness but still catches absurd values.)
2. Run `dbt test --select stg_vistareserve__asset_crosswalks`.

---

## Execution Notes

- **Run order:** Tasks 1–3 first (structural), then 4–9 (validity), then 12–15 (completeness/timeliness). Tasks 10–11 are blocked on open decisions.
- **Safe to auto-run:** All `dbt build`, `dbt test`, `dbt show`, and `dbt source freshness` commands. See Operating Principle #24.
- **Virtual environment:** Activate with `. .\.venv\Scripts\Activate.ps1` (PowerShell) or `source .venv/Scripts/activate` (Git Bash) before any dbt commands. See Operating Principle #10.
- **YAML/SQL alignment:** After any YAML change that adds columns, verify YAML columns match SQL output. See Operating Principle #17.
- **After completing all tasks:** Run `dbt build` on the full project to confirm no regressions.
