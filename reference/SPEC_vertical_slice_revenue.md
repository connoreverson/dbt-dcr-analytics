# Vertical Slice Specification: Revenue & Reservations

## Problem Statement

DCR operates ten disconnected source systems that have never been brought under a single analytical layer — and the consequences are predictable: business questions that span two systems require manual reconciliation, park-level revenue figures depend on which system you ask, and a customer who books a campsite and buys firewood at the point of sale exists as two unrelated records. This specification defines the first vertical slice of a dbt project that will unify those systems: the Revenue & Reservations domain, built on VistaReserve (DCR-REV-01) and anchored by the GeoParks (DCR-GEO-01) parks_master dimension. Every subsequent vertical slice — finance, human capital, assets, law enforcement, natural resources — will follow the patterns established here.

The slice is deliberately narrow; its purpose is to prove the architecture end-to-end before the project takes on broader scope. A working pipeline from source through staging, integration, and marts — with tested, documented, CDM-conforming models at every layer — is more valuable at this stage than partial coverage of all ten systems.

## Goals

1. **Establish the project foundation**: initialize a dbt project with dbt-core, the dbt-duckdb adapter, a Python virtual environment, required packages, and linting tooling (sqlfluff, dbt-score) so that all future development inherits a consistent, governed starting point.
2. **Deliver a complete Revenue & Reservations pipeline**: build source definitions, staging models, base models, integration models, fact and dimension models, and at least one report model for the VistaReserve and GeoParks-parks systems — exercising every layer defined in the dbt Project Standards.
3. **Resolve the parks dimension first**: produce a CDM-conforming integration model for parks that reconciles VistaReserve and GeoParks identifiers, because parks is the central dimension that every future vertical slice will reference.
4. **Demonstrate linting-as-governance**: configure sqlfluff and dbt-score with rules that enforce as much of the dbt Project Standards as automated tooling can cover, so that compliance is verifiable in CI rather than dependent on reviewer memory.
5. **Produce a replicable pattern**: document decisions, seeds, macros, and testing rationale thoroughly enough that a second analyst could build the next vertical slice (e.g., Finance via StateGov Financials) without ambiguity about conventions.

## Non-Goals

1. **No coverage of non-revenue source systems in this slice** — StateGov Financials, GrantTrack, InfraTrak, RangerShield, BioSurvey, PeopleFirst, TrafficCount, and LegacyRes will be addressed in subsequent slices. Including them here would expand scope without strengthening the architectural proof.
2. **No exposure definitions** — no external dashboards, analyses, or reverse-ETL syncs exist yet; exposures will be defined when downstream consumers are ready to declare their dependencies.
3. **No incremental materialization strategy** — all models in this slice will use view or table materialization. Incremental logic adds complexity that is better addressed once the full DAG is stable and performance profiling justifies it.
4. **No historical reservation data from LegacyRes (DCR-REV-02)** — the 2005–2021 archive uses three incompatible formats and a partial crosswalk covering only 15 parks. Integrating it is a separate effort that should follow the VistaReserve slice, not complicate it.
5. **No CI/CD pipeline configuration** — linting and testing will run locally during this slice. Automating them in a CI runner is a follow-on task.

---

## Source Systems in Scope

### DCR-REV-01: VistaReserve (7 tables)

Enterprise SaaS reservation and revenue platform; authoritative for reservations, POS transactions, customer profiles, pass management, and revenue batches since the March 2021 cutover. Sensitivity classification: Confidential (contains PII in customer_profiles).

| Source Table | Business Purpose | Known Quality Issues |
|---|---|---|
| `parks` | VistaReserve's internal park reference | INTEGER park IDs; not authoritative (GeoParks is) |
| `customer_profiles` | Known individuals who transact with DCR | 18–22% duplicate rate; PII fields |
| `inventory_assets` | Bookable inventory (campsites, cabins, shelters, day-use areas) | May reference stale asset_crosswalk |
| `reservations` | Reservation lifecycle records | Depends on customer_profiles and inventory_assets |
| `pos_transactions` | Point-of-sale purchases (firewood, passes, equipment) | Kiosk revenue gaps documented in data inventory |
| `revenue_batch` | Batched revenue postings for reconciliation with SGF | 2–5% timing divergence with StateGov GL |
| `asset_crosswalk` | Maps VistaReserve inventory IDs to InfraTrak and GeoParks IDs | Unmaintained since 2022; stale and incomplete |

### DCR-GEO-01: GeoParks (1 table in scope)

ArcGIS-based geospatial system; authoritative source of truth for park boundaries, identifiers, and organizational structure. Only the `parks_master` table is in scope for this slice; the remaining five GeoParks tables (cultural_resources, infrastructure_features, legal_boundaries, natural_resources, recreational_features) will be incorporated when their respective domains are built.

| Source Table | Business Purpose | Known Quality Issues |
|---|---|---|
| `parks_master` | Canonical park reference: 50 units across 4 regions, ~285,000 acres | VARCHAR park IDs (vs. INTEGER in VistaReserve); 1–3 year update lag on some attributes |

---

## CDM Entity Mapping (Preliminary)

Integration models must conform to Microsoft Common Data Model entity definitions per rule SQL-INT-05. The following mapping identifies candidate CDM entities for the revenue vertical slice; final column-level mapping is a deliverable of the implementation, not a prerequisite.

| Integration Model | Candidate CDM Manifest | Candidate CDM Entity | Rationale |
|---|---|---|---|
| `int_parks` | Asset | FunctionalLocation | Parks are physical locations with operational attributes; FunctionalLocation fits better than Territory or Account for a government parks context |
| `int_contacts` | nonProfitCore | Contact | Customer profiles represent "persons with whom a business unit has a relationship" — the CDM Contact definition |
| `int_customer_assets` | Asset | CustomerAsset | Bookable inventory (campsites, cabins) are assets associated with customer-facing transactions |
| `int_transactions` | nonProfitCore | Transaction | POS transactions and revenue batches are financial transactions from constituents to the organization |
| `int_reservations` | Asset | Visit | A reservation represents a scheduled visit to a functional location; the CDM Visit entity captures this pattern |

**Open question (Engineering):** The `asset_crosswalk` table maps across VistaReserve, InfraTrak, and GeoParks — but it has been unmaintained since 2022. The implementation must decide whether to (a) consume it as a base model with explicit staleness warnings, (b) rebuild the crosswalk logic from shared attributes, or (c) defer crosswalk integration to the Assets vertical slice. Recommendation: option (a) — consume it, document its limitations, and let the Assets slice improve it.

---

## Architecture: Layer-by-Layer Specification

### Layer 0: Project Initialization

#### Virtual Environment and Dependencies

| Deliverable | Specification |
|---|---|
| Python virtual environment | Create using `python -m venv` in the project root; all Python tooling installed within it |
| dbt-core | Latest stable release, installed via pip |
| dbt-duckdb | Latest stable release compatible with dbt-core version |
| sqlfluff | Latest stable release with the `sqlfluff-templater-dbt` plugin |
| dbt-score | Latest stable release |
| requirements.txt | Pin all installed versions for reproducibility |

#### dbt Project Scaffolding

| Deliverable | Specification |
|---|---|
| `dbt_project.yml` | Project name: `dcr_analytics`; profile: `dcr_analytics`; materialization defaults per layer (staging: view; integration: table; marts: table); tag and schema routing per standards ALL-CFG-01 |
| `profiles.yml` | Configure dbt-duckdb to attach the two in-scope DuckDB source databases (`dcr_rev_01_vistareserve.duckdb`, `dcr_geo_01_geoparks.duckdb`) as named schemas; target database is a separate analytical DuckDB file |
| `packages.yml` | All packages version-pinned per ALL-CFG-03 |

#### Required dbt Packages

| Package | Purpose in This Project |
|---|---|
| `dbt_utils` | Surrogate key generation (generate_surrogate_key), schema tests, SQL helpers; foundational to staging hash keys and integration surrogate keys |
| `dbt_expectations` | Statistical and volumetric testing (expect_table_row_count_to_be_between, expect_column_values_to_be_between); supports MRT-YML-08 and INT-YML-06 |
| `dbt_project_evaluator` | DAG hygiene validation (no circular dependencies, no skipped layers, naming conventions); supports ALL-DAG-01, ALL-DAG-02, ALL-NAME-01 |
| `audit_helper` | Compare_relations and compare_column_values for validating refactors and verifying integration model accuracy against source |
| `codegen` | Generate base YAML and SQL scaffolding from source schemas to accelerate development; not a runtime dependency |

#### Linting Configuration

##### sqlfluff (.sqlfluff)

sqlfluff must be configured to enforce every SQL formatting and structural rule from the dbt Project Standards that it can express. The table below maps each standard rule to a specific sqlfluff rule or custom configuration:

