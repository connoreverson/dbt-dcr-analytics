# CDM Entity Exception Request

## Form: Custom Entity Justification for Integration Model

**Model:** `int_ecological_surveys`
**Date:** 2026-03-03
**Requested by:** Engineering (dbt implementation team)
**Standards impacted:** SQL-INT-03 (Entity Name Word Choice), SQL-INT-05 (CDM Column Conformance)

---

## 1. Business Entity Being Modeled

**Entity name:** EcologicalSurvey (a dated field observation from a named ecological monitoring site within a DCR park)
**Grain:** One row per ecological observation event across three observation types: flora/fauna species surveys, water quality sampling events, and invasive species occurrence and treatment records
**Source systems:** BioSurvey_Legacy (DCR-NRM-01, Microsoft Access database active since 1993)
**Business definition:** An ecological survey is any systematic field observation conducted by DCR's Natural Resources Management program at a designated survey site within park boundaries. DCR manages three distinct observation types under a shared field program: flora/fauna abundance surveys (species counts and density estimates), water quality sampling events (seven abiotic parameters across three protocol eras), and invasive species occurrence records (spatial extent and treatment documentation). All three types share a survey site as the geographic anchor, which resolves to a park via int_parks.

---

## 2. Candidate CDM Entities Evaluated

The `identify_candidate_cdm` macro returned a maximum column coverage of 1.1% (Address entity, 4/360 columns). All matches were coincidental attribute overlaps (latitude, longitude, description-type fields). The full evaluation:

### 2a. Address (applicationCommon) — Top CDM candidate at 1.1%

| Criterion | Assessment |
|---|---|
| **Column coverage** | 4/360 columns matched: latitude, longitude (geographic coordinates), and two partial text matches. |
| **Semantic fit** | None. Address models a mailing or physical location record in a CRM context. An ecological survey observation is not an address. |
| **Verdict** | Rejected. Geographic coordinate columns caused a spurious match; the entity has no ecological survey semantics. |

### 2b. ProgramItem / ProgramItemRelationship (nonProfitCore)

| Criterion | Assessment |
|---|---|
| **Column coverage** | 1/39 matched (ProgramItem); 1/78 matched (ProgramItemRelationship). The matched column is a generic attribute (description or status equivalent). |
| **Semantic fit** | None. ProgramItem models a line item within a grant program budget. A species count or water quality test is not a grant program item. |
| **Verdict** | Rejected. Coincidental name overlap with no semantic connection to field ecological monitoring. |

### 2c. Stakeholder (nonProfitCore)

| Criterion | Assessment |
|---|---|
| **Column coverage** | 1/291 matched. |
| **Semantic fit** | None. Stakeholder represents an organizational actor in a fundraising or grant relationship. DCR survey sites and field observations are not stakeholders. |
| **Verdict** | Rejected. Zero semantic fit. |

### 2d. ObservationIdentifier (cdmfoundation)

Not evaluated by the macro (not in the curated manifests). The CDM foundation does define `ObservationIdentifier`, but it is a metadata label entity, not an event entity, and has no columns relevant to species counts, water quality parameters, or spatial extent.

---

## 3. Conclusion: No Standard CDM Entity Is Appropriate

The CDM was designed for commercial CRM, healthcare, and nonprofit grant management. Ecological field surveys — combining species population biology, water chemistry, spatial extent measurement, and treatment tracking — belong to a domain the CDM does not cover. Specific gaps:

- **No species observation entity**: The CDM has no construct for recording species presence/absence or abundance at a geographic point.
- **No water quality entity**: No CDM entity models abiotic parameter measurements (dissolved oxygen, turbidity, pH, nutrients) from a field sampling event.
- **No invasive species entity**: Treatment records (herbicide application, manual removal, spatial extent) have no CDM equivalent.
- **No multi-protocol entity**: The three-era protocol structure (pre-2005, 2005–2018, 2018+) with different parameter sets per era has no CDM analog.

This situation mirrors the prior custom exceptions: government natural resource monitoring falls entirely outside the CDM's commercial domain.

---

## 4. Proposed Custom Entity: `EcologicalSurvey`

### 4a. Entity Definition

| Property | Value |
|---|---|
| **Entity name** | `EcologicalSurvey` |
| **Extends** | None — this is a stand-alone domain entity with no useful CDM parent |
| **Manifest context** | Custom extension (`dcr/EcologicalSurvey.1.0`) within a proposed NaturalResources family |
| **Integration model** | `int_ecological_surveys` |
| **Description** | A dated ecological field observation conducted at a named survey site within a DCR park. Covers three observation sub-types: flora/fauna species abundance surveys, water quality sampling events, and invasive species occurrence and treatment records. The observation_type discriminator identifies the active schema for each row; type-specific columns are null for the other types. |

### 4b. Column Definitions

