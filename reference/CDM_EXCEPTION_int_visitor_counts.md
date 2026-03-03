# CDM Entity Exception Request

## Form: Custom Entity Justification for Integration Model

**Model:** `int_visitor_counts`
**Date:** 2026-03-03
**Requested by:** Engineering (dbt implementation team)
**Standards impacted:** SQL-INT-03 (Entity Name Word Choice), SQL-INT-05 (CDM Column Conformance)

---

## 1. Business Entity Being Modeled

**Entity name:** VisitorCount (a daily estimated visitor volume at one IoT sensor location within a DCR park)
**Grain:** One row per sensor per day
**Source systems:** TrafficCount_IoT (DCR-VUM-01, pilot IoT sensor network active since 2024)
**Business definition:** A visitor count is a daily aggregated estimate of person-visits at a specific sensor installation within a DCR park entrance or trailhead. The estimate is produced by the TrafficCount vendor system by applying a vehicle occupancy multiplier (2.7, from a 2019 study) to raw vehicle magnetometer readings and adding direct pedestrian/cyclist infrared counts. The occupancy multiplier is preserved per record because it has not been revalidated and downstream models may need to apply sensitivity analysis with alternative multiplier values.

The TrafficCount pilot covers 20 sensors at 8 park entrances and 12 trailheads — approximately 15% of DCR's park access points. The remaining 85% of parks have no IoT sensor coverage and visitor volume for those parks is estimated only from VistaReserve reservation data.

---

## 2. Candidate CDM Entities Evaluated

The `identify_candidate_cdm` macro returned no column matches for `int_visitor_counts`. The business columns evaluated (`target_date`, `estimated_total_visitors`, `vehicle_multiplier_used`, `calculation_timestamp`, `sensor_type`, `location_description`) produced zero matches across all CDM catalog manifests.

### 2a. No candidate entities found

The CDM catalogs (applicationCommon, nonProfitCore, Asset, Visits, cdmfoundation) contain no entity for:
- IoT sensor-based visitor counting
- Vehicle occupancy multiplier methodology
- Trailhead or entrance gate measurement
- Park attendance estimation via proxy counting

### 2b. Closest evaluated alternatives

**Visit (CDM Visits manifest):** The `int_visits` model already uses this entity for VistaReserve reservation lifecycle events. A CDM Visit represents a customer's intentional reservation transaction — it is not a passive IoT sensor reading. Applying Visit to an automated vehicle count would conflate two incompatible attendance measurement paradigms. The VistaReserve-based Visit entity counts confirmed reservations; the TrafficCount entity estimates total park attendance including day visitors without reservations.

**Appointment (nonProfitCore):** Appointment models scheduled organizational interactions. An IoT vehicle count at a park entrance is not an appointment.

---

## 3. Conclusion: No Standard CDM Entity Is Appropriate

The CDM has no entity for IoT-based passive visitor counting. The core attributes of `int_visitor_counts` — an occupancy multiplier, a sensor installation type, a daily aggregation grain, and a vendor-calculated estimate — have no CDM equivalents.

A secondary consideration: the TrafficCount pilot covers only 15% of DCR parks. Any downstream mart model consuming `int_visitor_counts` must explicitly account for the coverage gap; the parks_sk FK enables this filter but the entity design does not resolve the representativeness limitation.

---

## 4. Proposed Custom Entity: `VisitorCount`

### 4a. Entity Definition

| Property | Value |
|---|---|
| **Entity name** | `VisitorCount` |
| **Extends** | None — stand-alone IoT measurement entity |
| **Manifest context** | Custom extension (`dcr/VisitorCount.1.0`) within a proposed Attendance family |
| **Integration model** | `int_visitor_counts` |
| **Description** | A daily estimated visitor volume at one IoT sensor installation within a DCR park entrance or trailhead. Derived from vehicle magnetometer and pedestrian/cyclist infrared counts by the TrafficCount vendor system. The vehicle occupancy multiplier is preserved per record to support sensitivity analysis. Only active, non-deleted records from the 2024 pilot are included. |

### 4b. Column Definitions

