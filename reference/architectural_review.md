# Architectural Review: DCR Source Data Readiness for dbt

**Reviewer**: Analytics Engineering
**Date**: February 20, 2026
**Scope**: 10 source systems, 45 tables, evaluated against `dbt_project_standards.md`

---

## Executive Summary

The DCR source data is well-constructed and architecturally sound for its stated purpose: providing realistic, messy-yet-understandable synthetic data for a multi-layer dbt project. The 10 systems and 45 tables offer genuine breadth across financial, operational, HR, geospatial, ecological, revenue, and law enforcement domains. Internal schema quality is high — primary keys are defined, foreign keys enforce referential integrity within each system, CHECK constraints validate enums and ranges, and documented quality issues (stale crosswalks, regional gaps, duplicate customers) faithfully mirror the kinds of problems that make real government data challenging to model.

That said, the review identified several structural gaps and misalignments with the dbt project standards that should be resolved before model development begins. These are organized below by severity.

---

## Critical Gaps (Must Resolve Before Development)

### 1. No Microsoft Common Data Model (CDM) Mapping Exists

The standards are unusually prescriptive on this point. Rule **SQL-INT-03** requires integration model entity names to come from the Microsoft Common Data Model. Rule **SQL-INT-05** goes further: integration models *may not contain columns — aside from foreign keys or surrogate keys — that are not specified by the CDM entity definition*. Columns that are valuable but not in the CDM must be dropped at the integration layer and joined back at marts if needed.

No CDM mapping document has been prepared. Before writing a single integration model, the team needs to research which CDM entities (from the non-profit core manifest or alternatives) correspond to the source entities — parks, grants/awards, physical assets, employees, reservations, incidents, ecological surveys, financial transactions, etc. — and document which source columns map to CDM fields, which must be dropped, and which may warrant an exception request per the standards. This is not a minor documentation task; it will shape the structure of every integration model.

**Recommendation**: Produce a CDM entity mapping spreadsheet covering all planned integration models before development begins.

### 2. Cross-System Park Identifier Reconciliation Strategy Is Undefined

"Parks" is the central dimension of this entire dataset. At least six systems maintain independent park references:

| System | Identifier | Type | Coverage |
|--------|-----------|------|----------|
| VistaReserve | `park_id` | INTEGER | All 50 parks |
| InfraTrak | `park_id` | INTEGER | All 50 parks (data only for 28) |
| GeoParks | `geo_park_id` | VARCHAR | All 50 parks |
| BioSurvey | `park_id` (via `survey_sites`) | INTEGER | Subset |
| LegacyRes | `legacy_park_id` | VARCHAR | Only 15 mapped to current IDs |
| TrafficCount | `park_id` | INTEGER | 8–12 parks |

VistaReserve and InfraTrak share the same `park_id` INTEGER scheme, which simplifies things. But GeoParks uses a VARCHAR-based `geo_park_id` with no enforced FK to either. The `legacy_park_crosswalk` maps only 30% of legacy parks. And BioSurvey's `survey_sites.park_id` references an INTEGER park_id but has no FK constraint pointing to any specific system.

The standards require a unidirectional DAG (ALL-DAG-01) and integration models that harmonize across systems (SQL-INT-08, SQL-INT-11). The team needs a documented decision on which system's park identifier is the "golden" key, and whether a base model or seed is needed to reconcile the GeoParks VARCHAR IDs to the INTEGER scheme used everywhere else.

**Recommendation**: Define the parks integration strategy — golden key source, crosswalk handling, and the plan for GeoParks' divergent ID scheme — before building staging models.

### 3. Employee/Person Entity Has No Cross-System Linkage

People appear in five separate systems with five different identifiers and no crosswalk:

- **PeopleFirst**: `employee_id` (permanent staff), `seasonal_emp_id` (seasonal workers)
- **InfraTrak**: `employee_id` (maintenance staff, inspectors) — presumably overlaps with PeopleFirst but no FK enforces this
- **RangerShield**: `badge_number` (sworn officers) — completely isolated by CJIS air-gap
- **VistaReserve**: `customer_id` (guests) — distinct population, but staff may also appear as customers
- **LegacyRes**: `legacy_cust_id` — historical guests with no crosswalk to current customer IDs

