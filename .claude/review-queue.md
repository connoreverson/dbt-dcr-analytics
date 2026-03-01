# Audit Review Queue
Generated: 2026-02-27
Last Updated: 2026-02-27

## Status: PARTIALLY RESOLVED

### Resolved in this session (critical + high issues fixed, dbt build: 224/225 pass):
- **C-01** FIXED — Hash keys (hk_*) added to all 8 staging models + YAML tests
- **C-02** FIXED — Integration YAML fully documented: column names corrected + 50+ missing columns added
- **H-02** FIXED — generate_cdm_projection raises compiler_error on missing crosswalk (no more silent empty SQL)
- **H-03** FIXED — int_parks row_number() has deterministic parks_sk tiebreaker
- **H-04** FIXED — printf park ID logic extracted to get_geoparks_account_number macro
- **H-05** FIXED — FK relationship test rpt_park_revenue_summary → dim_parks added
- **H-06** FIXED — not_null tests on all integration business keys
- **H-07** FIXED — Cardinality test on int_reservations vs staging source
- **H-08** FIXED — Range tests on transaction_amount and reservation_amount (warn severity)
- **H-09** FALSE POSITIVE — rpt_park_revenue_summary already had contract enforced
- **H-10** FIXED — Cardinality test on int_customer_assets vs staging source
- **H-11** FIXED — park_id FK + not_null tests on stg__inventory_assets and stg__pos_transactions
- **H-01** FALSE POSITIVE — int_contacts correctly produces mobilephone (CDM alias)
- **C-03** FALSE POSITIVE (resolved anyway) — test used correct msnvo_visitid; YAML now corrected to match

---

---

## CRITICAL (3 issues)

### C-01: Staging models missing hash keys (hk_*)
**Files**: All 9 staging models under `models/staging/`
**Rule**: SQL-STG-07, STG-YML-03
**Description**: Every staging model must produce an `hk_<entity>` surrogate key via `dbt_utils.generate_surrogate_key()`. None of the 9 staging models implement this. This is a foundational gap.
**Affected models**: stg_vistareserve__parks, stg_vistareserve__customer_profiles, stg_vistareserve__inventory_assets, stg_vistareserve__asset_crosswalks, stg_vistareserve__pos_transactions, stg_vistareserve__reservations, stg_vistareserve__revenue_batch, stg_geoparks__parks_master, + base models
**Fix**: Add `dbt_utils.generate_surrogate_key([...]) as hk_<entity>` to each staging model's final CTE. Add `unique` + `not_null` tests in YAML.
**Effort**: large

### C-02: Integration layer YAML massively under-documented
**Files**: `models/integration/_models.yml`
**Rule**: YML-SYNC-01
**Description**: Every integration model YAML documents only 2–5 columns, but the actual SQL output (via `generate_cdm_projection` macro + pass_through_columns) produces 10–15+ columns per model. Gaps:
- `int_contacts`: missing firstname, lastname, emailaddress1, mobilephone, address_state, account_created_at, has_annual_pass, is_senior, is_veteran, source_system
- `int_parks`: missing description, address1_city, address1_stateorprovince, address1_postalcode, address1_latitude, address1_longitude, source_system, total_acres, classification, region_id
- `int_customer_assets`: missing name, asset_type, pet_policy, utility_hookup, max_occupancy, is_ada_accessible, source_system
- `int_transactions`: missing revenue_category, is_kiosk_entry, transaction_created_at, source_system
- `int_reservations`: missing reservation_status, total_amount, arrival_date, departure_date, reservation_created_at, booking_source, promo_code, number_of_guests, source_system
- `int_cdm_columns`: missing dbt_data_type, is_primary_key, is_foreign_key, description
**Fix**: For each model, run `dbt show --select <model> --limit 1`, capture the actual column list, and update YAML accordingly.
**Effort**: medium

### C-03: Singular test references non-existent column
**File**: `tests/integration/assert_no_orphan_parks_in_reservations.sql:4`
**Rule**: SQL-TST-04
**Description**: The test selects `r.msnvo_visitid` but `int_reservations` documents the column as `visit_id`. This will fail at runtime.
**Code**: `r.msnvo_visitid`
**Fix**: Change to `r.visit_id`
**Effort**: small

---

## HIGH (11 issues)

