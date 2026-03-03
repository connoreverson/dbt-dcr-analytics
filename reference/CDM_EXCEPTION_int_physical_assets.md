# CDM Entity Exception Request

## Form: Custom Entity Justification for Integration Model

**Model:** `int_physical_assets`
**Date:** 2026-03-03
**Requested by:** Engineering (dbt implementation team)
**Standards impacted:** SQL-INT-03 (Entity Name Word Choice), SQL-INT-05 (CDM Column Conformance)

---

## 1. Business Entity Being Modeled

**Entity name:** PhysicalAsset (a discrete, individually managed piece of public infrastructure owned or maintained by DCR)
**Grain:** One row per physical asset or GIS infrastructure feature — two source populations, undeduplicated
**Source systems:** InfraTrak Lifecycle (DCR-AST-01, 2,602 EAM records from Regions 1 & 2) and GeoParks Enterprise (DCR-GEO-01, 10,913 GIS feature records from all 50 parks)
**Business definition:** A physical asset is any individually managed piece of public infrastructure — a building, trail, road, bridge, dam, campsite, utility corridor, or marine structure — that DCR owns or maintains within its park boundaries. Physical assets carry two types of attributes that serve different analytical purposes: lifecycle attributes (replacement value, lifespan, condition assessment scores) and geographic attributes (geometry, classification, positional accuracy). These attribute types come from separate systems that were originally synchronized in 2020 but have not been linked since then due to identifier drift.

---

## 2. Candidate CDM Entities Evaluated

### 2a. FunctionalLocation (Asset 1.0) — Plan-specified first review

| Criterion | Assessment |
|---|---|
| **Column coverage** | 1 column: `functionalLocationId`. This is the entirety of the entity definition in the curated Asset manifest. |
| **Semantic fit** | Good. "A physical location where assets are installed or maintained" accurately describes a DCR park infrastructure feature — trails, buildings, and utility corridors are all installations within managed locations. |
| **Unmappable attributes** | All 16 model columns beyond the ID are unmappable: `feature_class`, `sub_type`, `description`, `installation_year`, `replacement_value`, `expected_lifespan_years`, `point_latitude`, `point_longitude`, `geometry_wkt`, `positional_accuracy_meters`, `last_updated`, `status`, `is_visible_in_survey`, `source_system`, `parks_sk`, `asset_id`. |
| **Verdict** | Rejected as-is. Correct semantic framing (the int_parks exception made the same observation about FunctionalLocation). Adopting it requires extending with every domain-specific column, at which point we are defining a custom entity under a FunctionalLocation label. The proposed `PhysicalAsset` entity extends FunctionalLocation explicitly. |

### 2b. CustomerAsset (Asset 1.0)

| Criterion | Assessment |
|---|---|
| **Column coverage** | 3 columns: `customerassetId`, `msrex_InstallationDate`, `msrex_SerialNumber`. `msrex_InstallationDate` maps loosely to `installation_year`; `msrex_SerialNumber` maps loosely to `asset_id`. |
| **Semantic fit** | Poor. CustomerAsset represents "a product or device associated with a customer" — the commercial analog of a piece of installed equipment under a service contract. DCR assets are public infrastructure, not customer-owned devices. Also, `int_customer_assets` already uses CustomerAsset for VistaReserve's bookable inventory (campsites, cabins) — adopting it here would conflate two distinct asset registries. |
| **Verdict** | Rejected. Wrong semantic abstraction and already claimed by `int_customer_assets`. |

### 2c. ProgramItemRelationship (nonProfitCore)

| Criterion | Assessment |
|---|---|
| **Column coverage** | 3/78 columns (3.8%) — the top result from `identify_candidate_cdm`. The matched columns are superficial string overlaps (`status`, `description`, `source_system`). |
| **Semantic fit** | None. ProgramItemRelationship models connections between programmatic activities in a nonprofit grant management context. A trail or building is not a grant program relationship. |
| **Verdict** | Rejected. The column match is coincidental; the semantic fit is zero. |

### 2d. Product (applicationCommon)