The standards expect integration models to "produce one authoritative version of each business concept" (SQL-INT-11). For employees, the team needs to decide: is the integration entity "all DCR workers" (permanent + seasonal + officers), or are these separate integration models? Is the InfraTrak `employee_id` the same namespace as PeopleFirst? The air-gapped RangerShield data makes a unified person model impractical for officers — this constraint needs to be explicitly documented rather than discovered mid-development.

**Recommendation**: Define the person/employee integration scope and document which systems can and cannot be joined at the person level.

---

## Significant Gaps (Should Resolve Before or During Early Development)

### 4. No Seed Files Exist for Lookup Data

The standards emphasize seed-driven lookups over hardcoded CASE statements (ALL-PERF-01) and require YAML properties for every seed (SQL-SEED-05). Several source tables are natural seed candidates that should be extracted before development:

- `species_codes` from BioSurvey (static reference data, custom 1993 scheme)
- Status value mappings (work order statuses, reservation statuses, grant statuses, etc.)
- `chart_of_accounts` structure from SGF (hierarchical lookups for fund/division/program/object)
- Water quality `protocol_era` definitions (needed for methodology-aware analysis)
- Region-to-name mappings (regions 1–4 appear everywhere but names only in org_units)

Some of these are already source tables (like `species_codes` and `chart_of_accounts`) and may not need to become seeds if they're consumed through staging. But static mappings that don't exist in any source — like a unified status code mapping across systems — will need seed files.

**Recommendation**: Inventory which lookups should be seeds versus staged source tables. Create seed CSVs for any cross-system mappings.

### 5. Sensitivity Classifications Need a dbt-Layer Policy

The sources contain data at four sensitivity levels (Public, Internal, Confidential, Restricted — Statutory). Several specific columns carry elevated risk:

- `ssn_last4` in PeopleFirst employees
- `partial_card_mask` in LegacyRes customers
- `tin_masked` in SGF vendors
- All of RangerShield (CJIS-restricted)
- Cultural resource locations in GeoParks (statutorily restricted)
- Endangered species locations in BioSurvey (statutorily restricted)

The dbt project standards do not explicitly address data sensitivity, masking, or access controls. The team needs a policy on whether PII and restricted columns flow through to marts, are dropped at staging, or are masked. Without this, an analyst could inadvertently surface SSN fragments or protected species locations in a report model.

**Recommendation**: Add a data sensitivity handling policy to the standards (or as a companion document) before development reaches the integration layer.

### 6. The `asset_crosswalk` Table Needs a Base Model Strategy

The VistaReserve `asset_crosswalk` is the only formal inter-system identifier mapping, and it's documented as stale and incomplete for post-2022 assets. It links VistaReserve inventory IDs to GeoParks feature IDs and InfraTrak asset tags — but many rows will have NULLs in one or both foreign columns.

Per the standards, this kind of pre-processing complexity (incomplete data, multi-system references) is a candidate for a base model (SQL-BASE-06, SQL-BASE-07). The team should decide whether to stage it as-is, build a base model that fills gaps or flags staleness, or handle the reconciliation entirely at the integration layer.

**Recommendation**: Design the crosswalk handling approach (base model vs. integration-layer logic) before building asset-related models.

---

## Minor Observations (Address During Development)

### 7. Source Column Naming Is Mostly Clean, With a Few Staging Rename Candidates

Most source columns already follow snake_case (ALL-FMT-05), which is good. A handful will need renaming per SQL-STG-09 (rename for understandability) and ALL-NAME-03 (abbreviation restraint):

- `wo_id`, `wo_type` → `work_order_id`, `work_order_type`
- `fci_score` → `facility_condition_index_score`
- `tin_masked` → `tax_id_number_masked`
- `ssn_last4` → should be evaluated for exclusion rather than renaming
- `ecoli_cfu_100ml` → `e_coli_colony_forming_units_per_100ml` (or an acceptable shorter form)
- `shpo_reference_number` → could stay if the acronym is universally understood in the domain; otherwise expand

### 8. Duplicate Parks Tables Across Systems Are a Feature, Not a Bug

Both VistaReserve and InfraTrak have their own `parks` tables with identical `park_id` INTEGER keys but slightly different columns (VistaReserve adds `has_unstaffed_kiosk`; InfraTrak does not). GeoParks has `parks_master` with a different key type entirely. This is intentional — it mirrors the real-world pattern of disconnected systems maintaining their own copies. The integration layer will need to reconcile these into a single `int_parks` model, coalescing the richest attributes.