| Standard Rule | sqlfluff Rule(s) | Configuration |
|---|---|---|
| ALL-FMT-01 File Length (≤200 lines) | Not natively supported | Custom pre-commit check or CI script; sqlfluff cannot enforce file length |
| ALL-FMT-02 Line Length (≤80 chars) | `LT01` (layout.long_lines) | `max_line_length = 80` |
| ALL-FMT-03 Lowercase Keywords | `CP01` (capitalisation.keywords) | `capitalisation_policy = lower` |
| ALL-FMT-04 Lowercase Function Names | `CP02` (capitalisation.functions) | `capitalisation_policy = lower` |
| ALL-FMT-05 Snake Case Field Names | `CP03` (capitalisation.identifiers) | `capitalisation_policy = lower`; extended_capitalisation_policy = lower; additional enforcement via dbt-score or custom check for underscores vs. camelCase |
| ALL-FMT-06 Predicate Indentation | `LT02` (layout.indent), `LT04` (layout.spacing) | Default indentation rules; `indent_unit = space`, `tab_space_size = 4` |
| ALL-FMT-07 Table Aliasing | `AL01` (aliasing.table), `AL02` (aliasing.column), `AL05` (aliasing.length) | `AL05: min_alias_length = 3` to prevent single-letter aliases; `AL01: aliasing = explicit` to require AS keyword |
| ALL-CTE-02 Explicit Joins | `ST09` (structure.join_condition) | Enforce explicit join types (no implicit cross joins) |
| ALL-CTE-09 No Direct DB References | `RF02` (references.qualification) | Combined with dbt-project-evaluator checks for source()/ref() usage |
| ALL-CTE-11 Simple Final Select | Not natively supported | Custom sqlfluff rule or CI check |
| ALL-PERF-03 No SELECT DISTINCT | `ST08` (structure.distinct) | `prefer_count_distinct = true`; additional custom rule to flag bare UNION (without ALL) |
| ALL-PERF-04 CTEs Over Subqueries | `ST01` (structure.subquery) | Flag subqueries that should be CTEs |
| ALL-CTE-01 Import CTEs at Top | Not natively supported | Enforced by code review and dbt-project-evaluator |
| ALL-CTE-07 PK First in Select | Not natively supported | Enforced by code review |

**Rules requiring custom enforcement outside sqlfluff:**

Several standards — file length (ALL-FMT-01), simple final select (ALL-CTE-11), import CTEs at top (ALL-CTE-01), primary key first (ALL-CTE-07), meaningful CTE names (ALL-CTE-03), and single unit of work per CTE (ALL-CTE-05) — are semantic or structural in ways that a syntax-level linter cannot enforce. These will be covered through a combination of: (a) dbt-project-evaluator rules, (b) custom pre-commit scripts where feasible, and (c) documented review checklists for human reviewers. The spec does not pretend that tooling can replace judgment; it aims to automate what can be automated and make the rest explicit.

##### dbt-score (pyproject.toml or dbt_score.yml)

dbt-score evaluates model-level metadata quality — descriptions, test coverage, documentation completeness — which maps to the YAML & Properties rules in the standards. Configure rules to enforce:

| Standard Rule | dbt-score Rule | Configuration |
|---|---|---|
| YML-DOC-01 Mandatory Description | `has_description` | Severity: error; all models, sources, seeds must have descriptions |
| YML-DOC-02 Description Quality | `has_description` + minimum length | Configure minimum description length (e.g., 50 chars) to prevent placeholder text |
| STG-YML-03 / INT-YML-03 / MRT-YML-03 PK Testing | `has_unique_test`, `has_not_null_test` | Severity: error; every model must have at least one unique and one not_null test |
| MRT-YML-04 Contract Enforcement | Custom rule | Check that mart models (fct_, dim_) have `contract: {enforced: true}` |
| MRT-YML-05 Contract Data Types | Custom rule | Check that contracted models define `data_type` on every column |
| SRC-YML-04 Freshness Thresholds | Custom rule | Check that source definitions include freshness blocks |
| ALL-NAME-01 File Name Prefixes | `sql_has_reasonable_number_of_lines` + custom | Validate model names start with expected prefixes |
| ALL-TST-02 Testing Rationale | Custom rule | Check that model descriptions contain testing rationale language |

**Custom dbt-score rules to be developed:**

Where dbt-score's built-in rules do not cover a standard, custom rules will be written. The following are candidates:

1. **`has_contract_on_marts`** — enforces MRT-YML-04 by checking that all models in the marts directory have contract enforcement enabled.
2. **`has_data_types_on_contracted_columns`** — enforces MRT-YML-05 by verifying that every column on a contracted model declares a data_type.
3. **`has_freshness_on_sources`** — enforces SRC-YML-04 by checking that every source has a freshness block.
4. **`model_name_prefix_matches_directory`** — enforces ALL-NAME-01 by validating that a model in the staging directory starts with `stg_`, etc.
5. **`description_contains_testing_rationale`** — enforces ALL-TST-02 by scanning descriptions for keywords like "tests verify", "tests protect", "tested because", or similar phrasing that indicates the analyst has documented their reasoning.

---

### Layer 1: Source Definitions

Two `_sources.yml` files, one per source system, each in its respective staging subdirectory.

#### `models/staging/vistareserve/_sources.yml`

Defines all 7 VistaReserve tables as sources with:
- `database` and `schema` mapped to the attached DuckDB file
- Freshness thresholds per SRC-YML-04 (VistaReserve is an active SaaS platform; warn after expected update interval + buffer, error when data is too stale for operational reporting)
- Primary key uniqueness and not_null tests per SRC-YML-05 on every table
- Foreign key relationship tests per SRC-YML-06 where referential integrity is expected within VistaReserve (e.g., reservations.customer_id → customer_profiles, reservations.inventory_asset_id → inventory_assets, pos_transactions.park_id → parks)

#### `models/staging/geoparks/_sources.yml`

Defines `parks_master` as a source with:
- Freshness thresholds reflecting GeoParks' slower update cadence (1–3 year lag on some attributes; thresholds should be appropriately wide)
- Primary key testing on parks_master's identifier

---

### Layer 2: Base Models

Base models are optional per the standards; they exist only when preprocessing improves downstream readability. Two base models are warranted in this slice:

#### `models/staging/vistareserve/base/base_vistareserve__customer_profiles.sql`

**Justification:** The DCR Data Inventory documents an 18–22% customer duplicate rate in VistaReserve. Deduplication logic — likely a window function selecting the most recently updated record per natural business key — is complex enough to warrant isolation from the staging model, per SQL-BASE-09.

- Input: `{{ source('vistareserve', 'customer_profiles') }}`
- Transformation: Deduplicate on natural business key using a window function (row_number partitioned by business key, ordered by updated_at desc); select only the most recent version of each customer
- Output: One row per distinct customer, ready for staging to rename and recast

#### `models/staging/vistareserve/base/base_vistareserve__asset_crosswalk.sql`

**Justification:** The asset_crosswalk has been unmaintained since 2022 and maps across three systems (VistaReserve, InfraTrak, GeoParks). A base model can add a staleness flag (days since last update), filter obviously invalid mappings, and add a source_system column — isolating these concerns from the staging model per SQL-BASE-08.

- Input: `{{ source('vistareserve', 'asset_crosswalk') }}`
- Transformation: Add `days_since_last_update` column; flag rows where the crosswalk's GeoParks or InfraTrak IDs do not appear in the other tables (this information is useful but not blocking); add `source_system` literal
- Output: Crosswalk records with staleness metadata

---

### Layer 3: Staging Models

One staging model per source table (or per base model output where a base model exists). Each staging model must follow SQL-STG-01 through SQL-STG-12.

#### VistaReserve Staging Models (7)

| Model | Source / Base Input | Key Transformations |
|---|---|---|
| `stg_vistareserve__parks` | `source('vistareserve', 'parks')` | Rename columns to CDM-adjacent names; cast park_id from INTEGER to VARCHAR for cross-system compatibility; add `hk_parks` hash key; add `source_system` literal ('vistareserve') |
| `stg_vistareserve__customer_profiles` | `ref('base_vistareserve__customer_profiles')` | Rename to business-meaningful names; recast dates from strings if needed; add `hk_customer_profiles` hash key; trim whitespace on name fields; handle PII column selection (include for now — sensitivity policy is a separate deliverable) |
| `stg_vistareserve__inventory_assets` | `source('vistareserve', 'inventory_assets')` | Rename to business names; recast types; add `hk_inventory_assets` hash key; parse any JSON metadata columns per SQL-STG-12 |
| `stg_vistareserve__reservations` | `source('vistareserve', 'reservations')` | Rename; recast dates/timestamps; add `hk_reservations` hash key; standardize status values if inconsistent |
| `stg_vistareserve__pos_transactions` | `source('vistareserve', 'pos_transactions')` | Rename; recast amounts to appropriate numeric types; recast timestamps; add `hk_pos_transactions` hash key |
| `stg_vistareserve__revenue_batches` | `source('vistareserve', 'revenue_batch')` | Rename (note: source table is singular `revenue_batch`; staging model uses plural per ALL-NAME-02); recast batch dates and amounts; add `hk_revenue_batches` hash key |
| `stg_vistareserve__asset_crosswalks` | `ref('base_vistareserve__asset_crosswalk')` | Rename; recast IDs to consistent VARCHAR types; add `hk_asset_crosswalks` hash key; retain staleness metadata from base model |