| Column | Data Type | Source | CDM Lineage | Role |
|---|---|---|---|---|
| `ecological_surveys_sk` | `VARCHAR` | Generated | Surrogate key (SQL-INT-06); includes type prefix for cross-type uniqueness | PK |
| `observation_id` | `VARCHAR` | BioSurvey native IDs (FFS-, test_id, observation_id) | No CDM analog — government ecological survey identifier | BK |
| `site_id` | `VARCHAR` | BioSurvey `survey_sites.site_id` | No CDM analog — ecological survey site | FK |
| `parks_sk` | `VARCHAR` | Generated via int_parks | FK to Park custom entity | FK |
| `observation_type` | `VARCHAR` | Generated (discriminator) | **Custom extension** — flora_fauna, water_quality, invasive_species | Classification |
| `observation_date` | `DATE` | BioSurvey survey_date / sample_date / observation_date | No CDM analog — ecological event date | Event |
| `species_code` | `VARCHAR` | BioSurvey species_code | **Custom extension** — FK to species codes reference | Species |
| `observer_name` | `VARCHAR` | BioSurvey flora_fauna observer_name | No CDM analog — field biologist name | Personnel |
| `latitude` | `NUMERIC` | BioSurvey flora_fauna / invasive_species latitude | **Custom extension** — WGS84 decimal latitude of observation point | Geography |
| `longitude` | `NUMERIC` | BioSurvey flora_fauna / invasive_species longitude | **Custom extension** — WGS84 decimal longitude | Geography |
| `count_estimate` | `INTEGER` | BioSurvey flora_fauna count_estimate | **Custom extension** — estimated individual count | Biodiversity |
| `density_estimate_per_hectare` | `NUMERIC` | BioSurvey flora_fauna density | **Custom extension** — individuals per hectare | Biodiversity |
| `extent_square_meters` | `NUMERIC` | BioSurvey invasive_species extent | **Custom extension** — infestation extent in m² | Invasive Management |
| `treatment_applied` | `VARCHAR` | BioSurvey invasive_species treatment_applied | **Custom extension** — treatment method | Invasive Management |
| `treatment_date` | `DATE` | BioSurvey invasive_species treatment_date | **Custom extension** — treatment application date | Invasive Management |
| `dissolved_oxygen_mgl` | `NUMERIC` | BioSurvey water_quality dissolved_oxygen | **Custom extension** — mg/L | Water Quality |
| `ph_level` | `NUMERIC` | BioSurvey water_quality ph_level | **Custom extension** — pH scale | Water Quality |
| `ecoli_cfu_100ml` | `INTEGER` | BioSurvey water_quality ecoli_cfu_100ml | **Custom extension** — CFU per 100 mL | Water Quality |
| `turbidity_ntu` | `NUMERIC` | BioSurvey water_quality turbidity | **Custom extension** — NTU | Water Quality |
| `temperature_celsius` | `NUMERIC` | BioSurvey water_quality temperature | **Custom extension** — °C | Water Quality |
| `nitrogen_mgl` | `NUMERIC` | BioSurvey water_quality nitrogen | **Custom extension** — mg/L total nitrogen | Water Quality |
| `phosphorus_mgl` | `NUMERIC` | BioSurvey water_quality phosphorus | **Custom extension** — mg/L total phosphorus | Water Quality |
| `protocol_era` | `VARCHAR` | BioSurvey water_quality protocol_era | **Custom extension** — testing protocol version | Water Quality |

### 4c. Scope Notes

**Endangered species monitoring excluded.** BioSurvey_Legacy also contains an `endangered_species_monitoring` table, but this data is Restricted — Statutory (sensitive species location data protected under state and federal regulations). A future `int_endangered_species_monitoring` model would require separate data handling controls and is out of scope for the current expansion.

**Field observations raw excluded.** The `field_observations_raw` staging model represents the original mixed-entity BioSurvey table. The three clean typed tables (`flora_fauna_surveys`, `water_quality_tests`, `invasive_species_observations`) are derived from it. Only the clean tables are included in this integration model.

**Relationship to other integration models:**

| Parent | Child | FK Column | Cardinality | Notes |
|---|---|---|---|---|
| `int_parks` (Park) | `int_ecological_surveys` (EcologicalSurvey) | `parks_sk` | 1 park : M observations | Resolved via survey_sites.park_id → infratrak_park_id |

---

## 5. Implementation Path

1. **Add `EcologicalSurvey` rows to CDM extension catalog.** Create rows in `seeds/cdm_catalogs/column_catalog_dcr_extensions.csv` defining each column above with `cdm_entity_name = 'EcologicalSurvey'`.
2. **Update `seeds/cdm_crosswalk.csv`.** Add rows mapping `int_ecological_surveys` to `EcologicalSurvey`, documenting the staging source for each column.
3. **Update `models/integration/_models.yml`.** Add `meta: cdm_entity: EcologicalSurvey` and `meta: cdm_entity_rationale:` referencing this document.
4. **No SQL changes required.** The model's column names, logic, and relationships are final.

---

## 6. Precedent and Governance Note

This exception follows the pattern established by `int_parks` (custom `Park` entity), `int_financial_transactions` (custom `FinancialTransaction` entity), and `int_physical_assets` (custom `PhysicalAsset` entity). All four cases arise from the same root cause: the Microsoft CDM was designed for commercial and nonprofit domains, and DCR's operational vocabulary — state park management, government GL accounting, physical asset management, and ecological monitoring — falls outside those domains.

The `EcologicalSurvey` entity is the fourth custom extension in the DCR CDM catalog.