### 9. The BioSurvey `survey_sites.park_id` FK Target Is Ambiguous

This column is `INTEGER NOT NULL` with no FK constraint. It presumably references the same `park_id` INTEGER used by VistaReserve and InfraTrak, but this should be confirmed. If it does, the staging model for `survey_sites` should document which system's parks table it logically references.

### 10. RangerShield Data Will Require a Separate Integration Pattern

The air-gapped constraint means RangerShield data cannot be joined to other systems at the person or location level. Incident locations are narrative text, not coordinates. Officer badge numbers have no crosswalk to PeopleFirst employee IDs. The standards' expectation of cross-system harmonization (SQL-INT-08, SQL-INT-11) will need a documented exception for law enforcement models — they'll likely be self-contained integration models that produce standalone facts and dimensions.

### 11. Temporal Boundaries Create Natural Model Scoping Questions

Several sources have hard temporal boundaries that downstream models will need to address:

- VistaReserve: March 2021 onward only (the "data cliff")
- LegacyRes: 2005–2021 with three format eras
- BioSurvey water quality: three protocol eras (pre-2005, 2005–2018, 2018+)
- TrafficCount: 2024 pilot onward only

Whether to union historical and current data into single integration models (e.g., a unified reservations timeline spanning LegacyRes and VistaReserve) or keep them separate is an architectural decision that should be made early.

---

## Comprehensiveness Assessment

The source data is more than sufficient for a full multi-layer dbt project. A rough count of the modeling surface area:

- **Staging**: 45 source tables → ~45 staging models (plus potential base models for crosswalks, legacy format handling, and customer deduplication)
- **Integration**: At minimum 8–12 integration models — parks, employees, assets, grants/awards, financial accounts, reservations, incidents, species/surveys, visitors, vendors
- **Facts**: Reservation completions, revenue transactions, work order completions, grant disbursements, condition assessments, incident reports, survey observations, visitor counts, payroll disbursements
- **Dimensions**: Parks, employees, assets, customers, species, accounts/funds, officers, organizational units
- **Reports**: Revenue by park/region, deferred maintenance backlog, grant compliance status, visitor trends, workforce distribution

The data supports interesting analytical questions that span multiple systems (e.g., "what is the relationship between asset condition scores, maintenance spending, and revenue per park?"), which is exactly the kind of multi-source integration challenge a dbt project should demonstrate.

---

## Real-World Plausibility Assessment

This is a strength of the dataset. The sources convincingly replicate patterns found in real government data environments:

- **Institutional accretion over decades** — systems ranging from 1993 (Access database) to 2024 (IoT pilot), each with its own ID scheme and data model
- **Partial implementations** — InfraTrak covering only 2 of 4 regions, TrafficCount sensors at 15% of parks
- **Manual workarounds** — the GrantTrack Excel workbook, paper kiosk logs, narrative-text incident locations
- **Known quality issues documented honestly** — 20% customer duplicates, 2–5% reconciliation gaps, stale crosswalks, regional data discipline variance
- **Compliance constraints** — CJIS air-gap, archaeological site protections, PII handling across multiple sensitivity levels
- **The "bus factor" problem** — single-person dependencies on BioSurvey and GrantTrack

The documented quality issues are not just realistic — they're the kind of issues that make dbt modeling interesting and instructive. They'll exercise base models (deduplication, format harmonization), integration logic (cross-system reconciliation with incomplete crosswalks), and testing strategies (orphan detection, volumetric checks for regional gaps).

---

## Summary of Recommendations

| Priority | Action | Blocking? |
|----------|--------|-----------|
| **Critical** | Produce CDM entity mapping for all planned integration models | Yes — shapes every integration model |
| **Critical** | Define parks identifier reconciliation strategy (golden key, crosswalk approach) | Yes — parks is the central dimension |
| **Critical** | Define employee/person integration scope and document air-gap constraints | Yes — affects integration model count and structure |
| **Significant** | Inventory seed vs. staged-source decisions for lookup data | No, but should precede integration work |
| **Significant** | Establish data sensitivity handling policy for PII/restricted columns | No, but should precede integration work |
| **Significant** | Design asset crosswalk base model strategy | No, but should precede asset-related models |
| **Minor** | Confirm BioSurvey park_id FK target | During staging development |
| **Minor** | Decide on historical data unification strategy (LegacyRes + VistaReserve, protocol eras) | During integration planning |