#### GeoParks Staging Model (1)

| Model | Source Input | Key Transformations |
|---|---|---|
| `stg_geoparks__parks_master` | `source('geoparks', 'parks_master')` | Rename to CDM-adjacent names; retain VARCHAR park_id as canonical identifier; add `hk_parks_master` hash key; add `source_system` literal ('geoparks'); standardize region names/codes |

#### Staging YAML (`_models.yml` per directory)

Every staging model documented with:
- Description including business meaning, grain, and testing rationale per YML-DOC-01, YML-DOC-02, ALL-TST-02
- `unique` and `not_null` tests on the hash key per STG-YML-03
- `not_null` tests on the natural key
- Hash collision test where warranted per STG-YML-04

---

### Layer 4: Integration Models

Integration models harmonize data across source systems into CDM-conforming, third-normal-form representations. Each model's columns must conform to the mapped CDM entity definition per SQL-INT-05; non-CDM columns are dropped at this layer and can be joined back in the marts layer if needed.

**Critical implementation constraint:** Integration models are NOT rename-only passthroughs. Every integration model in this spec must generate a surrogate key (`<entity>_sk`) using `dbt_utils.generate_surrogate_key()`, consume all listed input sources, and perform the transformations specified below. A model that only renames columns from a single staging source has not performed integration and must be reworked. The CDM entity mapping listed for each model is authoritative — do not substitute a different CDM entity without documenting the rationale and obtaining user approval.

#### `models/integration/int_parks.sql`

**CDM Entity:** Asset → FunctionalLocation (pending final mapping validation)

This is the most critical model in the slice — and arguably in the entire project — because parks is the central dimension referenced by every business domain. Six systems maintain independent park references; this integration model resolves two of them (GeoParks as authoritative, VistaReserve as supplementary) and establishes the pattern for incorporating the remaining four.

- **Inputs:** `ref('stg_geoparks__parks_master')`, `ref('stg_vistareserve__parks')`
- **Transformations:**
  - Union park records from both systems
  - GeoParks parks_master is the authoritative source; VistaReserve parks enrich where GeoParks records exist, but do not create new park records on their own
  - Join on a reconciled park identifier (the crosswalk or a deterministic matching strategy; this is an open design question)
  - Coalesce attributes with GeoParks taking precedence
  - Generate `parks_sk` surrogate key per SQL-INT-06
  - Drop non-CDM columns per SQL-INT-05
  - Deduplicate to one row per park per SQL-INT-11
- **Output grain:** One row per park unit (expected: 50 rows)

#### `models/integration/int_contacts.sql`

**CDM Entity:** nonProfitCore → Contact

- **Inputs:** `ref('stg_vistareserve__customer_profiles')`
- **Transformations:**
  - Map customer profile columns to CDM Contact columns (first_name, last_name, email_address, telephone, address fields, etc.)
  - Generate `contacts_sk` surrogate key
  - Drop non-CDM columns
  - In this slice, only VistaReserve contributes contacts; the model structure should accommodate future unions from other systems (PeopleFirst employees, RangerShield subjects) without restructuring
- **Output grain:** One row per distinct contact

#### `models/integration/int_customer_assets.sql`

**CDM Entity:** Asset → CustomerAsset

- **Inputs:** `ref('stg_vistareserve__inventory_assets')`, optionally `ref('stg_vistareserve__asset_crosswalks')` for GeoParks/InfraTrak linkage
- **Transformations:**
  - Map inventory asset columns to CDM CustomerAsset columns
  - Join crosswalk data to enrich with cross-system identifiers (with staleness caveats documented)
  - Generate `customer_assets_sk` surrogate key
  - Drop non-CDM columns
- **Output grain:** One row per bookable asset

#### `models/integration/int_transactions.sql`

**CDM Entity:** nonProfitCore → Transaction

- **Inputs:** `ref('stg_vistareserve__pos_transactions')`, `ref('stg_vistareserve__revenue_batches')`
- **Transformations:**
  - Union POS transactions and revenue batch line items into a single transaction stream (if revenue_batch records are at a compatible grain; otherwise model separately)
  - Map to CDM Transaction columns
  - Generate `transactions_sk` surrogate key
  - Drop non-CDM columns
- **Output grain:** One row per financial transaction event
- **Design decision:** If revenue_batch records represent aggregated batches rather than individual transactions, they should be modeled separately (e.g., `int_revenue_batches`) rather than forced into the same grain. Profiling during development will determine the correct approach per ALL-TST-03.

#### `models/integration/int_reservations.sql`

**CDM Entity:** Asset → Visit

- **Inputs:** `ref('stg_vistareserve__reservations')`
- **Transformations:**
  - Map reservation columns to CDM Visit columns
  - Generate `reservations_sk` surrogate key
  - Include foreign keys to int_contacts (customer) and int_customer_assets (booked asset)
  - Drop non-CDM columns
- **Output grain:** One row per reservation

#### Integration YAML (`models/integration/_models.yml`)

Every integration model documented with:
- Description including business meaning, grain, and CDM entity mapping. Descriptions must NOT contain test rationale — that belongs in `meta: testing_rationale:` blocks per ALL-TST-02
- `unique` and `not_null` tests on surrogate key per INT-YML-03
- `relationships` tests on foreign keys per INT-YML-04 — these are mandatory, not optional
- Join cardinality validation per INT-YML-05 (using dbt_expectations row count comparison)
- Business logic constraint tests per INT-YML-06 (e.g., reservation check_in_date <= check_out_date)
- CDM accepted values tests per INT-YML-08 where CDM metadata provides them
- Every column documented in the YAML must exist in the model's SQL output per YML-SYNC-01. No phantom columns
- Each model must appear exactly once in the YAML — no duplicate entries per YML-SYNC-02

---

### Layer 5: Mart Models

Mart models consume integration models only (per SQL-FCT-05, SQL-DIM-05) and serve business users directly. All mart models in this slice belong to the `revenue` owner directory.

#### Fact Models

##### `models/marts/revenue/fct_reservations.sql`

- **Grain:** One row per reservation event
- **Input:** `ref('int_reservations')`
- **Measures:** reservation_amount, nights_stayed (derived from check_in/check_out dates), number_of_guests
- **Dimension keys:** parks_sk (from int_parks), contacts_sk (from int_contacts), customer_assets_sk (from int_customer_assets), date keys for check_in and check_out
- **Contract:** enforced: true with data_type on every column per MRT-YML-04, MRT-YML-05

##### `models/marts/revenue/fct_pos_transactions.sql`

- **Grain:** One row per point-of-sale transaction
- **Input:** `ref('int_transactions')` (filtered to POS transactions if int_transactions unions multiple types)
- **Measures:** transaction_amount, quantity
- **Dimension keys:** parks_sk, contacts_sk (where available; POS transactions may be anonymous), transaction_date key
- **Contract:** enforced: true

#### Dimension Models

##### `models/marts/revenue/dim_parks.sql`

- **Input:** `ref('int_parks')`; may join back to `ref('stg_geoparks__parks_master')` or `ref('stg_vistareserve__parks')` to recover non-CDM descriptive columns dropped at integration
- **Attributes:** park_name, region, acreage, park_type, operational_status, address fields, geographic coordinates
- **Enrichments per SQL-DIM-09:** Region groupings, acreage size tiers, operational status labels
- **Contract:** enforced: true

##### `models/marts/revenue/dim_customers.sql`

- **Input:** `ref('int_contacts')`; may join back to `ref('stg_vistareserve__customer_profiles')` for non-CDM attributes
- **Attributes:** customer_name (combined from first/last per SQL-DIM-08), email, phone, address, customer_since_date
- **Enrichments:** Customer tenure tier, geographic region (from address)
- **Contract:** enforced: true

##### `models/marts/revenue/dim_reservation_inventory.sql`

- **Input:** `ref('int_customer_assets')`; may join back to staging for non-CDM descriptive columns
- **Attributes:** asset_name, asset_type (campsite, cabin, shelter, day-use), park assignment, capacity, amenities
- **Enrichments:** Asset type groupings, capacity tiers
- **Contract:** enforced: true

#### Report Models

##### `models/marts/revenue/rpt_park_revenue_summary.sql`

