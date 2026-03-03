# CDM Entity Exception Request

## Form: Custom Entity Justification for Integration Model

**Model:** `int_employees`
**Date:** 2026-03-03
**Requested by:** Engineering (dbt implementation team)
**Standards impacted:** SQL-INT-03 (Entity Name Word Choice), SQL-INT-05 (CDM Column Conformance)

---

## 1. Business Entity Being Modeled

**Entity name:** Employee (a DCR staff member with an active or historical employment record in PeopleFirst HR)
**Grain:** One row per active employee (records with `is_deleted = true` excluded)
**Source systems:** PeopleFirst HR (DCR-HCM-01, statewide cloud ERP active since 2011)
**Business definition:** An employee is a person employed by DCR under a classified position tracked in the PeopleFirst HR system. This integration model denormalizes three PeopleFirst staging models — employees, positions, and org_units — into a single record per person. The model carries position classification, pay grade, funding source, and organizational unit attributes alongside hashed PII fields (first name, last name, email, phone). Duty station is recorded at the org-unit level only; PeopleFirst does not track park-specific assignments, so no parks_sk foreign key is produced by this model.

A secondary population of seasonal workers exists in `stg_peoplefirst__seasonal_workforce`. Seasonal workers are tracked in a separate PeopleFirst table with a distinct identifier namespace and no position-based classification structure. They are excluded from this model; a separate integration model would be required to represent the seasonal workforce cohort.

---

## 2. Candidate CDM Entities Evaluated

The `identify_candidate_cdm` macro returned a maximum column coverage of 7.1% with no named top candidate entity. All matching columns were coincidental — the CDM catalog contains `employee_id` as a reference attribute on the Contact, Address, and Activity entities, not as a primary entity field. The full evaluation:

### 2a. Contact (applicationCommon / nonProfitCore) — Top CDM candidate at 7.1%