| Criterion | Assessment |
|---|---|
| **Column coverage** | ~2% estimated. `description` matches; `status` has a loose equivalent. No columns for geometry, lifespan, replacement cost, or asset classification. |
| **Semantic fit** | Poor. Product represents sellable goods or service catalog items. Public infrastructure assets are not products in any meaningful commercial or nonprofit sense. |
| **Verdict** | Rejected. Commercial product taxonomy does not transfer to government infrastructure management. |

---

## 3. Conclusion: No Standard CDM Entity Is Appropriate

No entity in the curated CDM manifests (applicationCommon, nonProfitCore, Asset, Visits, cdmfoundation) provides both semantic correctness and adequate column coverage for government physical infrastructure management. The situation mirrors the `int_parks` exception:

- **FunctionalLocation** has correct semantics but zero usable columns beyond the ID (a stub entity)
- **CustomerAsset** has a small number of relevant columns but the wrong domain context
- All other candidates match only generic attributes (`status`, `description`) that appear in nearly every entity

The CDM was designed for commercial CRM, healthcare, and financial services. Geospatial government infrastructure management — combining GIS geometry, EAM lifecycle data, and condition assessment scoring — is not covered by any standard manifest.

An additional complicating factor: `int_physical_assets` is a heterogeneous union of two source populations (InfraTrak EAM assets and GeoParks GIS features) that cannot be joined at the individual record level due to identifier drift in the cross-system crosswalk. No CDM entity is designed to represent this kind of system-boundary artifact, where the same conceptual "asset" is tracked independently by an EAM system and a GIS system with no synchronized identifier.

---

## 4. Proposed Custom Entity: `PhysicalAsset`

### 4a. Entity Definition

| Property | Value |
|---|---|
| **Entity name** | `PhysicalAsset` |
| **Extends** | `FunctionalLocation` (Asset manifest) — inherits `functionalLocationId` as the base identity pattern |
| **Manifest context** | Custom extension (`dcr/PhysicalAsset.1.0`) within the Asset family |
| **Integration model** | `int_physical_assets` |
| **Description** | A discrete, individually managed piece of public infrastructure (building, trail, road, bridge, dam, campsite, utility corridor, or marine structure) owned or maintained by DCR within its park boundaries. Carries both lifecycle attributes (sourced from InfraTrak EAM) and geographic attributes (sourced from GeoParks GIS). Records from each source are maintained as distinct rows because the cross-system identifier crosswalk is stale and cannot support record-level deduplication. |

### 4b. Column Definitions

| Column | Data Type | Source | CDM Lineage | Role |
|---|---|---|---|---|
| `physical_assets_sk` | `VARCHAR` | Generated | Surrogate key (SQL-INT-06), unique within each source system | PK |
| `asset_id` | `VARCHAR` | InfraTrak `asset_tag` / GeoParks `feature_id` | Modeled after `FunctionalLocation.functionalLocationId` — the system-native identifier for this physical element | BK |
| `parks_sk` | `VARCHAR` | Generated | FK to `int_parks.parks_sk` — inherited from `Park` custom entity | FK |
| `feature_class` | `VARCHAR` | InfraTrak `asset_category` / GeoParks `feature_class` | **Custom extension** — broad infrastructure type (Trail, Road, Building, Bridge, etc.) | Classification |
| `sub_type` | `VARCHAR` | GeoParks `sub_type` | **Custom extension** — secondary classification refining feature_class | Classification |
| `description` | `VARCHAR` | InfraTrak `description` | Standard CDM attribute (`description` appears across many entities as free-text narrative) | Descriptive |
| `installation_year` | `INTEGER` | InfraTrak `construction_year` / GeoParks `installation_year` | Analogous to `CustomerAsset.msrex_InstallationDate` (year-only precision) | Lifecycle |
| `replacement_value` | `NUMERIC` | InfraTrak `replacement_value` | **Custom extension** — estimated full replacement cost in USD; critical for capital planning | Lifecycle |
| `expected_lifespan_years` | `INTEGER` | InfraTrak `expected_lifespan_years` | **Custom extension** — design lifespan in years; used for depreciation and capital renewal forecasting | Lifecycle |
| `point_latitude` | `NUMERIC` | InfraTrak `latitude` | **Custom extension** — WGS84 decimal latitude for point-located InfraTrak assets | Geography |
| `point_longitude` | `NUMERIC` | InfraTrak `longitude` | **Custom extension** — WGS84 decimal longitude for point-located InfraTrak assets | Geography |
| `geometry_wkt` | `VARCHAR` | GeoParks `geometry_wkt` | **Custom extension** — WKT geometry for GIS features; supports LINESTRING and POLYGON in addition to POINT | Geography |
| `positional_accuracy_meters` | `NUMERIC` | GeoParks `positional_accuracy_meters` | **Custom extension** — documented horizontal GPS/GIS error; relevant for joining geometry to field inspection data | Geography |
| `last_updated` | `DATE` | GeoParks `last_updated` | **Custom extension** — GIS team's last review date for this feature | Audit |
| `status` | `VARCHAR` | GeoParks `status` | **Custom extension** — operational lifecycle flag (Active / Inactive-Abandoned) | Operational |
| `is_visible_in_survey` | `BOOLEAN` | InfraTrak `is_visible_in_survey` | **Custom extension** — EAM survey scope flag; determines whether this asset is included in condition assessment cycles | EAM |
| `source_system` | `VARCHAR` | Generated | Infrastructure column — identifies the originating source system (DCR-AST-01 or DCR-GEO-01) | Audit |