- **Justification:** Park-level revenue reporting is the most commonly requested analytical view across DCR leadership; it will be consumed by multiple downstream processes once exposures exist.
- **Inputs:** `ref('fct_reservations')`, `ref('fct_pos_transactions')`, `ref('dim_parks')`
- **Grain:** One row per park per month
- **Columns:** park_name, region, month, reservation_revenue, pos_revenue, total_revenue, reservation_count, transaction_count, average_reservation_value
- **Aggregation per SQL-RPT-07:** Facts aggregated from transaction-level to park-month grain

#### Marts YAML (`models/marts/revenue/_models.yml`)

Every mart model documented with:
- Description including business meaning, grain, and testing rationale
- `unique` and `not_null` tests on primary/surrogate key per MRT-YML-03
- `contract: {enforced: true}` per MRT-YML-04
- `data_type` on every column per MRT-YML-05
- `relationships` tests on dimension foreign keys
- Volumetric tests using dbt_expectations per MRT-YML-08

---

### Seeds

| Seed File | Purpose | Columns |
|---|---|---|
| `seeds/reservation_status_codes.csv` | Map reservation status codes to human-readable labels | `status_code`, `status_label`, `is_active`, `sort_order` |
| `seeds/transaction_type_codes.csv` | Map POS transaction type codes to labels and categories | `type_code`, `type_label`, `revenue_category` |
| `seeds/park_region_mappings.csv` | Canonical region assignments for the 4 DCR regions | `region_code`, `region_name`, `region_description` |
| `seeds/source_system_registry.csv` | Registry of source systems for lineage tagging | `source_system_code`, `source_system_name`, `system_type`, `operational_status` |

Each seed will have a corresponding entry in `seeds/_seeds.yml` with descriptions and data type overrides per SQL-SEED-05.

---

### Macros

| Macro File | Purpose | Standards Addressed |
|---|---|---|
| `macros/generate_source_system_tag.sql` | Standardize the `source_system` literal added in staging models; accepts system code, returns formatted string | ALL-PERF-01 (macros over boilerplate) |
| `macros/clean_string.sql` | Trim whitespace, remove special characters, standardize casing for string fields | SQL-STG-11 (standardize value formats); ALL-PERF-01 |
| `macros/cast_park_id_to_varchar.sql` | Consistent INTEGER-to-VARCHAR park ID casting with zero-padding if needed | Ensures cross-system park ID compatibility |

Each macro will have a corresponding entry in `macros/_macros.yml` with description and argument documentation per MAC-YML-03.

---

### Singular Tests

| Test File | Assertion | Standards Addressed |
|---|---|---|
| `tests/integration/assert_no_orphan_parks_in_reservations.sql` | Every reservation's park reference exists in int_parks | INT-YML-04 (FK consistency) |
| `tests/integration/assert_park_ids_reconciled.sql` | VistaReserve parks in int_parks all have a valid GeoParks parks_master match | Cross-system reconciliation validation |
| `tests/marts/assert_revenue_sums_balance.sql` | Total revenue in rpt_park_revenue_summary equals sum of fct_reservations + fct_pos_transactions for the same period | End-to-end reconciliation |

---

### Snapshots

Snapshots are documented as "not currently in active use" in the standards, but the vertical slice should include at least one to prove the pattern.

#### `snapshots/snp_vistareserve__inventory_assets.sql`