### H-01: dim_customers.sql references `mobilephone` — likely runtime failure
**File**: `models/marts/revenue/dim_customers.sql`
**Description**: `dim_customers` selects `mobilephone as phone` from `int_contacts`. But `int_contacts` is generated from `stg_vistareserve__customer_profiles` which has a column named `phone`. If `int_contacts` does not produce a `mobilephone` CDM alias that dim_customers can consume, this will fail at runtime. Needs verification against actual `dbt show` output of `int_contacts`.
**Fix**: Run `dbt show --select int_contacts --limit 1`. If column is `phone` (not `mobilephone`), change `dim_customers.sql` accordingly.
**Effort**: small

### H-02: `generate_cdm_projection` returns empty string on missing crosswalk
**File**: `macros/generate_cdm_projection.sql:26`
**Description**: `{{ return('') }}` on line 26 produces invalid SQL if no crosswalk entries found. Should raise a compiler error instead.
**Code**: `{{ return('') }}`
**Fix**: Replace with `{% do exceptions.raise_compiler_error("No crosswalk entries found for " ~ integration_model ~ " / " ~ source_model) %}`
**Effort**: small

### H-03: Non-deterministic fuzzy deduplication in int_parks
**File**: `models/integration/int_parks.sql`
**Description**: `row_number()` partitioned by `clean_string('name')` with ORDER BY `source_system` priority is non-deterministic when two parks share the same source system AND have identical cleaned names.
**Fix**: Add secondary tiebreaker: `order by case when source_system = 'DCR-GEO-01' then 1 else 2 end, parks_sk`
**Effort**: small

### H-04: Duplicate printf park ID crosswalk logic in two models
**Files**: `models/integration/int_transactions.sql:32`, `models/integration/int_customer_assets.sql:23`
**Description**: `printf('GP-%03d', source.park_id) = source_parks.accountnumber` is duplicated in both files. This is fragile and creates maintenance drift.
**Fix**: Extract to a macro `get_geoparks_account_number(park_id)` that returns `printf('GP-%03d', park_id)`. Call it from both models.
**Effort**: small

### H-05: Missing FK relationship test from rpt_park_revenue_summary → dim_parks
**File**: `models/marts/revenue/_models.yml` (rpt_park_revenue_summary)
**Description**: `rpt_park_revenue_summary` has no `relationships` test on `parks_sk`. Parks in fact tables but missing from dim_parks will silently drop from the report.
**Fix**: Add `relationships: to: ref('dim_parks'), field: parks_sk` test on the `parks_sk` column.
**Effort**: small

### H-06: Missing NOT_NULL tests on business keys in integration models
**Files**: `models/integration/_models.yml`
**Description**: The following business key columns have no `not_null` test, making reconciliation impossible if NULLs appear:
- `int_contacts.contact_id`
- `int_parks.accountnumber`
- `int_customer_assets.customerasset_id`
- `int_transactions.transaction_id`
- `int_reservations.visit_id`
**Fix**: Add `- not_null` test to each business key column in `_models.yml`.
**Effort**: small

### H-07: Missing cardinality test on int_reservations
**File**: `models/integration/_models.yml` (int_reservations)
**Description**: `int_reservations` does LEFT JOINs to `int_contacts` and `int_customer_assets`. No row-count test exists to detect silent join failures. Compare with `stg_vistareserve__reservations`.
**Fix**: Add `dbt_expectations.expect_table_row_count_to_equal_other_table` at the model level pointing to `stg_vistareserve__reservations`.
**Effort**: small

### H-08: No range/value tests on financial fact columns
**Files**: `models/marts/revenue/_models.yml` (fct_pos_transactions, fct_reservations)
**Description**: `transaction_amount` and `reservation_amount` have zero tests. Negative values or extreme outliers would be undetected.
**Fix**: Add `dbt_expectations.expect_column_values_to_be_between` with `min_value: 0` (warn severity) to both columns.
**Effort**: small

### H-09: rpt_park_revenue_summary missing contract enforcement
**File**: `models/marts/revenue/_models.yml` (rpt_park_revenue_summary)
**Rule**: MRT-YML-04
**Description**: `rpt_park_revenue_summary` is a mart model but lacks `contract: {enforced: true}`. All mart models must have enforced contracts per the standard.
**Fix**: Add `config: contract: enforced: true` to the model's YAML config block.
**Effort**: small

### H-10: Missing cardinality test on int_customer_assets
**File**: `models/integration/_models.yml` (int_customer_assets)
**Description**: `int_customer_assets` does a LEFT JOIN to `int_parks`. If assets fail to match a park, `_parent_park_sk` will be NULL. No row-count test exists to catch silent join failures.
**Fix**: Add `dbt_expectations.expect_table_row_count_to_equal_other_table` pointing to `stg_vistareserve__inventory_assets`.
**Effort**: small

