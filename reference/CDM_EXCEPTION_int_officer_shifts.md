# CDM Entity Exception Request

## Form: Custom Entity Justification for Integration Model

**Model:** `int_officer_shifts`
**Date:** 2026-03-03
**Requested by:** Engineering (dbt implementation team)
**Standards impacted:** SQL-INT-03 (Entity Name Word Choice), SQL-INT-05 (CDM Column Conformance)

---

## 1. Business Entity Being Modeled

**Entity name:** OfficerShift (a patrol shift record for a DCR law enforcement officer, including operational metrics logged during that shift)
**Grain:** One row per officer per shift (activity_id from RangerShield officer_activity)
**Source systems:** RangerShield CAD/RMS (DCR-LES-01, on-premise air-gapped system active since 2014 RMS / 2017 CAD)
**Business definition:** An officer activity record captures the operational metrics logged by a single DCR law enforcement ranger during one assigned patrol shift. The record includes the shift window (start and end timestamp), patrol distance (miles), visitor contacts made, and natural resource checks performed. Officer rank and certification status are denormalized from the officer roster to support downstream staffing analysis. RangerShield is air-gapped from all other DCR systems; this model does not join to int_parks or any non-RangerShield integration model, per CJIS governance requirements for law enforcement data isolation.

---

## 2. Candidate CDM Entities Evaluated

The `identify_candidate_cdm` macro returned a maximum column coverage of 7.1% with no named top candidate entity. The evaluation:

### 2a. Activity (applicationCommon) — Top CDM candidate at 7.1%

| Criterion | Assessment |
|---|---|
| **Column coverage** | 1 of ~11 evaluated business columns matched: a generic activity timestamp field. No LE-specific columns (badge_number, patrol_miles, visitor_contacts, resource_checks, certification_status) have CDM equivalents. |
| **Semantic fit** | None. CDM Activity models CRM interaction events (phone calls, emails, appointments). A law enforcement patrol shift with physical patrol metrics is not a CRM activity. |
| **Verdict** | Rejected. Timestamp overlap is coincidental; no semantic connection to patrol operations. |

### 2b. Visit (CDM Visits manifest)

| Criterion | Assessment |
|---|---|
| **Column coverage** | No column matches. |
| **Semantic fit** | None. Visit models a customer's reservation or attendance event. A ranger shift is not a park visitor event. |
| **Verdict** | Rejected. Zero coverage and zero semantic fit. |

### 2c. Appointment (nonProfitCore)

| Criterion | Assessment |
|---|---|
| **Column coverage** | No column matches. |
| **Semantic fit** | None. Appointment models a scheduled organizational interaction. A patrol shift log is not an appointment in any CRM or nonprofit fundraising sense. |
| **Verdict** | Rejected. Zero coverage. |

### 2d. Law Enforcement / Public Safety CDM Modules

Not present in the curated CDM catalog manifests deployed in this project. The CDM does not include a public safety or law enforcement module in the commercial CRM manifests. No entity in the available catalogs covers officer rosters, patrol logs, incident reporting, use-of-force documentation, or dispatch operations.

---

## 3. Conclusion: No Standard CDM Entity Is Appropriate

The CDM was designed for commercial CRM, healthcare, and nonprofit domains. Law enforcement records management — patrol shift metrics, officer certification tracking, badge-number-based personnel rosters — has no CDM analog in any of the available manifests (applicationCommon, nonProfitCore, Asset, Visits, cdmfoundation). Specific gaps:

- **No officer entity**: The CDM has no construct for a sworn law enforcement officer with rank, badge number, and certification status.
- **No patrol shift entity**: Shift start/end timestamps, patrol miles, visitor contacts, and resource checks have no CDM equivalent. These are public safety operational metrics with no commercial CRM analog.
- **No LE data isolation pattern**: The CDM does not define any entity-level constraint for CJIS air-gap compliance. The governance requirement to isolate LE data from non-LE integration models is a DCR operational constraint that has no CDM equivalent.
- **Incident and citation data excluded at this layer**: RangerShield also contains `incidents`, `citations`, `dispatch_logs`, and `use_of_force` tables. These are separate entities with their own governance requirements and are out of scope for this model. The `int_officer_shifts` model covers the shift-level operational log only.

---

## 4. Proposed Custom Entity: `OfficerShift`

### 4a. Entity Definition

| Property | Value |
|---|---|
| **Entity name** | `OfficerShift` |
| **Extends** | None — stand-alone law enforcement operational entity |
| **Manifest context** | Custom extension (`dcr/OfficerShift.1.0`) within a proposed LawEnforcement family (air-gapped, Restricted — Statutory) |
| **Integration model** | `int_officer_shifts` |
| **Description** | A patrol shift record for a single DCR law enforcement officer. Includes shift window, patrol distance, visitor contact count, and natural resource checks. Officer rank and certification status are denormalized from the RangerShield officer roster. This model is isolated from all non-RangerShield integration models per CJIS governance requirements; no parks_sk foreign key is produced at this layer. |