### 4c. Normalization and Data Quality Notes

**No deduplication is applied.** This is a deliberate architectural decision, not a defect. The VistaReserve asset crosswalk (`stg_vistareserve__asset_crosswalks`) nominally links InfraTrak asset tags to GeoParks feature IDs, but the crosswalk was built against legacy identifier formats (GEO-* for GeoParks, plain AST-* integers for InfraTrak) that predate the current INF-* and AST-{park}-{seq} schemes. The crosswalk cannot be applied to current records.

As a result, `int_physical_assets` is a heterogeneous union. Records from the two source populations are distinguishable via `source_system`. Downstream marts that require a single population should filter accordingly. Future work to rebuild the crosswalk against current identifiers would enable record-level deduplication and attribution.

**Column sparsity by source:**
- InfraTrak records have: `description`, `replacement_value`, `expected_lifespan_years`, `point_latitude`, `point_longitude`, `is_visible_in_survey`; no `geometry_wkt`, `positional_accuracy_meters`, `last_updated`, `status`
- GeoParks records have: `sub_type`, `geometry_wkt`, `positional_accuracy_meters`, `last_updated`, `status`; no `description`, `replacement_value`, `expected_lifespan_years`, `point_latitude`, `point_longitude`

**Relationship to other integration models:**

| Parent | Child | FK Column | Cardinality | Notes |
|---|---|---|---|---|
| `int_parks` (Park) | `int_physical_assets` (PhysicalAsset) | `parks_sk` | 1 park : M assets | Each physical asset belongs to one park. GeoParks features join via `geo_park_id`; InfraTrak assets join via `infratrak_park_id`. |

---

## 5. Implementation Path

1. **Add `PhysicalAsset` rows to CDM extension catalog.** Create rows in `seeds/cdm_catalogs/column_catalog_dcr_extensions.csv` defining each column above with `cdm_entity_name = 'PhysicalAsset'`.
2. **Update `seeds/cdm_crosswalk.csv`.** Add rows mapping `int_physical_assets` to `PhysicalAsset`, documenting the staging source for each column.
3. **Update `models/integration/_models.yml`.** Add `meta: cdm_entity: PhysicalAsset` and `meta: cdm_entity_rationale:` referencing this document.
4. **No SQL changes required.** The model's column names, logic, and relationships are final.

---

## 6. Precedent and Governance Note

This exception follows the pattern established by `int_parks` (custom `Park` entity) and `int_financial_transactions` (custom `FinancialTransaction` entity). All three cases arise from the same root cause: the Microsoft CDM was designed for commercial and nonprofit domains, and DCR's operational vocabulary — state park infrastructure, government GL accounting, physical asset management — falls outside those domains.

The `PhysicalAsset` entity is the third custom extension in the DCR CDM catalog. Future models for natural resources, visitor counts, and law enforcement activity will almost certainly require similar exceptions. The `column_catalog_dcr_extensions.csv` seed serves as the growing registry for all DCR-specific entity definitions.