### H-11: stg_vistareserve__inventory_assets missing park_id FK test
**File**: `models/staging/vistareserve/_vistareserve__models.yml`
**Description**: `park_id` on inventory assets is the FK that drives the `int_customer_assets` join to parks. It has no `not_null` or `relationships` test at the staging layer.
**Fix**: Add `not_null` and `relationships: to: ref('stg_vistareserve__parks'), field: park_id` to `park_id` column.
**Effort**: small

---

## MEDIUM (13 issues)

### M-01: All models use `select * from final` instead of explicit column list
**Files**: All 20 models (staging, integration, mart)
**Description**: Every model's final select is `select * from final`. This obscures the contract and makes static analysis harder.
**Fix**: Replace with explicit column lists. Low priority on staging (columns defined in final CTE); higher priority on integration/mart where output is less obvious.
**Effort**: large (across all files)

### M-02: Hardcoded park size tier thresholds in dim_parks
**File**: `models/marts/revenue/dim_parks.sql:28-44`
**Description**: Size tiers (500, 5000 acres) hardcoded. Should be in a seed.
**Fix**: Create seed `park_size_tiers.csv` or move thresholds to a `var()`.
**Effort**: medium

### M-03: Hardcoded state-to-region mapping in dim_customers
**File**: `models/marts/revenue/dim_customers.sql:27-38`
**Description**: State abbreviation lists for geographic regions hardcoded in CASE WHEN. Should be in a seed table.
**Fix**: Create `seed_state_region_mappings.csv` and join to it.
**Effort**: medium

### M-04: Hardcoded capacity tier thresholds in dim_reservation_inventory
**File**: `models/marts/revenue/dim_reservation_inventory.sql:59-65`
**Description**: Capacity tiers (1-4, 5-8, 9+) hardcoded.
**Fix**: Externalize to seed or var().
**Effort**: medium

### M-05: Base model descriptions use red-flag language
**File**: `models/staging/vistareserve/base/_vistareserve__base_models.yml`
**Description**: Description for `base_vistareserve__customer_profiles` says "deduplicate profiles" — rule YML-DOC-02 forbids test rationale in descriptions. Rewrite to focus on business meaning.
**Fix**: "Pre-processed customer profiles from VistaReserve, retaining the most recently created record per customer as the authoritative profile."
**Effort**: small

### M-06: Missing accepted_values tests on categorical columns
**Files**: Multiple staging YAML files
**Description**: No `accepted_values` tests on: `classification` (stg_vistareserve__parks), `revenue_category` (stg_vistareserve__pos_transactions), `reservation_status` (stg_vistareserve__reservations).
**Fix**: Add `accepted_values` tests with warn severity for each.
**Effort**: small

### M-07: YAML staging file naming inconsistency
**Files**: `_vistareserve__models.yml`, `_geoparks__models.yml`, `_vistareserve__base_models.yml`
**Description**: YAML files use double-underscore source prefix pattern (reserved for SQL naming). SPEC implies `_models.yml`.
**Fix**: Rename to `_models.yml` in each subdirectory.
**Effort**: small

### M-08: cdm_crosswalk seed has no YAML entry
**File**: `seeds/_seeds.yml`
**Description**: `seeds/cdm_crosswalk.csv` exists and is used at compile time by `generate_cdm_projection` but has no entry in `_seeds.yml`. Rule SQL-SEED-05 requires all seeds to be documented.
**Fix**: Add `cdm_crosswalk` entry to `_seeds.yml` with column descriptions and `not_null`/uniqueness tests on the composite key `(integration_model, source_model, cdm_column_name)`.
**Effort**: small

### M-09: Missing date order tests at staging layer for reservations
**File**: `models/staging/vistareserve/_vistareserve__models.yml` (stg_vistareserve__reservations)
**Description**: `departure_date > arrival_date` is tested in the integration layer but not at staging, where violations would be caught earlier.
**Fix**: Add `dbt_expectations.expect_column_pair_values_A_to_be_greater_than_B` to `departure_date` at the staging level.
**Effort**: small

### M-10: Missing date order test on fct_reservations.check_out_date
**File**: `models/marts/revenue/_models.yml` (fct_reservations)
**Description**: Date order validated at integration but not re-asserted at the fact layer. If the mart transformation accidentally inverts dates, the integration test won't catch it.
**Fix**: Add `dbt_expectations.expect_column_pair_values_A_to_be_greater_than_B` on `check_out_date` vs `check_in_date`.
**Effort**: small