### 4b. Column Definitions

| Column | Data Type | Source | CDM Lineage | Role |
|---|---|---|---|---|
| `officer_shifts_sk` | `VARCHAR` | Generated | Surrogate key (SQL-INT-06), generated from activity_id | PK |
| `activity_id` | `VARCHAR` | RangerShield `officer_activity.activity_id` | No CDM analog — RangerShield activity identifier | BK |
| `badge_number` | `VARCHAR` | RangerShield `officer_activity.badge_number` | No CDM analog — law enforcement badge identifier | FK |
| `shift_date` | `DATE` | RangerShield `officer_activity.shift_date` | **Custom extension** — calendar date of the patrol shift | Event |
| `shift_start_time` | `TIMESTAMP` | RangerShield `officer_activity.shift_start_time` | **Custom extension** — shift start timestamp | Event |
| `shift_end_time` | `TIMESTAMP` | RangerShield `officer_activity.shift_end_time` | **Custom extension** — shift end timestamp | Event |
| `patrol_miles` | `DECIMAL(5,1)` | RangerShield `officer_activity.patrol_miles` | **Custom extension** — distance patrolled in statute miles | Operational |
| `visitor_contacts` | `INTEGER` | RangerShield `officer_activity.visitor_contacts` | **Custom extension** — count of documented visitor interactions | Operational |
| `resource_checks` | `INTEGER` | RangerShield `officer_activity.resource_checks` | **Custom extension** — count of natural resource condition checks | Operational |
| `rank` | `VARCHAR` | RangerShield `officers.rank` | **Custom extension** — officer rank (Ranger, Corporal, Sergeant, Lieutenant, Captain) | Classification |
| `certification_status` | `VARCHAR` | RangerShield `officers.certification_status` | **Custom extension** — CJIS/POST certification status (Active, Suspended, Expired) | Classification |
| `assigned_region` | `INTEGER` | RangerShield `officers.assigned_region` | **Custom extension** — DCR administrative region (1–4) for duty assignment | Geography |
| `source_system` | `VARCHAR` | Generated | **Custom extension** — DCR-LES-01 | Audit |

### 4c. Scope Notes

**LE data isolation.** RangerShield (DCR-LES-01) is an on-premise, air-gapped system subject to CJIS security requirements. Per the expansion plan (Task 2.5): "Isolate LE data to its own compliant integration point — do not join LE data with non-LE sources at this layer." This model does not join to `int_parks`, `int_employees`, or any other non-RangerShield model. `assigned_region` is an integer (1–4) but is not used as a FK to int_parks.region_id at this layer.

**Excluded RangerShield tables.** RangerShield also contains `incidents`, `citations`, `dispatch_logs`, and `use_of_force` records. These represent distinct entities — incident reports are CJIS-controlled public safety records, citations are legal enforcement actions, use-of-force reports have their own review workflow. Each would require a separate integration model with its own CDM exception. They are out of scope for this initial implementation.

**Location as narrative text.** Incident and dispatch records contain location as free-text narrative (`location_narrative`, `radio_traffic_transcript`). Officer activity records do not carry location at all — patrol coverage is implied by `assigned_region`. No coordinate data is available from RangerShield at the shift level.

**Relationship to other integration models:**

| Parent | Child | FK Column | Cardinality | Notes |
|---|---|---|---|---|
| None | `int_officer_shifts` (OfficerShift) | — | — | No cross-domain FKs — LE isolation requirement |

---

## 5. Implementation Path

1. **Add `OfficerShift` rows to CDM extension catalog.** Create rows in `seeds/cdm_catalogs/column_catalog_dcr_extensions.csv` defining each column above with `cdm_entity_name = 'OfficerShift'`.
2. **Update `seeds/cdm_crosswalk.csv`.** Add rows mapping `int_officer_shifts` to `OfficerShift`, documenting the staging source for each column.
3. **Update `models/integration/_models.yml`.** Add `meta: cdm_entity: OfficerShift` and `meta: cdm_entity_rationale:` referencing this document.
4. **No SQL changes required.** The model's column names, logic, and relationships are final.

---

## 6. Precedent and Governance Note

This exception follows the pattern established by `int_parks` (Park), `int_financial_transactions` (FinancialTransaction), `int_physical_assets` (PhysicalAsset), `int_ecological_surveys` (EcologicalSurvey), `int_visitor_counts` (VisitorCount), and `int_employees` (Employee). The `OfficerShift` entity is the seventh custom extension in the DCR CDM catalog.

The law enforcement domain represents a particularly constrained case: unlike the other six exceptions, which arise from the CDM's commercial domain boundaries, `int_officer_shifts` carries an additional governance constraint — CJIS air-gap compliance — that prohibits cross-domain joins at the integration layer. The CDM exception document and the SQL model's isolation comment both record this constraint for future developers.