| Column | Data Type | Source | CDM Lineage | Role |
|---|---|---|---|---|
| `visitor_counts_sk` | `VARCHAR` | Generated | Surrogate key (SQL-INT-06), generated from metric_id | PK |
| `metric_id` | `VARCHAR` | TrafficCount `derived_visitor_metrics.metric_id` | No CDM analog — vendor-assigned daily estimate ID | BK |
| `sensor_id` | `VARCHAR` | TrafficCount `derived_visitor_metrics.sensor_id` | No CDM analog — IoT sensor identifier | FK |
| `parks_sk` | `VARCHAR` | Generated via int_parks | FK to Park custom entity | FK |
| `target_date` | `DATE` | TrafficCount `derived_visitor_metrics.target_date` | **Custom extension** — calendar date of estimate | Event |
| `estimated_total_visitors` | `INTEGER` | TrafficCount `derived_visitor_metrics.estimated_total_visitors` | **Custom extension** — daily person-visit estimate | Measure |
| `vehicle_multiplier_used` | `NUMERIC` | TrafficCount `derived_visitor_metrics.vehicle_multiplier_used` | **Custom extension** — occupancy multiplier (standardly 2.7) | Methodology |
| `calculation_timestamp` | `TIMESTAMP` | TrafficCount `derived_visitor_metrics.calculation_timestamp` | **Custom extension** — vendor calculation time for audit | Audit |
| `sensor_type` | `VARCHAR` | TrafficCount `sensor_locations.sensor_type` | **Custom extension** — IoT technology type | Classification |
| `location_description` | `VARCHAR` | TrafficCount `sensor_locations.location_description` | **Custom extension** — human-readable installation location | Descriptive |

### 4c. Coverage and Limitations

**Pilot coverage only.** This model contains data for 20 sensors at 15% of DCR parks. Downstream marts consuming `int_visitor_counts` should join to `int_parks` to filter or annotate coverage gaps — the `parks_sk` FK supports this. A park with no sensor records in `int_visitor_counts` has no TrafficCount coverage, not zero visitors.

**Deleted records excluded.** The TrafficCount vendor system soft-deletes records when sensor calibration errors are detected. Records with `is_deleted = true` are excluded from this integration model. The row count will therefore be less than the raw `derived_visitor_metrics` staging model row count.

**Multiplier revalidation.** The vehicle occupancy multiplier (2.7) was set in 2019 and has not been revalidated. It is preserved in `vehicle_multiplier_used` so that sensitivity analyses can be run downstream without modifying the integration model.

**Relationship to other integration models:**

| Parent | Child | FK Column | Cardinality | Notes |
|---|---|---|---|---|
| `int_parks` (Park) | `int_visitor_counts` (VisitorCount) | `parks_sk` | 1 park : M daily estimates | Resolved via sensor_locations.park_id (varchar) cast to int → infratrak_park_id |

---

## 5. Implementation Path

1. **Add `VisitorCount` rows to CDM extension catalog.** Create rows in `seeds/cdm_catalogs/column_catalog_dcr_extensions.csv` defining each column above with `cdm_entity_name = 'VisitorCount'`.
2. **Update `seeds/cdm_crosswalk.csv`.** Add rows mapping `int_visitor_counts` to `VisitorCount`, documenting the staging source for each column.
3. **Update `models/integration/_models.yml`.** Add `meta: cdm_entity: VisitorCount` and `meta: cdm_entity_rationale:` referencing this document.
4. **No SQL changes required.** The model's column names, logic, and relationships are final.

---

## 6. Precedent and Governance Note

This exception follows the pattern established by `int_parks` (Park), `int_financial_transactions` (FinancialTransaction), `int_physical_assets` (PhysicalAsset), and `int_ecological_surveys` (EcologicalSurvey). The `VisitorCount` entity is the fifth custom extension in the DCR CDM catalog.

The TrafficCount pilot data represents a particularly novel case: unlike the other four exceptions, which cover established government operational domains, `int_visitor_counts` covers an emerging IoT measurement methodology that has no precedent in either the commercial CDM or in DCR's historical data systems.