- **Justification:** Inventory assets (campsites, cabins) change over time — assets are added, decommissioned, or reclassified. Capturing SCD Type 2 history on this table demonstrates the snapshot pattern for future use across other mutable source tables.
- **Strategy:** timestamp (using the source's updated_at column per SQL-SNAP-03)
- **Source:** `{{ source('vistareserve', 'inventory_assets') }}` per SQL-SNAP-04

---

### Analyses

#### `analyses/profile_customer_duplicate_rate.sql`

- **Purpose:** Ad-hoc query to validate the 18–22% duplicate rate documented in the Data Inventory; used during development profiling per ALL-TST-03 but retained as a reference
- **References:** `{{ source('vistareserve', 'customer_profiles') }}` per SQL-ANL-03

#### `analyses/audit_park_id_crosswalk_coverage.sql`

- **Purpose:** Quantify how many VistaReserve parks match GeoParks parks_master records; informs the int_parks reconciliation strategy
- **References:** `{{ ref('stg_vistareserve__parks') }}`, `{{ ref('stg_geoparks__parks_master') }}`

---

## Directory Structure

```
dcr_analytics/
├── .venv/
├── .sqlfluff
├── .sqlfluffignore
├── pyproject.toml              # dbt-score config + custom rules
├── dbt_project.yml
├── packages.yml
├── profiles.yml
├── requirements.txt
│
├── analyses/
│   ├── profile_customer_duplicate_rate.sql
│   └── audit_park_id_crosswalk_coverage.sql
│
├── macros/
│   ├── _macros.yml
│   ├── generate_source_system_tag.sql
│   ├── clean_string.sql
│   └── cast_park_id_to_varchar.sql
│
├── models/
│   ├── staging/
│   │   ├── vistareserve/
│   │   │   ├── _sources.yml
│   │   │   ├── _models.yml
│   │   │   ├── base/
│   │   │   │   ├── base_vistareserve__customer_profiles.sql
│   │   │   │   └── base_vistareserve__asset_crosswalks.sql
│   │   │   ├── stg_vistareserve__parks.sql
│   │   │   ├── stg_vistareserve__customer_profiles.sql
│   │   │   ├── stg_vistareserve__inventory_assets.sql
│   │   │   ├── stg_vistareserve__reservations.sql
│   │   │   ├── stg_vistareserve__pos_transactions.sql
│   │   │   ├── stg_vistareserve__revenue_batches.sql
│   │   │   └── stg_vistareserve__asset_crosswalks.sql
│   │   └── geoparks/
│   │       ├── _sources.yml
│   │       ├── _models.yml
│   │       └── stg_geoparks__parks_master.sql
│   │
│   ├── integration/
│   │   ├── _models.yml
│   │   ├── int_parks.sql
│   │   ├── int_contacts.sql
│   │   ├── int_customer_assets.sql
│   │   ├── int_transactions.sql
│   │   └── int_reservations.sql
│   │
│   └── marts/
│       └── revenue/
│           ├── _models.yml
│           ├── fct_reservations.sql
│           ├── fct_pos_transactions.sql
│           ├── dim_parks.sql
│           ├── dim_customers.sql
│           ├── dim_reservation_inventory.sql
│           └── rpt_park_revenue_summary.sql
│
├── seeds/
│   ├── _seeds.yml
│   ├── reservation_status_codes.csv
│   ├── transaction_type_codes.csv
│   ├── park_region_mappings.csv
│   └── source_system_registry.csv
│
├── snapshots/
│   └── snp_vistareserve__inventory_assets.sql
│
└── tests/
    ├── integration/
    │   ├── assert_no_orphan_parks_in_reservations.sql
    │   └── assert_park_ids_reconciled.sql
    └── marts/
        └── assert_revenue_sums_balance.sql
```

---

## Rule-by-Rule Compliance Verification Plan

The dbt Project Standards document contains 103 rules. This table maps every rule to its primary verification method so that compliance is observable — not assumed — and so that the boundary between automated enforcement and human judgment is explicit. Where a rule can be checked by tooling, the specific tool and configuration are named. Where a rule requires human review, the table says so plainly; pretending that a linter can evaluate whether a CTE name is "meaningful" would erode trust in the verification process itself.

**Verification method key:**

| Method | Description |
|---|---|
| **sqlfluff** | Enforced by sqlfluff linting rules in `.sqlfluff`; violations block merge |
| **dbt-project-evaluator** | Enforced by the dbt_project_evaluator package; runs as part of `dbt build` |
| **dbt-score** | Enforced by dbt-score rules (built-in or custom); violations block merge |
| **dbt build (tests)** | Enforced by generic or singular dbt tests defined in YAML or `tests/`; failures block merge |
| **dbt build (runtime)** | Enforced by dbt's own compilation or runtime behavior; errors surface naturally |
| **custom script** | Enforced by a custom pre-commit or CI script written for this project |
| **code review** | Requires human judgment; cannot be reliably automated. Reviewer checklist item |
| **structural inspection** | Verified by inspecting directory layout, file names, or project config — trivially observable but not worth automating |
| **N/A (this slice)** | Rule is valid but does not apply to the current vertical slice; will be verified when relevant |

---

### Cross-Model Standards

| Rule | Name | Verification Method | Implementation Detail |
|---|---|---|---|
| ALL-DAG-01 | Unidirectional Dependency Flow | **dbt-project-evaluator** | `fct_direct_join_to_source` and `fct_staging_dependent_on_staging` models detect layer-skipping and reverse dependencies; any rows returned indicate a violation |
| ALL-DAG-02 | No Circular Dependencies | **dbt build (runtime)** | dbt itself raises a compilation error if a circular dependency exists; this is enforced at the engine level and cannot be bypassed |
| ALL-CFG-01 | Centralize Configs in dbt_project.yml | **dbt-project-evaluator** + **code review** | dbt-project-evaluator's `fct_model_directories` checks for directory/config consistency; reviewer confirms that per-model `config()` blocks are exceptions, not defaults |
| ALL-CFG-02 | Config Block Placement | **sqlfluff** | `JJ01` / layout rules enforce that `config()` blocks — if present — appear before any SQL. Additionally verified by **code review** |
| ALL-CFG-03 | Package Version Pinning | **structural inspection** | Reviewer confirms every entry in `packages.yml` specifies a version or version range; no unpinned packages |
| ALL-NAME-01 | File Name Prefixes | **dbt-project-evaluator** + **custom script** | dbt-project-evaluator's `fct_model_naming_conventions` flags models without the expected prefix for their directory. Custom script validates that YAML files have leading underscores |
| ALL-NAME-02 | Plural Phrasing | **dbt-project-evaluator** + **code review** | dbt-project-evaluator flags some naming issues; plural vs. singular requires human judgment on word choice |
| ALL-NAME-03 | Abbreviation Restraint | **code review** | No linter can determine whether an abbreviation is necessary or premature; reviewer evaluates names under 20 characters for unnecessary shortening |
| ALL-NAME-04 | Business Concept Phrasing | **code review** | Semantic judgment — whether a name reflects a business concept rather than a system artifact — is inherently human |
| ALL-FMT-01 | File Length (≤200 lines) | **custom script** | `wc -l` check in pre-commit; warn above 200 lines, error above 300. sqlfluff does not support file-level length checks |
| ALL-FMT-02 | Line Length (≤80 chars) | **sqlfluff** | Rule `LT01` with `max_line_length = 80` |
| ALL-FMT-03 | Lowercase Keywords | **sqlfluff** | Rule `CP01` with `capitalisation_policy = lower` |
| ALL-FMT-04 | Lowercase Function Names | **sqlfluff** | Rule `CP02` with `capitalisation_policy = lower` |
| ALL-FMT-05 | Snake Case Field Names | **sqlfluff** + **dbt-score** | `CP03` enforces lowercase identifiers; **dbt-score** custom rule or **custom script** checks for underscores (no camelCase, no hyphens, no spaces) |
| ALL-FMT-06 | Predicate Indentation | **sqlfluff** | Rules `LT02` (indent) and `LT04` (spacing) with `indent_unit = space`, `tab_space_size = 4` |
| ALL-FMT-07 | Table Aliasing | **sqlfluff** | `AL01` (aliasing = explicit, requiring AS keyword); `AL05` (`min_alias_length = 3`) to prevent single-letter aliases; `AL07` to enforce table alias usage in joins |
| ALL-CTE-01 | Import CTEs at Top | **code review** + **dbt-project-evaluator** | dbt-project-evaluator flags models with `source()` or `ref()` not in import CTEs. Reviewer confirms all refs/sources are isolated at the top of the file |
| ALL-CTE-02 | Explicit Joins with Aliases | **sqlfluff** | `JJ01` flags implicit joins (comma joins); `RF02` enforces column qualification. `AL01` requires explicit aliasing with AS |
| ALL-CTE-03 | Meaningful CTE Names | **code review** | Whether a name is "meaningful and succinct" is a judgment call; reviewer evaluates against the naming guidance (import CTEs = object, transformation CTEs = object + verb, complex = subject + object + verb) |
| ALL-CTE-04 | No Duplicative CTEs Across Models | **code review** | No linter compares CTE logic across files. Reviewer identifies repeated patterns and recommends extraction to upstream models or macros |
| ALL-CTE-05 | Single Unit of Work | **code review** | Whether a CTE performs "one unit of work" requires understanding the transformation intent; no automated tool can reliably assess this |
| ALL-CTE-06 | Comment Confusing CTEs | **code review** | Whether logic is "non-obvious" and whether a comment adequately explains it are judgment calls |
| ALL-CTE-07 | Primary Key First | **custom script** + **code review** | Custom script can check that the first column in the final SELECT matches the model's documented primary key; edge cases require review |
| ALL-CTE-08 | Column Alias Prefixing | **sqlfluff** | `RF02` (references.qualification) flags unqualified column references in joins and multi-table contexts |
| ALL-CTE-09 | No Direct Database References | **dbt-project-evaluator** + **sqlfluff** | dbt-project-evaluator's `fct_direct_join_to_source` flags direct database references. `RF02` can also flag fully qualified table names outside of `ref()`/`source()` |
| ALL-CTE-10 | Early Aggregation | **code review** | Determining whether aggregation happens "as early as possible" requires understanding the data flow and cardinality at each step; no linter can evaluate this |
| ALL-CTE-11 | Simple Final Select | **custom script** + **code review** | Custom script can parse the last SQL statement and verify it matches `select * from <cte_name>` with no additional logic; false positives possible on complex trailing comments |
| ALL-PERF-01 | Use Macros Over Boilerplate | **code review** | Recognizing that a SQL pattern appears in multiple models and should be extracted to a macro requires cross-file awareness that linters lack |
| ALL-PERF-02 | Reproducible Primary Keys | **code review** + **dbt build (tests)** | Reviewer confirms that surrogate keys use `generate_surrogate_key()` or equivalent deterministic method; `unique` tests on PKs catch non-reproducibility indirectly if re-runs produce different keys |
| ALL-PERF-03 | No SELECT DISTINCT / UNION DISTINCT | **sqlfluff** | Custom sqlfluff rule or `ST08` flags `SELECT DISTINCT`; custom regex rule flags bare `UNION` without `ALL` |
| ALL-PERF-04 | CTEs Over Subqueries | **sqlfluff** | `ST01` flags subqueries that should be CTEs |
| ALL-TST-01 | Test What You Deliver and Depend On | **dbt-score** + **code review** | dbt-score's `has_unique_test` and `has_not_null_test` verify minimum test presence; whether the *right* things are tested requires reviewer judgment |
| ALL-TST-02 | Justify Testing Choices | **dbt-score** (custom rule) + **code review** | Custom dbt-score rule `description_contains_testing_rationale` checks for keywords indicating testing rationale; reviewer evaluates whether the rationale is substantive, not formulaic |
| ALL-TST-03 | Exploratory Data Profiling | **code review** | This is a development practice, not an artifact. Reviewer can ask the analyst to describe their profiling findings; the tests and rationale in YAML should reflect profiling insights |

---

### Staging SQL Models

| Rule | Name | Verification Method | Implementation Detail |
|---|---|---|---|
| SQL-STG-01 | Directory Syntax | **dbt-project-evaluator** + **structural inspection** | dbt-project-evaluator flags models not in expected directories; reviewer confirms `models/staging/{source}/*` |
| SQL-STG-02 | File Name Syntax | **dbt-project-evaluator** + **custom script** | Custom script validates pattern `stg_<source>__<entity>.sql` using regex; dbt-project-evaluator checks prefix |
| SQL-STG-03 | Entity Word Choice | **code review** | Whether a name uses "business meaning" vs. "system logic" requires semantic judgment |
| SQL-STG-04 | File Name Underscore Delimitation | **custom script** | Regex check: single underscore between prefix and source, double underscore between source and entity |
| SQL-STG-05 | Consume Source Tables or Base Models | **dbt-project-evaluator** | `fct_direct_join_to_source` confirms staging models use `source()` or `ref()` to a base model; `fct_staging_dependent_on_staging` confirms they do not consume other staging models |
| SQL-STG-06 | No Joins, Aggregations, or Filtering | **sqlfluff** + **code review** | Custom sqlfluff rule can flag `JOIN`, `GROUP BY`, `HAVING`, or `WHERE` (excluding CTE definitions) in files matching `stg_*`; edge cases (e.g., `WHERE` for type casting) require review |
| SQL-STG-07 | Add a Hash Key | **dbt-score** (custom rule) + **code review** | Custom dbt-score rule checks that staging models have a column matching `hk_*` with `unique` and `not_null` tests. Reviewer confirms `generate_surrogate_key()` is used |
| SQL-STG-08 | Pick Relevant Columns | **code review** | Column selection decisions require business context; no automated tool can determine which columns are "useful" |
| SQL-STG-09 | Rename Columns for Understandability | **code review** | Whether a column name is "intuitive" and "CDM-adjacent" requires domain knowledge |
| SQL-STG-10 | Recast Sub-Optimally Formatted Data | **code review** + **dbt build (runtime)** | Reviewer checks that dates stored as strings are cast to DATE/TIMESTAMP, decimals as floats are cast to NUMERIC, etc. dbt will surface some type errors at runtime |
| SQL-STG-11 | Standardize Value Formats | **code review** | Trimming whitespace, removing special characters, correcting casing — these are transformation decisions informed by data profiling |
| SQL-STG-12 | Parse and Flatten Structure | **code review** | JSON extraction, composite key splitting, and similar transformations require understanding the source data structure |

---

### Base SQL Models

| Rule | Name | Verification Method | Implementation Detail |
|---|---|---|---|
| SQL-BASE-01 | Directory Syntax | **structural inspection** | Confirm base models are in `models/staging/{source}/base/*` |
| SQL-BASE-02 | File Name Syntax | **custom script** | Regex check: `base_<source>__<entity>.sql` |
| SQL-BASE-03 | Entity Name Word Choice | **code review** | Same semantic judgment as SQL-STG-03 |
| SQL-BASE-04 | File Name Underscore Delimitation | **custom script** | Same regex check as SQL-STG-04 but with `base_` prefix |
| SQL-BASE-05 | Consume Source Tables | **dbt-project-evaluator** | Confirms base models use `source()` macro |
| SQL-BASE-06 | Combine Multiple Tables | **code review** | Whether a union or join of source tables is appropriate requires understanding the source data |
| SQL-BASE-07 | Split Up a Single Table | **code review** | Whether a table contains multiple entity types requiring separation is a design decision |
| SQL-BASE-08 | Add Columns | **code review** | JSON extraction, derived columns, and similar preprocessing are verified by inspecting the SQL |
| SQL-BASE-09 | Complex Deduplication | **code review** + **dbt build (tests)** | Reviewer confirms window function logic; `unique` test on the output's natural key confirms deduplication succeeded |

---

### Integration SQL Models

| Rule | Name | Verification Method | Implementation Detail |
|---|---|---|---|
| SQL-INT-01 | Directory Syntax | **dbt-project-evaluator** + **structural inspection** | Confirm models are in `models/integration/*` |
| SQL-INT-02 | File Name Syntax | **dbt-project-evaluator** + **custom script** | Regex check: `int_<entity>.sql` |
| SQL-INT-03 | Entity Name Word Choice (CDM) | **code review** | Reviewer confirms the entity name matches a Microsoft CDM entity; this is a semantic mapping that no linter can validate |
| SQL-INT-04 | File Name Underscore Delimitation | **custom script** | Regex check: single underscore between `int` prefix and entity |
| SQL-INT-05 | CDM Column Conformance | **custom script** + **code review** | Custom script compares model output columns against the CDM entity CSV in `source_data/cdm_metadata/columns/`; flags columns not in the CDM definition (excluding `_sk` and `_id` keys). Reviewer evaluates whether exceptions are documented and justified |
| SQL-INT-06 | Surrogate Key Naming | **dbt-score** (custom rule) + **custom script** | Regex check: integration models must have a column ending in `_sk`; dbt-score custom rule validates naming pattern |
| SQL-INT-07 | Consume Staging Models | **dbt-project-evaluator** | `fct_direct_join_to_source` confirms integration models use `ref()` to staging models; they should not reference `source()` directly |
| SQL-INT-08 | Union Data Across Systems | **code review** | Whether the model unions data from multiple staging models is a design decision based on the entity's source system landscape |
| SQL-INT-09 | Filter Irrelevant Data | **code review** | Whether records should be excluded requires understanding the entity definition and source data contents |
| SQL-INT-10 | Join to Enrich Records | **code review** | Whether enrichment joins use the most accurate, complete, and fresh source requires domain knowledge |
| SQL-INT-11 | Harmonize and Deduplicate | **dbt build (tests)** + **code review** | `unique` test on the surrogate key confirms deduplication succeeded; reviewer evaluates coalesce/case logic for correctness |
| SQL-INT-12 | Minimal Renaming | **code review** | Widespread renaming at integration is a sign that staging models need improvement; reviewer flags if more than a few columns are renamed |

---

### Fact SQL Models

| Rule | Name | Verification Method | Implementation Detail |
|---|---|---|---|
| SQL-FCT-01 | Directory Syntax | **dbt-project-evaluator** + **structural inspection** | Confirm models are in `models/marts/{owner}/*` |
| SQL-FCT-02 | File Name Syntax | **dbt-project-evaluator** + **custom script** | Regex check: `fct_<business_process_event>.sql` |
| SQL-FCT-03 | Business Process Event Word Choice | **code review** | Whether the name sounds like an "event noun" is a judgment call |
| SQL-FCT-04 | File Name Underscore Delimitation | **custom script** | Regex check: single underscore between `fct` and event |
| SQL-FCT-05 | Consume Integration Models | **dbt-project-evaluator** | Confirms fact models use `ref()` to integration models; flags direct references to staging or sources |
| SQL-FCT-06 | Declare the Grain | **code review** + **dbt build (tests)** | Reviewer confirms the model description states the grain explicitly; `unique` test on the primary key validates that each row corresponds to one event at the declared grain |
| SQL-FCT-07 | Compute Numeric Measurements | **code review** | Whether the model includes appropriate measures is a domain decision |
| SQL-FCT-08 | Join in Dimension Keys | **dbt build (tests)** + **code review** | `not_null` tests on foreign key columns confirm every fact row has dimension key references; `relationships` tests confirm keys exist in dimension tables |

---

### Dimension SQL Models

| Rule | Name | Verification Method | Implementation Detail |
|---|---|---|---|
| SQL-DIM-01 | Directory Syntax | **dbt-project-evaluator** + **structural inspection** | Confirm models are in `models/marts/{owner}/*` |
| SQL-DIM-02 | File Name Syntax | **dbt-project-evaluator** + **custom script** | Regex check: `dim_<noun>.sql` |
| SQL-DIM-03 | Noun Word Choice | **code review** | Whether the name is a descriptive "head noun" is a judgment call |
| SQL-DIM-04 | File Name Underscore Delimitation | **custom script** | Regex check: single underscore between `dim` and noun |
| SQL-DIM-05 | Consume Integration Models | **dbt-project-evaluator** | Confirms dimension models reference integration models via `ref()` |
| SQL-DIM-06 | Join Multiple Integration Tables | **code review** | Whether the dimension is sufficiently wide and flat requires understanding the business context |
| SQL-DIM-07 | Dimension Keys | **dbt build (tests)** + **code review** | `unique` and `not_null` tests on dimension keys; reviewer confirms keys match those expected by consuming fact models |
| SQL-DIM-08 | Split or Combine Columns | **code review** | Column transformations (name splitting, address combining) are verified by inspecting the SQL |
| SQL-DIM-09 | Add Enriching Columns | **code review** | Binning, hierarchies, and descriptive labels are design decisions informed by downstream reporting needs |

---

### Report SQL Models

| Rule | Name | Verification Method | Implementation Detail |
|---|---|---|---|
| SQL-RPT-01 | Directory Syntax | **dbt-project-evaluator** + **structural inspection** | Confirm models are in `models/marts/{owner}/*` |
| SQL-RPT-02 | File Name Syntax | **dbt-project-evaluator** + **custom script** | Regex check: `rpt_<subject>.sql` |
| SQL-RPT-03 | Subject Word Choice | **code review** | Whether the name describes the report subject accurately is a judgment call |
| SQL-RPT-04 | File Name Underscore Delimitation | **custom script** | Regex check: single underscore between `rpt` and subject |
| SQL-RPT-05 | Consume Fact and Dimension Models | **dbt-project-evaluator** | Confirms report models reference fact and dimension models via `ref()` |
| SQL-RPT-06 | Join Multiple Fact and Dimension Tables | **code review** | Whether the report joins the right combination of facts and dimensions requires understanding the business question |
| SQL-RPT-07 | Aggregate Facts to Consistent Grains | **code review** + **dbt build (tests)** | Reviewer confirms aggregation produces a consistent grain; `unique` test on the primary key validates grain integrity |

---

### Macros

| Rule | Name | Verification Method | Implementation Detail |
|---|---|---|---|
| SQL-MAC-01 | Directory Syntax | **structural inspection** | Confirm macros are in `macros/*` |
| SQL-MAC-02 | File Name Syntax | **structural inspection** | Confirm file names describe the macro's action in snake_case; one macro per file |
| SQL-MAC-03 | Argument Validation | **code review** | Reviewer confirms macros include defensive checks (e.g., `{% if not argument %}{% do exceptions.raise_compiler_error(...) %}{% endif %}`) |
| SQL-MAC-04 | Prefer Packages Over Custom | **code review** | Reviewer confirms that custom macros do not duplicate functionality available in dbt_utils, dbt_expectations, or other installed packages |

---

### Singular Tests

| Rule | Name | Verification Method | Implementation Detail |
|---|---|---|---|
| SQL-TST-01 | Directory Syntax | **structural inspection** | Confirm tests are in `tests/*` with optional subdirectories |
| SQL-TST-02 | File Name Syntax | **custom script** | Regex check: `assert_<description>.sql` |
| SQL-TST-03 | Query Returns Failing Rows | **code review** + **dbt build (tests)** | Reviewer confirms query returns violations (not successes); dbt's test runner interprets returned rows as failures |
| SQL-TST-04 | Reference Models with ref | **dbt build (runtime)** + **code review** | dbt compilation will fail if a model is referenced without `ref()`; reviewer confirms no hardcoded table names |

---

### Seeds

| Rule | Name | Verification Method | Implementation Detail |
|---|---|---|---|
| SQL-SEED-01 | Directory Syntax | **structural inspection** | Confirm seeds are in `seeds/*` |
| SQL-SEED-02 | File Format | **structural inspection** | Confirm seeds are CSV with header rows; column names in snake_case |
| SQL-SEED-03 | Naming | **structural inspection** | Confirm file names describe the reference data in snake_case |
| SQL-SEED-04 | No Business Logic in Seeds | **code review** | Reviewer confirms seeds contain only raw reference data; no formulas, no derived values |
| SQL-SEED-05 | YAML Properties | **dbt-score** | dbt-score `has_description` rule applied to seeds; reviewer confirms `_seeds.yml` includes data type overrides where defaults are inappropriate |

---

### Snapshots

| Rule | Name | Verification Method | Implementation Detail |
|---|---|---|---|
| SQL-SNAP-01 | Directory Syntax | **structural inspection** | Confirm snapshots are in `snapshots/*` |
| SQL-SNAP-02 | File Name Syntax | **custom script** | Regex check: `snp_<source>__<entity>.sql` |
| SQL-SNAP-03 | Strategy Declaration | **code review** | Reviewer confirms config block declares strategy (timestamp or check) and the column(s) used for change detection |
| SQL-SNAP-04 | Source Reference | **dbt build (runtime)** + **code review** | Reviewer confirms `source()` macro is used, not `ref()` |

---

### Analyses

| Rule | Name | Verification Method | Implementation Detail |
|---|---|---|---|
| SQL-ANL-01 | Directory Syntax | **structural inspection** | Confirm analyses are in `analyses/*` |
| SQL-ANL-02 | File Name Syntax | **structural inspection** | Confirm file names describe the query purpose in snake_case |
| SQL-ANL-03 | Use ref and source Macros | **dbt build (runtime)** + **code review** | dbt compilation validates macro usage; reviewer confirms no hardcoded table names |

---

### Hooks

| Rule | Name | Verification Method | Implementation Detail |
|---|---|---|---|
| SQL-HOOK-01 | Declare Hooks in dbt_project.yml | **structural inspection** | N/A for this slice — no hooks are planned. If hooks are added, reviewer confirms they are declared in `dbt_project.yml` |
| SQL-HOOK-02 | Extract Complex Logic into Macros | **code review** | N/A for this slice. If hooks are added, reviewer confirms multi-statement hooks call macros |
| SQL-HOOK-03 | Document Hook Purpose | **code review** | N/A for this slice. If hooks are added, reviewer confirms comments explain what and why |

---

### YAML Documentation Standards (All Layers)

| Rule | Name | Verification Method | Implementation Detail |
|---|---|---|---|
| YML-DOC-01 | Mandatory Description Field | **dbt-score** | Built-in `has_description` rule; severity: error. Every model, source, seed, and macro must have a non-empty description |
| YML-DOC-02 | Description Content Quality | **dbt-score** (custom rule) + **code review** | Custom dbt-score rule enforces minimum description length (≥50 characters) to prevent placeholder text. Reviewer evaluates whether descriptions explain business meaning, grain, filters, and testing rationale — not just technical derivation |

---

### Source YAML

| Rule | Name | Verification Method | Implementation Detail |
|---|---|---|---|
| SRC-YML-01 | Directory Location | **structural inspection** | Confirm `_sources.yml` files are in `models/staging/{source}/` |
| SRC-YML-02 | Filename Syntax | **structural inspection** + **custom script** | Confirm single `_sources.yml` per source directory; no individual source files |
| SRC-YML-03 | Database and Schema Configuration | **code review** | Reviewer confirms `database` and `schema` are defined for each source |
| SRC-YML-04 | Freshness Thresholds | **dbt-score** (custom rule) + **dbt source freshness** | Custom dbt-score rule `has_freshness_on_sources` checks that every source includes a freshness block; `dbt source freshness` validates thresholds at runtime |
| SRC-YML-05 | Source Key Testing | **dbt-score** + **dbt build (tests)** | dbt-score confirms `unique` and `not_null` tests exist on source PKs/BKs; `dbt build` runs them |
| SRC-YML-06 | Source Foreign Key Testing | **dbt build (tests)** + **code review** | `relationships` tests on source FKs run during `dbt build`; reviewer evaluates whether the right FKs are tested |

---

### Staging & Base YAML

| Rule | Name | Verification Method | Implementation Detail |
|---|---|---|---|
| STG-YML-01 | Directory Location | **structural inspection** | Confirm YAML files are co-located in `models/staging/{source}/` |
| STG-YML-02 | Filename Syntax | **structural inspection** + **custom script** | Confirm single `_models.yml` per staging directory; no individual model YAML files |
| STG-YML-03 | Staging PK Testing | **dbt-score** + **dbt build (tests)** | dbt-score's `has_unique_test` and `has_not_null_test` confirm PK tests exist; `dbt build` runs them |
| STG-YML-04 | Hash Collision Testing | **code review** + **dbt build (tests)** | Reviewer evaluates whether hash collision tests are warranted based on table size; tests run during `dbt build` where applied |

---

### Integration YAML

| Rule | Name | Verification Method | Implementation Detail |
|---|---|---|---|
| INT-YML-01 | Directory Location | **structural inspection** | Confirm `_models.yml` is in `models/integration/` |
| INT-YML-02 | Filename Syntax | **structural inspection** | Confirm single `_models.yml`; no individual model YAML files |
| INT-YML-03 | Integration PK Testing | **dbt-score** + **dbt build (tests)** | dbt-score confirms `unique` and `not_null` tests on PK; `dbt build` runs them |
| INT-YML-04 | Integration FK Testing | **dbt build (tests)** + **code review** | `relationships` tests validate FKs against parent staging models; reviewer confirms the right FKs are tested |
| INT-YML-05 | Join Cardinality Validation | **dbt build (tests)** + **code review** | `dbt_expectations.expect_table_row_count_to_equal_other_table` or equivalent row count comparison; reviewer evaluates whether cardinality is correctly validated |
| INT-YML-06 | Business Logic Constraints | **dbt build (tests)** + **code review** | `accepted_values`, custom singular tests, and `dbt_expectations` tests validate business rules; reviewer evaluates whether the highest-risk rules are covered |
| INT-YML-07 | Calculated Field Nullability | **dbt build (tests)** | `not_null` tests on calculated fields where nulls would indicate upstream gaps or logic errors |
| INT-YML-08 | CDM Accepted Values Testing | **dbt build (tests)** + **custom script** | `accepted_values` tests on string fields per CDM specification; `dbt_expectations.expect_column_values_to_be_between` on numeric fields per CDM min/max. Custom script cross-references CDM metadata CSVs to identify which fields have testable constraints |

---

### Mart YAML

| Rule | Name | Verification Method | Implementation Detail |
|---|---|---|---|
| MRT-YML-01 | Directory Location | **structural inspection** | Confirm YAML files are in `models/marts/{owner}/` |
| MRT-YML-02 | Filename Syntax | **structural inspection** | Confirm single `_models.yml` per mart directory; exposures in `_exposures.yml` |
| MRT-YML-03 | Mart PK Testing | **dbt-score** + **dbt build (tests)** | dbt-score confirms `unique` and `not_null` tests on PK; `dbt build` runs them |
| MRT-YML-04 | Public Interface Contracts | **dbt-score** (custom rule) | Custom rule `has_contract_on_marts` checks that all `fct_*` and `dim_*` models have `contract: {enforced: true}` |
| MRT-YML-05 | Contract Data Type Definitions | **dbt-score** (custom rule) + **dbt build (runtime)** | Custom rule `has_data_types_on_contracted_columns` checks every column defines `data_type`; dbt enforces contract compliance at runtime |
| MRT-YML-06 | Downstream Exposure Definitions | **N/A (this slice)** | No exposures in this vertical slice; rule will be enforced when downstream consumers exist |
| MRT-YML-07 | Complex Logic Unit Testing | **code review** | Reviewer evaluates whether models with complex SQL logic (regex parsing, window functions, multi-condition case statements) have `unit_tests` blocks; straightforward models may not need them |
| MRT-YML-08 | Statistical Volumetric Testing | **dbt build (tests)** + **code review** | `dbt_expectations.expect_table_row_count_to_be_between` and `expect_column_values_to_be_between` validate data volumes and value ranges; reviewer evaluates whether thresholds are appropriate |

---

### Macro YAML

| Rule | Name | Verification Method | Implementation Detail |
|---|---|---|---|
| MAC-YML-01 | Directory Location | **structural inspection** | Confirm macro YAML is in `macros/` |
| MAC-YML-02 | Filename Syntax | **structural inspection** | Confirm single `_macros.yml` |
| MAC-YML-03 | Macro Documentation and Arguments | **dbt-score** + **code review** | dbt-score `has_description` on macros; reviewer confirms argument documentation and defensive validation |

---

### Doc Blocks

| Rule | Name | Verification Method | Implementation Detail |
|---|---|---|---|
| DOC-YML-01 | When to Use Doc Blocks | **code review** | Reviewer evaluates whether shared column descriptions (e.g., `hk_*`, `created_at`) use doc blocks rather than duplicating inline descriptions across YAML files |
| DOC-YML-02 | Directory and File Location | **structural inspection** | Confirm `.md` doc block files are co-located with the YAML they support; project-wide blocks in `models/docs/` |
| DOC-YML-03 | Naming | **code review** | Reviewer confirms doc block names match the column or concept they describe |

---

### Verification Summary

| Verification Method | Rule Count | Percentage |
|---|---|---|
| **sqlfluff** (primary or contributing) | 16 | 16% |
| **dbt-project-evaluator** (primary or contributing) | 18 | 17% |
| **dbt-score** (primary or contributing) | 18 | 17% |
| **dbt build — tests** (primary or contributing) | 23 | 22% |
| **dbt build — runtime** (primary or contributing) | 7 | 7% |
| **custom script** (primary or contributing) | 17 | 17% |
| **structural inspection** (primary or contributing) | 24 | 23% |
| **code review** (primary or contributing) | 55 | 53% |
| **N/A (this slice)** | 4 | 4% |

> **Note:** Percentages sum to more than 100% because many rules use multiple verification methods. The count reflects every rule where the method contributes — either as the primary check or as a secondary safeguard.

The distribution is honest: just over half the rules require some degree of human judgment. That is not a failure of the tooling strategy; it reflects the reality that many standards govern *intent* and *semantics* — whether a name is meaningful, whether a description is substantive, whether the right business rules are tested — and no linter can reliably substitute for an analyst who understands the domain. The tooling strategy's value is in handling the other half: the formatting, structural, and testable rules that are tedious to check manually and easy to miss under deadline pressure. Automation covers the mechanical; review covers the meaningful.

---

## Open Questions

| # | Question | Owner | Impact |
|---|---|---|---|
| 1 | **Park ID reconciliation strategy**: Should int_parks join GeoParks and VistaReserve parks on a deterministic attribute match (park name similarity, region + ordinal), or rely on the stale asset_crosswalk, or require a manually curated seed file mapping the two ID systems? | Engineering + Business | Blocks int_parks; cascades to every downstream model |
| 2 | **Revenue batch grain**: Are revenue_batch records individual transactions or aggregated batch summaries? If aggregated, they cannot be unioned with pos_transactions in int_transactions and need their own integration model. | Engineering (data profiling) | Determines integration model count and fact model structure |
| 3 | **PII handling policy**: Customer profiles contain PII (names, addresses, potentially payment info). Should the dbt project apply column-level masking, exclude PII columns at staging, or handle sensitivity classification as a separate workstream? | Business + Legal | Affects stg_vistareserve__customer_profiles column selection |
| 4 | **CDM FunctionalLocation vs. Territory for parks**: The preliminary mapping uses FunctionalLocation from the Asset manifest, but Territory from applicationCommon or Account from nonProfitCore could also fit. Which CDM entity best represents a state park? | Engineering | Determines int_parks column definitions |
| 5 | **Snapshot cadence**: The snp_vistareserve__inventory_assets snapshot needs a run schedule. Since this is a local development project without a scheduler, should the snapshot be documented but not actively scheduled? | Engineering | Low impact; pattern demonstration only |

---

## Success Metrics

| Metric | Target | Measurement Method |
|---|---|---|
| `dbt build` completes without errors | 0 errors, 0 test failures | `dbt build --full-refresh` |
| sqlfluff passes on all SQL files | 0 linting violations | `sqlfluff lint models/ macros/ tests/ analyses/ snapshots/` |
| dbt-score passes on all models | All models meet minimum score threshold | `dbt-score score` |
| dbt-project-evaluator passes | 0 DAG violations, 0 naming violations | `dbt build -s package:dbt_project_evaluator` |
| All 8 staging models produce rows | Non-zero row count per model | `dbt show` or ad-hoc query |
| All 5 integration models produce rows | Non-zero row count per model | `dbt show` or ad-hoc query |
| All 6 mart models produce rows | Non-zero row count per model | `dbt show` or ad-hoc query |
| int_parks contains 50 rows | Exactly 50 (one per park unit) | Row count query |
| Revenue reconciliation passes | rpt total = fct_reservations total + fct_pos_transactions total | Singular test assert_revenue_sums_balance |

---

## Implementation Sequence

The following sequence respects the DAG's dependency order and front-loads the decisions that block the most downstream work.

1. **Project initialization** — virtual environment, dbt-core + dbt-duckdb, packages.yml, profiles.yml, dbt_project.yml, sqlfluff config, dbt-score config
2. **Source definitions** — _sources.yml for vistareserve and geoparks; run `dbt source freshness` to validate connectivity
3. **Seeds** — create all four business-domain seed CSVs (reservation_status_codes, transaction_type_codes, park_region_mappings, source_system_registry) and _seeds.yml; run `dbt seed`. CDM infrastructure seeds (if used) are additional — they do not substitute for the four required seeds.
4. **Base models** — base_vistareserve__customer_profiles and base_vistareserve__asset_crosswalks; profile to confirm deduplication behavior
5. **Staging models** — all 8 staging models plus _models.yml with tests; run `dbt build -s tag:staging`; run sqlfluff; run dbt-score
6. **Integration models** — starting with int_parks (resolve open question #1 first), then int_contacts, int_customer_assets, int_transactions, int_reservations; profile at each step per ALL-TST-03. Before declaring integration complete, verify: all surrogate keys generated, all specified sources consumed, all FK joins implemented, all YAML columns match SQL output.
7. **Macros** — build spec-required macros (generate_source_system_tag, clean_string, cast_park_id_to_varchar) plus any CDM infrastructure macros; document all in _macros.yml with argument validation per SQL-MAC-03
8. **Mart models** — dim_parks, dim_customers, dim_reservation_inventory, then fct_reservations, fct_pos_transactions, then rpt_park_revenue_summary
9. **Singular tests** — write after marts are stable; validate cross-layer reconciliation
10. **Snapshot** — snp_vistareserve__inventory_assets
11. **Analyses** — profile_customer_duplicate_rate, audit_park_id_crosswalk_coverage
12. **Full validation** — `dbt build --full-refresh`; sqlfluff lint; dbt-score; dbt-project-evaluator

### Phase Completion Checklist

Before declaring any phase complete, verify against this spec:

1. **All deliverables present** — every model, seed, macro, test, and YAML file listed in this spec for that phase exists
2. **All inputs consumed** — if this spec says a model consumes multiple staging sources, all are consumed
3. **All transformations applied** — surrogate keys, unions, joins, deduplication, CDM column mapping as specified
4. **All YAML complete** — _models.yml, _sources.yml, _seeds.yml, _macros.yml with descriptions, tests, and type overrides as required
5. **YAML/SQL consistency** — every column in YAML exists in SQL output; no duplicate model entries
6. **No orphaned artifacts** — no unused macros, no dead code, no Python scripts that should be dbt macros

---

## Expansion Path

Once this slice is validated, subsequent slices follow the same pattern. The recommended order, informed by business priority and data dependency:

1. **Finance** (StateGov Financials + GrantTrack) — adds GL, AP, encumbrances, grants; enables revenue-to-ledger reconciliation
2. **Assets** (InfraTrak) — adds physical assets, work orders, condition assessments; enriches dim_parks and creates dim_assets
3. **Human Capital** (PeopleFirst) — adds employees, positions, payroll; creates dim_employees
4. **Natural Resources** (BioSurvey) — adds ecological surveys, species data, water quality
5. **Visitor Use** (TrafficCount) — adds anonymous visitor metrics; enables visitor estimation models
6. **Historical Reservations** (LegacyRes) — extends int_reservations with 2005–2021 data; requires format normalization
7. **Law Enforcement** (RangerShield) — constrained by CJIS air-gap; requires separate integration pattern with restricted access controls

Each subsequent slice adds sources, staging models, and integration models — then extends or creates new mart models. The integration layer grows incrementally; the parks dimension gets richer with each slice as new systems contribute park-level data.