### M-11: Missing NOT_NULL on stg_vistareserve__pos_transactions.park_id
**File**: `models/staging/vistareserve/_vistareserve__models.yml`
**Description**: `park_id` on POS transactions has a `relationships` test but no `not_null`. A transaction must always occur at a park.
**Fix**: Add `- not_null` test.
**Effort**: small

### M-12: Missing tests on rpt_park_revenue_summary measure columns
**File**: `models/marts/revenue/_models.yml` (rpt_park_revenue_summary)
**Description**: All `coalesce(..., 0)` measure columns (total_reservations, total_reservation_revenue, total_pos_transactions, etc.) have no `not_null` or range tests. The `coalesce` means they should never be NULL.
**Fix**: Add `not_null` and `dbt_expectations.expect_column_values_to_be_between` (min: 0) to each measure.
**Effort**: medium

### M-13: Park reconciliation decision not documented in SPEC or reference docs
**File**: `models/integration/int_parks.sql` (inline comment), `reference/SPEC_vertical_slice_revenue.md`
**Description**: SPEC left Open Question #1 (Park ID Reconciliation) open. The code resolved it via fuzzy string matching but this was never recorded as a decision in the SPEC. Future developers will not know this was a deliberate architectural choice.
**Fix**: Update `reference/SPEC_vertical_slice_revenue.md` to record the decision: fuzzy name matching was chosen over consuming the stale crosswalk. Document GeoParks as system of record.
**Effort**: small

---

## LOW (7 issues)

### L-01: Redundant `cast(... as varchar)` on surrogate keys in fct_ models
**Files**: `models/marts/revenue/fct_pos_transactions.sql:9-20`, `models/marts/revenue/fct_reservations.sql:9-14`
**Description**: Surrogate keys are already varchar from upstream; recasting is redundant.
**Fix**: Remove redundant casts.
**Effort**: small

### L-02: Redundant double-cast on total_acres in dim_parks
**File**: `models/marts/revenue/dim_parks.sql:16`
**Description**: `cast(int_parks.total_acres as decimal(10, 2))` recasts a column already decimal from staging.
**Fix**: Remove redundant cast: `int_parks.total_acres as acreage`.
**Effort**: small

### L-03: Missing secondary ORDER BY tiebreaker in base_vistareserve__customer_profiles
**File**: `models/staging/vistareserve/base/base_vistareserve__customer_profiles.sql:7-14`
**Description**: `row_number()` is non-deterministic if two records share identical `customer_id` and `created_at`.
**Fix**: Add tiebreaker to ORDER BY.
**Effort**: small

### L-04: nullif() missing on concat_ws amenities in dim_reservation_inventory
**File**: `models/marts/revenue/dim_reservation_inventory.sql:26-38`
**Description**: `concat_ws` returns empty string `''` when no conditions match, not NULL. Downstream code may not distinguish empty string from no amenities.
**Fix**: Wrap with `nullif(concat_ws(...), '')`.
**Effort**: small

### L-05: Missing tests on park_region_mappings and cdm seeds
**File**: `seeds/_seeds.yml`
**Description**: `park_region_mappings` seed has no column-level tests (no unique/not_null on region_code). CDM catalog seeds (`column_catalog_*`) similarly untested.
**Fix**: Add basic unique + not_null tests to primary key columns.
**Effort**: small

### L-06: Missing base model YAML description quality
**File**: `models/staging/vistareserve/base/_vistareserve__base_models.yml`
**Description**: `base_vistareserve__asset_crosswalks` description focuses on "how long it has been since manually verified" — operational, not business-oriented.
**Fix**: Lead with grain and entity: "One-row-per-asset mapping between VistaReserve, GeoParks, and InfraTrak identifiers. Includes staleness indicator (days since last manual verification) to support data quality monitoring."
**Effort**: small

### L-07: Hardcoded source system codes across models
**Files**: `models/integration/int_parks.sql:29,50`, similar in other int_ models
**Description**: `'DCR-GEO-01'`, `'DCR-REV-01'` hardcoded in multiple places. Should be centralized.
**Fix**: Create `seed_source_systems.csv` or project vars.
**Effort**: medium

---

## Queue Summary
| Severity | Count |
|----------|-------|
| Critical | 3 |
| High     | 11 |
| Medium   | 13 |
| Low      | 7 |
| **Total** | **34** |