| Criterion | Assessment |
|---|---|
| **Column coverage** | 1 of ~14 evaluated business columns matched: `employee_id` appears as a reference attribute on Contact (a field to record the contact's employer-assigned ID, not an employee record). |
| **Semantic fit** | None. Contact models an external organization's customer or donor relationship. An HR employee record — with position classification, pay grade, org unit, and government benefits eligibility — is not a Contact. |
| **Verdict** | Rejected. The `employee_id` coincidence caused a spurious match. The CDM Contact entity has no HR semantics. |

### 2b. Worker / Employee (CDM HCM module)

Not present in the curated CDM catalog manifests deployed in this project (applicationCommon, nonProfitCore, Asset, Visits, cdmfoundation). The CDM does define a Worker entity in its Human Capital Management module, but the DCR catalog does not include the HCM manifest. The Worker entity's conceptual structure (hire date, position, org hierarchy, compensation grade) would align with this model; however, because the HCM manifest is not available, no formal column coverage analysis is possible.

### 2c. Activity (applicationCommon)

| Criterion | Assessment |
|---|---|
| **Column coverage** | 1 match: `employee_id` reference field, same as Contact above. |
| **Semantic fit** | None. Activity models a CRM interaction event. An employment record is not a CRM activity. |
| **Verdict** | Rejected. Coincidental attribute overlap with no semantic connection to HR data. |

---

## 3. Conclusion: No Standard CDM Entity Is Appropriate

The CDM Worker / Employee entity, which would be the natural fit for this model, is not available in the curated catalog manifests for this project. The available manifests (applicationCommon, nonProfitCore, Asset, Visits, cdmfoundation) were designed for commercial CRM, nonprofit fundraising, and asset management — not for government HR and civil service position classification. Specific gaps:

- **No position classification entity**: The CDM has no construct for government job classification codes (GR-15, GR-23), pay grades, or civil service position hierarchies.
- **No org-unit-as-duty-station pattern**: DCR employees are assigned at the org-unit level, not the park level. CDM org hierarchy concepts (business unit, team) do not model the spatial-administrative relationship of org_unit → region.
- **No government benefits entity**: Health plan type, retirement tier, leave balance tracking at the agency level has no CDM analog in the available manifests.
- **PII hash preservation**: The PeopleFirst system returns hashed PII (MD5) rather than clear-text identity fields. A CDM Contact entity would expect clear-text name and email fields.

---

## 4. Proposed Custom Entity: `Employee`

### 4a. Entity Definition

| Property | Value |
|---|---|
| **Entity name** | `Employee` |
| **Extends** | None — stand-alone HR entity with no useful CDM parent in current manifests |
| **Manifest context** | Custom extension (`dcr/Employee.1.0`) within a proposed HumanCapital family |
| **Integration model** | `int_employees` |
| **Description** | A DCR staff member with an active classified position in PeopleFirst HR. Denormalized from employees, positions, and org_units. PII fields are carried as MD5 hashes (Confidential — PeopleFirst is a Confidential-rated system). Duty station is at org-unit level only; no park-specific assignment is available. Seasonal workers are excluded. |

### 4b. Column Definitions

| Column | Data Type | Source | CDM Lineage | Role |
|---|---|---|---|---|
| `employees_sk` | `VARCHAR` | Generated | Surrogate key (SQL-INT-06), generated from employee_id | PK |
| `employee_id` | `VARCHAR` | PeopleFirst `employees.employee_id` | No CDM analog — government HR employee number | BK |
| `first_name_hash` | `VARCHAR` | PeopleFirst `employees.first_name` (MD5) | PII hash — no CDM equivalent | PII-Hash |
| `last_name_hash` | `VARCHAR` | PeopleFirst `employees.last_name` (MD5) | PII hash — no CDM equivalent | PII-Hash |
| `email_hash` | `VARCHAR` | PeopleFirst `employees.email` (MD5) | PII hash — no CDM equivalent | PII-Hash |
| `phone_hash` | `VARCHAR` | PeopleFirst `employees.phone` (MD5) | PII hash — no CDM equivalent | PII-Hash |
| `hire_date` | `DATE` | PeopleFirst `employees.hire_date` | **Custom extension** — government civil service hire date | Event |
| `separation_date` | `DATE` | PeopleFirst `employees.separation_date` | **Custom extension** — null for currently active employees | Event |
| `position_id` | `VARCHAR` | PeopleFirst `positions.position_id` | No CDM analog — government position identifier | FK |
| `job_classification` | `VARCHAR` | PeopleFirst `positions.job_classification` | **Custom extension** — civil service job class (e.g., Maintenance Worker I) | Classification |
| `pay_grade` | `VARCHAR` | PeopleFirst `positions.pay_grade` | **Custom extension** — government pay grade (e.g., GR-15) | Classification |
| `funding_source` | `VARCHAR` | PeopleFirst `positions.funding_source` | **Custom extension** — position funding type (General Fund, Grant, etc.) | Financial |
| `position_is_active` | `BOOLEAN` | PeopleFirst `positions.is_active` | **Custom extension** — whether the position is currently budgeted and open | Status |
| `org_unit_id` | `VARCHAR` | PeopleFirst `org_units.org_unit_id` | No CDM analog — government org unit code (e.g., R2-RECR) | FK |
| `org_unit_name` | `VARCHAR` | PeopleFirst `org_units.org_unit_name` | **Custom extension** — human-readable org unit name | Descriptive |
| `region_id` | `INTEGER` | PeopleFirst `org_units.region_id` | **Custom extension** — DCR administrative region (1–4); duty station at region level only | Geography |
| `source_system` | `VARCHAR` | Generated | **Custom extension** — DCR-HCM-01 | Audit |

### 4c. Scope Notes

**Seasonal workers excluded.** PeopleFirst tracks seasonal workers in a separate `seasonal_workforce` table with a distinct identifier namespace (`seasonal_emp_id`), no position_id foreign key, and no pay-grade classification. This table requires its own integration model to represent correctly. Merging the two populations into one model would require a discriminator union pattern and would obscure the fundamental difference in employment type.

**PII sensitivity.** PeopleFirst is classified as Confidential (SSN, salary, medical leave). The staging model applies MD5 hashing to name, email, and phone fields. Clear-text PII is not present in this integration model; however, the model is still Confidential-classified because hashed fields combined with other attributes can support re-identification.

**No parks_sk foreign key.** Per the PeopleFirst Data Inventory entry: "Duty station at org-unit level only (not park-specific)." An org unit may correspond to an administrative region (region_id = 1–4) or a functional domain (HQ-EXEC, HQ-FIN). There is no one-to-one mapping between an org unit and a park. Downstream marts that require an employee-to-park linkage must use region_id → int_parks.region_id as a 1:M relationship, not a point FK.

**Relationship to other integration models:**

| Parent | Child | FK Column | Cardinality | Notes |
|---|---|---|---|---|
| None | `int_employees` (Employee) | — | — | No parks_sk — duty station is at org-unit/region level only |

---

## 5. Implementation Path

1. **Add `Employee` rows to CDM extension catalog.** Create rows in `seeds/cdm_catalogs/column_catalog_dcr_extensions.csv` defining each column above with `cdm_entity_name = 'Employee'`.
2. **Update `seeds/cdm_crosswalk.csv`.** Add rows mapping `int_employees` to `Employee`, documenting the staging source for each column.
3. **Update `models/integration/_models.yml`.** Add `meta: cdm_entity: Employee` and `meta: cdm_entity_rationale:` referencing this document.
4. **No SQL changes required.** The model's column names, logic, and relationships are final.

---

## 6. Precedent and Governance Note

This exception follows the pattern established by `int_parks` (Park), `int_financial_transactions` (FinancialTransaction), `int_physical_assets` (PhysicalAsset), `int_ecological_surveys` (EcologicalSurvey), and `int_visitor_counts` (VisitorCount). The `Employee` entity is the sixth custom extension in the DCR CDM catalog.

The CDM HCM Worker entity would be the appropriate standard mapping; however, the HCM manifest is not included in the curated catalog deployed for this project. If the HCM manifest is added in a future catalog refresh, this exception should be revisited and the `Employee` entity evaluated for conformance with CDM Worker column definitions.
