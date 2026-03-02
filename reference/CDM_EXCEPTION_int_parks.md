# CDM Entity Exception Request

## Form: Custom Entity Justification for Integration Model

**Model:** `int_parks`
**Date:** 2026-02-27
**Requested by:** Engineering (dbt implementation team)
**Standards impacted:** SQL-INT-03 (Entity Name Word Choice), SQL-INT-05 (CDM Column Conformance)

---

## 1. Business Entity Being Modeled

**Entity name:** Park (a named, bounded unit of public land managed by DCR)
**Grain:** One row per park unit (expected: 50 rows)
**Source systems:** GeoParks (parks_master), VistaReserve (parks)
**Business definition:** A state park is a geographically bounded area of public land with a legal name, physical location, measurable acreage, an operational classification (state park, state reservation, urban park, etc.), and a regional administrative assignment. Parks are the fundamental organizational unit for revenue reporting, visitor tracking, and resource allocation at DCR.

---

## 2. Candidate CDM Entities Evaluated

### 2a. Account (applicationCommon 1.5)

| Criterion | Assessment |
|---|---|
| **Column coverage** | 149 columns. Address fields (`addressCity`, `addressStateOrProvince`, `addressLatitude`, `addressLongitude`), `name`, `description`, and `accountNumber` are usable. |
| **Semantic fit** | Poor. Account represents "an organization or person with which a business unit has a relationship." Its columns assume a CRM context: `creditLimit`, `creditOnHold`, `aging30/60/90`, `numberOfEmployees`, `SIC`, `marketCap`, `tickerSymbol`, `doNotBulkEMail`, `industryCode`, `revenue` (Annual Revenue). A state park is not a customer, vendor, or partner. |
| **Unmappable park attributes** | `total_acres`, `classification`, `region_id` have no semantic equivalent. Mapping `total_acres` to any Account column (e.g., `revenue`, `sharesOutstanding`) would be semantically dishonest. |
| **Verdict** | Rejected. The address fields are convenient, but adopting Account misrepresents what the entity is. 97% of Account's columns (144 of 149) are irrelevant CRM concepts. |

### 2b. FunctionalLocation (Asset 1.0)

| Criterion | Assessment |
|---|---|
| **Column coverage** | 1 column: `functionalLocationId`. This is the case in both the curated seed subset and the full CDM library. |
| **Semantic fit** | Good. "A physical location where assets are installed or maintained" reasonably describes a park. The CDM documentation positions FunctionalLocation as a parent entity for asset hierarchies. |
| **Unmappable park attributes** | All park attributes beyond the ID are unmappable because the entity defines nothing else. |
| **Verdict** | Rejected as-is. Semantically appropriate name, but the entity is a stub. Adopting it requires extending it with every column the model needs, at which point we are defining a custom entity wearing a FunctionalLocation label. |

### 2c. CustomerAsset (Asset 1.0)

| Criterion | Assessment |
|---|---|
| **Column coverage** | 3 columns: `customerassetId`, `msrex_InstallationDate`, `msrex_SerialNumber`. |
| **Semantic fit** | Poor. CustomerAsset represents a product or device associated with a customer (e.g., a piece of installed equipment). Parks are not assets owned by customers. Already used by `int_customer_assets` for bookable inventory (campsites, cabins). |
| **Verdict** | Rejected. Wrong abstraction level and already claimed by another integration model. |

### 2d. Visit (Asset 1.0)

| Criterion | Assessment |
|---|---|
| **Column coverage** | 1 column: `visitId`. |
| **Semantic fit** | Poor. Visit represents a scheduled interaction event, not a location. Already used by `int_reservations`. |
| **Verdict** | Rejected. Represents events at parks, not parks themselves. |

---

## 3. Conclusion: No Standard CDM Entity Is Appropriate

No entity in the curated CDM manifests (applicationCommon, nonProfitCore, Asset, Visits, cdmfoundation) provides both semantic correctness and adequate column coverage for a public-land park entity. The two closest candidates fail on opposite dimensions:

- **Account** has columns but the wrong meaning
- **FunctionalLocation** has the right meaning but no columns

The Microsoft CDM was designed for commercial CRM, healthcare, and financial services. Public-sector land management is not covered by any standard manifest.

---

## 4. Proposed Custom Entity: `Park`

### 4a. Entity Definition

| Property | Value |
|---|---|
| **Entity name** | `Park` |
| **Extends** | `FunctionalLocation` (Asset manifest) — inherits `functionalLocationId` as the base identity pattern |
| **Manifest context** | Custom extension (`dcr/Park.1.0`) within the Asset family |
| **Integration model** | `int_parks` (model retains its current name per SPEC; the CDM entity metadata is recorded in YAML `meta:`) |
| **Description** | A named, bounded unit of public land managed by DCR, identified by a cross-system surrogate key and located by geographic coordinates and administrative address. |

### 4b. Column Definitions

| Column | Data Type | Source | CDM Lineage | Role |
|---|---|---|---|---|
| `parks_sk` | `VARCHAR` | Generated | Surrogate key (SQL-INT-06) | PK |
| `accountnumber` | `VARCHAR` | GeoParks `geo_park_id` / VistaReserve `park_id` | Modeled after `Account.accountNumber` — retained as a cross-system business key identifier | BK |
| `name` | `VARCHAR` | Both sources: `park_name` | Standard CDM attribute (`name` appears in Account, Contact, and many entities as a display name) | Descriptive |
| `description` | `VARCHAR` | GeoParks: `gis_steward` | Standard CDM attribute | Descriptive |
| `address1_city` | `VARCHAR` | GeoParks (future) | Borrowed from `Account.addressCity` address pattern | Location |
| `address1_stateorprovince` | `VARCHAR` | GeoParks (future) | Borrowed from `Account.addressStateOrProvince` | Location |
| `address1_postalcode` | `VARCHAR` | GeoParks (future) | Borrowed from `Account.addressPostalCode` | Location |
| `address1_latitude` | `DECIMAL(10,6)` | GeoParks (future) | Borrowed from `Account.addressLatitude` | Location |
| `address1_longitude` | `DECIMAL(10,6)` | GeoParks (future) | Borrowed from `Account.addressLongitude` | Location |
| `total_acres` | `DECIMAL(10,2)` | GeoParks: `total_acres` | **Custom extension** — no CDM equivalent | Domain-specific |
| `classification` | `VARCHAR` | VistaReserve: `classification` | **Custom extension** — park operational type (state park, state reservation, urban park) | Domain-specific |
| `region_id` | `INTEGER` | VistaReserve: `region_id` | **Custom extension** — DCR administrative region assignment | Domain-specific |
| `source_system` | `VARCHAR` | Generated | Infrastructure column — identifies the winning source system after deduplication | Audit |

### 4c. Normalization and Relationships

The `Park` entity is in **third normal form**: every non-key column depends on the whole key (`parks_sk`) and nothing but the key. No transitive dependencies exist — `region_id` is a raw FK, not a derived value, and region descriptive attributes (name, grouping) live in the downstream `dim_parks` dimension via the `park_region_mappings` seed.

**Relationships to other CDM-mapped integration models:**

```
                          ┌──────────────────┐
                          │   int_parks       │
                          │   (Park)          │
                          │   PK: parks_sk    │
                          └────────┬──────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    │ 1:M          │ 1:M          │ 1:M
                    ▼              ▼              ▼
          ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
          │int_customer │  │int_trans-   │  │int_reser-   │
          │  _assets    │  │  actions    │  │  vations    │
          │(Customer    │  │(Transaction)│  │(Visit)      │
          │  Asset)     │  │             │  │             │
          │FK:          │  │FK:          │  │FK (via      │
          │_parent_     │  │_park_sk     │  │ asset):     │
          │  park_sk    │  │             │  │_park_sk     │
          └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
                 │                │                │
                 │                │                │
                 │         ┌──────┴──────┐        │
                 │         │int_contacts │        │
                 │         │(Contact)    │        │
                 │         │PK:          │        │
                 │         │contacts_sk  │◄───────┘
                 │         └─────────────┘
                 │                ▲
                 │                │
                 └────────────────┘
                  (via Transaction/Visit FK to Contact)
```

**Relationship details:**

| Parent | Child | FK Column | Cardinality | Join Path |
|---|---|---|---|---|
| `int_parks` (Park) | `int_customer_assets` (CustomerAsset) | `_parent_park_sk` | 1 park : M assets | Direct — each bookable asset (campsite, cabin) belongs to one park |
| `int_parks` (Park) | `int_transactions` (Transaction) | `_park_sk` | 1 park : M transactions | Direct — each POS transaction occurs at one park |
| `int_parks` (Park) | `int_reservations` (Visit) | `_park_sk` | 1 park : M reservations | Indirect via `int_customer_assets._parent_park_sk` — each reservation is for an asset, which belongs to a park |
| `int_contacts` (Contact) | `int_transactions` (Transaction) | `_contact_sk` | 1 contact : M transactions | Direct |
| `int_contacts` (Contact) | `int_reservations` (Visit) | `_contact_sk` | 1 contact : M reservations | Direct |
| `int_customer_assets` (CustomerAsset) | `int_reservations` (Visit) | `_asset_sk` | 1 asset : M reservations | Direct |

The `Park` entity serves as the **top-level organizational node** in the integration layer's entity graph. All financial events (transactions) and operational events (reservations/visits) resolve to a park, either directly or through the asset hierarchy. This is consistent with DCR's reporting structure, where revenue and visitation are always attributed to a specific park unit.

---

## 5. Implementation Path

1. **Add `Park` entity rows to CDM catalog seed.** Create rows in `seeds/cdm_catalogs/column_catalog_asset.csv` (or a new `column_catalog_dcr_extensions.csv`) defining each column above with `cdm_entity_name = 'Park'`. These seeds serve as reference data for CDM conformance.
2. **Update `seeds/cdm_crosswalk.csv`.** Change `cdm_entity` from `Account` to `Park` for all `int_parks` rows.
3. **Update `models/integration/_models.yml`.** Add `meta: cdm_entity: Park` and `meta: cdm_entity_rationale:` referencing this document.
4. **No SQL changes required.** The model's column names, logic, and relationships are unchanged.
5. **Update `check_model.py` CDM validation.** The checker will now validate `int_parks` columns against the `Park` entity definition, which will pass because we defined the entity to match the model.

---

## 6. Precedent and Governance Note

This is the expected outcome when applying a commercial data model to a public-sector domain. The CDM's coverage of government land management is negligible. This exception request does not bypass SQL-INT-05 — it satisfies it by defining the entity the model conforms to, rather than forcing conformance to an inappropriate entity. The custom entity is documented, its columns are cataloged in the same seed infrastructure as standard CDM entities, and its conformance is validated against those seeds.

Future vertical slices (Infrastructure/Assets, Natural Resources) will likely require similar extensions for entities like `Trail`, `WaterBody`, or `WildlifeHabitat`. This form should serve as the template for those requests.
