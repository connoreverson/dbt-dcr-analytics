# DCR Business Glossary

**Document Classification:** Internal — Data Governance
**Version:** 1.0
**Date:** 2026-02-20
**Companion To:** DCR Data Inventory (Version 2.0)
**Maintained By:** Office of Strategic Technology, DCR Central Administration

---

## Purpose

This glossary defines the canonical business terms used across the Department of Conservation and Recreation. It answers the question the Data Inventory deferred: *What do our business terms mean, and how are they measured?*

It is designed for three audiences: a new analyst joining the dbt project who needs to understand the business domain before writing models; a data steward who needs to know which system is authoritative for a given concept; and a business stakeholder who needs plain-language definitions that resolve (or at least acknowledge) the ambiguity that arises when multiple systems define the same concept differently.

Where a term is well-understood and uncontested, the definition is brief. Where systems disagree about what a term means or how it's measured, the full treatment is provided — including the disagreement itself, because that disagreement is information the dbt project needs.

---

## Core Entity Terms

### Park / Park Unit

**Definition:** A discrete, state-managed land unit administered by DCR. The agency manages 50 park units classified into five types: State Parks, State Recreation Areas, State Natural Reserves, State Historic Parks, and State Beaches. Together these span approximately 285,000 acres across four administrative regions.

**Source of Truth:** GeoParks Enterprise (DCR-GEO-01). GeoParks maintains the authoritative `parks_master` registry with surveyed legal boundaries for all 50 units. Its feature ID scheme has been stable since the 2008 platform migration and predates the identifiers used by all other systems.

**Also Found In:** VistaReserve (DCR-REV-01) maintains its own `parks` table covering all 50 units with operational attributes (kiosk status, booking configuration). InfraTrak (DCR-AST-01) maintains a `parks` table for all 50 units but has asset and work order data only for the 28 parks in Regions 1 and 2. BioSurvey (DCR-NRM-01) references parks through `survey_sites.park_id`. TrafficCount (DCR-VUM-01) covers 8–12 parks. LegacyRes (DCR-REV-02) used a retired identifier scheme with only 15 parks crosswalked to current IDs.

**Known Discrepancies:** Six systems maintain independent park references with different identifiers and different coverage. VistaReserve and InfraTrak share an INTEGER `park_id` scheme. GeoParks uses a VARCHAR `geo_park_id` with no enforced foreign key to the INTEGER scheme. The crosswalk tables linking these identifiers have not been maintained since 2022. Resolving which system's park identifier is the "golden key" — and how to reconcile the GeoParks VARCHAR IDs to the INTEGER scheme — is a prerequisite for building the dbt `int_parks` integration model.

**CDM Alignment Notes:** Microsoft CDM includes a `Facility` entity in the non-profit and government accelerators. A park unit maps most naturally to `Facility` or a custom extension of it, with park type as a classification attribute.

**Status:** Defined

---

### Asset

**Definition:** A physical piece of infrastructure or bookable inventory owned, maintained, or managed by DCR. The term encompasses buildings, trails, roads, bridges, dams, water and wastewater systems, electrical infrastructure, campsites, cabins, lodge rooms, marina slips, picnic shelters, day-use areas, and other facilities with a geographic footprint.

**Source of Truth:** No single system is authoritative for all assets. InfraTrak Lifecycle (DCR-AST-01) is the designated source for physical infrastructure assets — but only in Regions 1 and 2 (28 of 50 parks). VistaReserve (DCR-REV-01) is authoritative for bookable recreational inventory across all 50 parks. GeoParks Enterprise (DCR-GEO-01) provides the spatial representation of everything with a geographic footprint.

**Also Found In:** All three systems above, with overlapping but non-identical populations.

**Known Discrepancies:** The three asset populations overlap but don't align. InfraTrak tracks physical infrastructure (buildings, trails, bridges, dams) but only in Regions 1–2. VistaReserve tracks bookable inventory (campsites, cabins, shelters) across all 50 parks. GeoParks represents everything with a spatial footprint. A campsite in Region 1 appears in all three systems with three different identifiers; a campsite in Region 3 appears in VistaReserve and GeoParks but not InfraTrak; a utility corridor appears in GeoParks and possibly InfraTrak but not VistaReserve. The `asset_crosswalk` table linking identifiers across the three systems is stale (unmaintained since 2022) and incomplete for assets added or reclassified after that date.

**CDM Alignment Notes:** CDM includes `Asset` and `Facility Equipment` entities. The distinction between a bookable asset (VistaReserve) and a maintainable asset (InfraTrak) may require two CDM entity mappings or a unified `Asset` entity with a type discriminator.

**Status:** Contested — the agency has not formally defined whether "asset" is a single concept or three related concepts.

---

### Employee / Staff / Worker / Officer

**Definition:** A person who performs work for DCR. This umbrella term covers several distinct populations that are tracked in different systems with no cross-system person linkage:

- **Permanent employees** (~420 FTE): Tracked in PeopleFirst HR (DCR-HCM-01) with `employee_id`. Includes all permanent classified and exempt positions.
- **Seasonal workers** (~600 annually): Also tracked in PeopleFirst with `seasonal_emp_id`. Temporary appointments from approximately April through October, subject to different benefits eligibility.
- **Maintenance staff**: Referenced in InfraTrak (DCR-AST-01) work orders by `employee_id`, presumably the same namespace as PeopleFirst — but no foreign key enforces this.
- **State Park Peace Officers (SPPOs)**: Tracked in RangerShield (DCR-LES-01) by `badge_number`. SPPOs are also PeopleFirst employees, but the RangerShield badge number has no crosswalk to PeopleFirst `employee_id` due to the CJIS air-gap.

**Source of Truth:** PeopleFirst (DCR-HCM-01) for permanent employees and seasonal workers (position, classification, pay, benefits). RangerShield (DCR-LES-01) for sworn officer duty records, dispatch, and law enforcement activity — but this data cannot be joined to PeopleFirst at the person level.

**Known Discrepancies:** The air-gap between RangerShield and all other systems is a permanent architectural constraint mandated by CJIS policy. Building a unified "all DCR workers" integration model that includes officers is not feasible. The dbt project will likely need separate integration models: one for civilian employees (PeopleFirst + InfraTrak staff references) and one for law enforcement (RangerShield, standalone).

**CDM Alignment Notes:** CDM `Worker` entity for PeopleFirst employees. No CDM entity naturally represents the air-gapped officer population — these should be modeled as a separate entity.

**Status:** Draft — the agency has not formally resolved whether "employee" encompasses all worker populations.

---

### Customer / Guest / Visitor

**Definition:** A person who uses DCR park facilities or services. The term fragments across systems depending on how the person interacts with the agency:

- **Customer** (VistaReserve): A person with an account in the reservation system. Has a `customer_id`, profile data (name, email, residency, pass status), and transaction history. The customer profile table has an estimated 18–22% duplicate rate from self-service account creation.
- **Guest** (LegacyRes): A historical reservation holder from the 2005–2021 era, identified by `legacy_cust_id`. Identifiers are incompatible with current VistaReserve customer IDs. A partial crosswalk exists for 15 parks only.
- **Visitor** (TrafficCount): An anonymous person counted by a sensor. No identity data — only aggregate counts extrapolated from vehicle occupancy.
- **Subject** (RangerShield): A person referenced in a law enforcement incident report. Separate identity namespace, air-gapped.

**Source of Truth:** VistaReserve (DCR-REV-01) for current customers with accounts. LegacyRes (DCR-REV-02) for historical guests pre-March 2021. TrafficCount (DCR-VUM-01) for anonymous aggregate visitor counts.

**Known Discrepancies:** These are fundamentally different populations with different levels of identity resolution. A "customer" is a known individual with PII; a "visitor" is an anonymous count derived from sensor data and a vehicle occupancy multiplier. The 18 million annual visitors figure cannot be produced from VistaReserve data alone — it is a composite estimate combining reservation counts, fee receipts, sensor data, and professional judgment.

**CDM Alignment Notes:** CDM `Contact` entity for VistaReserve customers. Anonymous visitor counts do not map to a CDM person entity — they are facts, not entities.

**Status:** Defined — these are intentionally separate concepts, not a single concept in disagreement.

---

### Species

**Definition:** A biological organism identified using BioSurvey's custom alphanumeric coding scheme, developed in 1993. The scheme is the sole authoritative species reference in the agency and is maintained by the Chief Biologist.

**Source of Truth:** BioSurvey_Legacy (DCR-NRM-01), specifically the `species_codes` reference table. The table includes a comma-separated `alternate_names` field maintained for field staff convenience.

**Also Found In:** Nowhere else. No other DCR system tracks species data.

**CDM Alignment Notes:** No obvious CDM entity mapping. Species data is domain-specific to ecological monitoring and would likely require a custom entity.

**Status:** Defined

---

## Financial Terms

### Revenue

**Definition:** Income received by DCR from the operation of its park units. Revenue sources include camping and lodging fees, day-use entry fees, equipment rentals, retail sales (firewood, ice, merchandise), annual recreation passport sales, gift pass activations, marina slip fees, and concessionaire franchise fees.

**Source of Truth:** It depends on the purpose. VistaReserve (DCR-REV-01) is authoritative for operational revenue management — it records point-of-sale transactions at the daily level with park, category, and transaction-type granularity. StateGov Financials (DCR-FIN-01) is authoritative for statutory audit compliance — it is the legally mandated financial record, but it aggregates daily revenue into monthly fiscal periods, losing daily-level detail.

**Also Found In:** Both systems above; also, revenue from 12 unstaffed kiosks is initially captured on paper logs before manual entry into VistaReserve.

**Measurement / Calculation:** VistaReserve: sum of point-of-sale transaction amounts by park and revenue category per day. SGF: sum of general ledger revenue postings by appropriation code per monthly fiscal period. Pass revenue is tracked separately from transactional revenue in VistaReserve for enterprise fund reporting.

**Known Discrepancies:** A 2–5% timing divergence exists between VistaReserve daily totals and SGF monthly aggregations. The divergence is attributed to batch processing timing: VistaReserve transmits daily batches via SFTP; SGF posts them in monthly periods. Additionally, kiosk revenue enters VistaReserve with a 1–2 week lag and may carry transcription errors. The "20-Year Revenue Trend" report was suspended in 2023 because reconciling pre- and post-migration (LegacyRes vs. VistaReserve) revenue data was too labor-intensive.

**CDM Alignment Notes:** CDM `Transaction` or `Payment` entity for individual revenue records. The dual-source pattern (operational vs. statutory) may require separate staging models that converge at the integration layer with a source indicator.

**Status:** Defined

---

### Expenditure

**Definition:** A payment or financial obligation incurred by DCR, recorded in StateGov Financials (SGF) against the agency's chart of accounts. Expenditures are coded by a hierarchical structure: agency, division, program, fund source, and object code.

**Source of Truth:** StateGov Financials (DCR-FIN-01) for all official expenditure records. SGF is the legally mandated financial system.

**Also Found In:** InfraTrak Lifecycle (DCR-AST-01) records maintenance costs at the asset level through work orders — labor hours, material costs, and contractor invoices linked to specific assets. GrantTrack (DCR-FIN-02) tracks grant-level expenditures for reimbursement purposes.

**Measurement / Calculation:** SGF: sum of general ledger expenditure postings by object code per monthly fiscal period. InfraTrak: sum of work order costs by asset.

**Known Discrepancies:** SGF expenditures have no asset-level granularity — a building repair coded to "Object Code 7340 — Building Repair" cannot be attributed to a specific building within SGF. To understand *what* was repaired, analysts must manually join SGF data with InfraTrak work orders using date ranges and dollar amount matching — an error-prone process. Furthermore, InfraTrak only covers Regions 1–2, so asset-level cost attribution is impossible for half the agency's parks. The coding discipline variance across regions (the same repair might be coded differently by different regional managers) further undermines cross-regional financial analysis.

**CDM Alignment Notes:** CDM `Transaction` entity, likely with an expenditure type discriminator. The SGF hierarchical chart of accounts structure may map to CDM `Account` and `Fund` entities.

**Status:** Defined

---

### Grant Award vs. Grant Application

**Definition:** Two distinct stages in the grant lifecycle, both tracked in GrantTrack (DCR-FIN-02):

- **Grant Application:** A pending request for funding, with submission date, reviewing agency, and estimated award timeline. An application that has not yet resulted in an award.
- **Grant Award:** An approved funding commitment from a federal or private source, with defined award amount, performance period, authorized expenditure categories, and match obligations. Federal grants include Land and Water Conservation Fund, FEMA hazard mitigation, and Recreational Trails Program grants; private endowment grants are also tracked.

**Source of Truth:** GrantTrack_Excel_Master (DCR-FIN-02) is the sole source for application status, award terms, compliance deadlines, match obligations, and reimbursement workflows. SGF (DCR-FIN-01) records grant expenditures but not grant lifecycle status.

**Known Discrepancies:** Grant expenditure totals in GrantTrack diverge from SGF by 2–5%, attributed to timing differences (GrantTrack records when a reimbursement is *submitted*; SGF records when the expenditure is *posted*) and to regional coding discipline variance.

**CDM Alignment Notes:** CDM `Grant` or `Award` entity in the non-profit accelerator. The application pipeline and award lifecycle may warrant separate CDM entities or a single entity with a status discriminator.

**Status:** Defined

---

### Deferred Maintenance / Maintenance Backlog

**Definition:** The estimated total cost to restore DCR assets to a "good" condition, defined as a Facility Condition Index (FCI) score of 70 or above. This is not a colloquial term — it has a specific formula: for each asset, deferred maintenance = estimated cost to bring that asset's FCI to ≥ 70. The statewide backlog is the sum of these per-asset estimates.

**Source of Truth:** InfraTrak Lifecycle (DCR-AST-01) calculates deferred maintenance for assets in Regions 1 and 2 only.

**Measurement / Calculation:** Per asset: estimated cost of repairs needed to achieve FCI ≥ 70. Statewide: sum of per-asset estimates across all registered assets. The figure used in legislative budget requests is produced by InfraTrak's built-in reporting module.

**Known Discrepancies:** Because InfraTrak covers only Regions 1 and 2 (28 of 50 parks), the statewide deferred maintenance figure underreports the true backlog by approximately 40%. Assets in Regions 3 and 4 are not assessed in InfraTrak; their maintenance needs are tracked on paper or not tracked at all. Any dbt model that presents a "statewide deferred maintenance backlog" must caveat that it represents only the digitally inventoried portion.

**CDM Alignment Notes:** No direct CDM entity. Deferred maintenance is a derived metric, not a transactional entity. It would likely appear as a calculated field on an `Asset` or `Facility` entity.

**Status:** Defined

---

### Facility Condition Index (FCI)

**Definition:** A standardized 1–100 numeric scale used to assess the physical condition of DCR infrastructure assets. Higher scores indicate better condition. An FCI of 70 or above is considered "good" condition — the threshold used for deferred maintenance calculations.

**Source of Truth:** InfraTrak Lifecycle (DCR-AST-01).

**Measurement / Calculation:** Periodic inspection by trained assessors, scoring each asset against a standardized rubric. Assessment frequency varies by asset criticality: dams and water treatment systems are assessed annually; standard facilities (restrooms, picnic shelters) are on a three-year cycle. The specific scoring methodology is maintained within InfraTrak's assessment module.

**Known Discrepancies:** FCI scores exist only for assets in Regions 1 and 2. No condition assessment data exists in any digital system for Regions 3 and 4.

**CDM Alignment Notes:** FCI would be an attribute on the `Asset` entity rather than a separate entity.

**Status:** Defined

---

### Object Code

**Definition:** The lowest level in SGF's hierarchical accounting classification structure. The full hierarchy is: agency → division → program → fund source → object code. An object code identifies the nature of an expenditure (e.g., "7340 — Building Repair") or revenue (e.g., a specific revenue source code).

**Source of Truth:** StateGov Financials (DCR-FIN-01). The chart of accounts is defined and maintained by the statewide Department of Administration; DCR cannot modify the structure.

**Known Discrepancies:** Different DCR regions use inconsistent practices when selecting object codes for equivalent expenditures. A trail bridge repair may be coded as "Infrastructure — Bridges" in Region 1 and "Building Repair — Other" in Region 3. This coding discipline variance has been documented in two consecutive internal audit findings without resolution. It undermines any cross-regional financial comparison at the object code level.

**CDM Alignment Notes:** CDM `Account` entity. The hierarchical structure maps to a chart of accounts dimension in the dbt mart layer.

**Status:** Defined

---

## Operational Terms

### Visit / Visitation

**Definition:** A single instance of a person or party using a DCR park. This is the most contested term in DCR's data landscape because three systems measure it differently, and the resulting numbers are not reconcilable without understanding the methodology behind each.

**Source of Truth:** There is no single source of truth. Each system measures a different proxy for visitation:

- **VistaReserve (DCR-REV-01):** Counts transactions. One reservation = one visit, regardless of party size. Only captures visitors who make a reservation or purchase — misses walk-in day-use visitors at unstaffed parks.
- **TrafficCount (DCR-VUM-01):** Counts vehicle occupants. Vehicle counts × occupancy multiplier (currently 2.7 persons/vehicle, based on a 2019 survey that has not been re-validated). Deployed at only 8 park entrance stations and 12 trailheads (~15% of parks). Counts include staff, contractors, and delivery vehicles — not just visitors.
- **SGF (DCR-FIN-01):** Counts revenue-generating entries. Day-use fees collected, which only captures visitors who pay — not those at free-entry parks or those who enter when kiosks are unstaffed.

**Measurement / Calculation:** The agency's official "18 million annual visitors" figure is a composite estimate: VistaReserve reservation counts for parks with booking data, TrafficCount sensor data where available, fee receipt counts from SGF for paid day-use, and park manager professional judgment for everything else. The methodology for combining these inputs into a single number is maintained by the Visitor Use Program Coordinator and is documented in the annual "System Visitation Report."

**Known Discrepancies:** The three measurement approaches produce fundamentally different numbers for the same park on the same day. A park with 100 camping reservations (VistaReserve), 500 vehicle entries (TrafficCount × 2.7 = 1,350 estimated visitors), and 200 day-use fee receipts (SGF) has three "visit" counts that cannot be added together. The dbt project must decide whether to model these as three separate metrics or attempt a reconciled composite — and either choice involves documented assumptions.

**CDM Alignment Notes:** No direct CDM entity for an anonymous visit event. If modeled as a fact, it would be a custom `Visitation` fact table with a source discriminator column.

**Status:** Contested

---

### Reservation

**Definition:** A booking made by a customer for use of a DCR recreational asset (campsite, cabin, lodge room, marina slip, picnic shelter, or day-use area). A reservation has a defined lifecycle: search → hold → booking → modification → cancellation → no-show → completion.

**Source of Truth:** VistaReserve (DCR-REV-01) for reservations made after March 2021. LegacyRes_Archive (DCR-REV-02) for reservations from 2005 through February 2021.

**Known Discrepancies:** The March 2021 cutover from LegacyRes to VistaReserve created a hard "data cliff." Historical reservation records were not migrated — they remain in LegacyRes with incompatible identifiers and a different data model. Any longitudinal reservation analysis spanning the boundary requires a manual cross-system join using a partial crosswalk that covers only 15 parks.

**CDM Alignment Notes:** CDM `Booking` or `Reservation` entity in hospitality accelerators.

**Status:** Defined

---

### Occupancy Rate

**Definition:** The proportion of available bookable inventory that is reserved or occupied for a given time period. Used for revenue management and capacity planning.

**Source of Truth:** VistaReserve (DCR-REV-01), where "capacity" = the count of bookable inventory items (campsites, cabins, etc.) with an "available" status for the given date range.

**Measurement / Calculation:** Occupied units ÷ available units for a given park, asset type, and date range. Meaningful at the daily or weekly grain for operational decisions; often aggregated to monthly or seasonal for reporting. "Available" reflects VistaReserve's bookable inventory, not physical carrying capacity — a park may have physical space for more visitors than its bookable inventory represents.

**Known Discrepancies:** Occupancy rate as calculated from VistaReserve only reflects the reservable portion of park capacity. Day-use areas with free entry, overflow camping, and walk-in visitors are not captured. The metric systematically understates true utilization at parks where a large share of visitors do not make reservations.

**CDM Alignment Notes:** Derived metric, not a CDM entity. Would appear as a calculated measure in a mart model.

**Status:** Defined

---

### Work Order

**Definition:** InfraTrak Lifecycle's unit of maintenance activity. A work order documents a single maintenance task performed on a specific asset.

**Source of Truth:** InfraTrak Lifecycle (DCR-AST-01), for Regions 1 and 2 only.

**Measurement / Calculation:** Each work order captures: type (corrective — reactive repair; or preventative — scheduled maintenance), assigned asset, labor hours, material costs, contractor invoices, and lifecycle status (open, in-progress, completed, deferred).

**Known Discrepancies:** Work order completion discipline varies by region. Region 1 has an estimated 90%+ completion rate (maintenance activities that result in a closed work order). Region 2 is estimated at ~70%, attributed to unreliable mobile app connectivity in several canyon parks. Regions 3 and 4 have no digital work orders — maintenance is tracked on paper forms and local spreadsheets. Any dbt analysis of maintenance activity will systematically undercount work performed in Regions 2–4.

**CDM Alignment Notes:** CDM `Work Order` entity in the field service or asset management accelerators.

**Status:** Defined

---

### Incident

**Definition:** RangerShield's unit of law enforcement activity. An incident is a recorded event requiring ranger or peace officer response.

**Source of Truth:** RangerShield CAD/RMS (DCR-LES-01). This is the exclusive source, air-gapped from all other systems.

**Measurement / Calculation:** Incidents are classified using the CJIS Uniform Crime Reporting (UCR) taxonomy. Types include: criminal offenses (theft, assault, drug offenses, DUI, resource damage, trespass), non-criminal incidents (medical aids, lost person reports, search and rescue, drowning responses, wildlife encounters), citations (parking, resource damage, campground rules, traffic), and dispatches (radio communications, officer check-ins, call-for-service assignments).

**Known Discrepancies:** Incident locations are recorded as narrative text descriptions (e.g., "Campsite 47, Loop B, Tall Pines State Park"), not geographic coordinates. These cannot be programmatically joined to GeoParks spatial data without manual geocoding. Summary statistics are compiled manually by LE administrative staff and delivered as static PDFs with a 2–4 week reporting lag. The air-gap is a permanent architectural constraint — any downstream use of incident data must work from sanitized, aggregated extracts.

**CDM Alignment Notes:** No standard CDM entity for law enforcement incidents. Would require a custom entity. The CJIS compliance constraints may require this data to remain in a standalone integration model that does not join to other DCR entities.

**Status:** Defined

---

### Survey / Observation

**Definition:** BioSurvey's unit of ecological monitoring. A single observation record from a structured biological survey or water quality sampling event.

**Source of Truth:** BioSurvey_Legacy (DCR-NRM-01).

**Measurement / Calculation:** Each observation includes: species identification (using the 1993 custom alphanumeric code), observation date, count or density estimate, observer name, and location. The primary data entry form writes all observations — flora surveys, fauna surveys, and water quality readings — to a single `field_observations_raw` table, with an `observation_type` field as the discriminator. Columns specific to one observation type (e.g., pH for water quality, nesting status for fauna) exist on every row but are populated only when relevant.

**Known Discrepancies:** Three water quality protocol eras create comparability challenges for longitudinal analysis: 1993–2005 (original methodology), 2005–2018 (revised methodology), and 2018–present (EPA-aligned protocols). The methodology-aware statistical adjustments needed for cross-era analysis are understood by the Chief Biologist but are not documented in the database. Records before 2011 have no GPS coordinates — locations are identified by park unit and site name only. E. coli colony counts are stored as text because some readings exceed lab quantification limits and are recorded as ">2000" or "TNTC" (too numerous to count).

**CDM Alignment Notes:** No standard CDM entity. Ecological monitoring is domain-specific and would require custom entities. The mixed-entity observation table will need to be split into separate models (flora/fauna, water quality) at the base or staging layer.

**Status:** Defined

---

## Classification and Status Terms

### Lifecycle Status

**Definition:** The operational state of a data source in DCR's inventory. Each inventoried system is assigned one of the following statuses:

- **Active — Primary:** Currently operational; designated source of truth for its domain.
- **Active — Secondary:** Currently operational but not the designated source of truth; may hold supplementary or regional data.
- **Active — Mandated:** Operational use is required by statute, statewide policy, or federal compliance; DCR has no authority to replace or modify.
- **Pilot:** Deployed to a limited subset of park units or regions for evaluation; not yet approved for system-wide adoption.
- **Partially Implemented:** Approved for system-wide use but adoption is incomplete, resulting in parallel processes in non-adopting units.
- **Decommissioned:** No longer receiving new data; retained in read-only state for historical reference or statutory retention.
- **Fragmented:** No single instance serves the domain; data is distributed across multiple disconnected tools, files, or practices by park unit or region.

**Source of Truth:** DCR Data Inventory.

**Status:** Defined

---

### Sensitivity Classification

**Definition:** The data handling category assigned to each source system, governing who may access the data and under what conditions:

- **Public:** Publishable without restriction.
- **Internal:** Restricted to DCR staff and authorized contractors; no public disclosure without review.
- **Confidential:** Contains PII, financial account data, or personnel records; access restricted to named stewards and authorized roles.
- **Restricted — Statutory:** Governed by a specific federal or state statute (e.g., CJIS, ARPA, state endangered species laws); access requires compliance certification and may be audited.

**Source of Truth:** DCR Data Inventory. Applied at the system level; some systems carry mixed classifications (e.g., GeoParks is mostly Internal but cultural resource layers are Restricted — Statutory).

**Status:** Defined

---

### Region

**Definition:** One of DCR's four administrative regions, each comprising a geographically and operationally distinct group of park units:

- **Region 1** — Urban-proximate parks. Includes the agency's "Flagship" parks with the highest visitation and most developed infrastructure. Fully onboarded to InfraTrak. Highest data system adoption and work order discipline (~90% completion rate).
- **Region 2** — Suburban and mixed parks. "High Utilization" parks with significant visitation. Fully onboarded to InfraTrak but with lower work order completion rates (~70%) due to mobile connectivity issues in canyon parks.
- **Region 3** — Rural parks. Not onboarded to InfraTrak (Phase 2 paused). Maintenance tracked on paper. Lower data system adoption. Coding discipline for SGF expenditures may differ from Regions 1–2.
- **Region 4** — Remote parks. Not onboarded to InfraTrak. Paper-based processes. Data from enterprise systems systematically understates the operational reality of these parks.

The regional adoption divide is the most consequential structural pattern in DCR's data landscape. Any "statewide" analysis produced from enterprise systems covers only Regions 1–2 for asset management, and may carry regional coding inconsistencies for financial data.

**Source of Truth:** PeopleFirst HR (DCR-HCM-01) for organizational structure; GeoParks Enterprise (DCR-GEO-01) for geographic boundaries.

**Status:** Defined

---

### Fiscal Year

**Definition:** DCR's fiscal year runs from July 1 through June 30 of the following calendar year. For example, Fiscal Year 2026 runs from July 1, 2025 through June 30, 2026.

**Source of Truth:** StateGov Financials (DCR-FIN-01), which processes all transactions in monthly fiscal period batches aligned to this calendar.

**Known Discrepancies:** SGF dates use the mainframe's native `YYYYMMDD` fixed-width format. Calendar-year-based analysis (e.g., comparing January–December visitation across years) will not align with fiscal-year-based financial data without explicit date logic in the dbt models.

**CDM Alignment Notes:** CDM uses a standard `FiscalCalendar` entity.

**Status:** Defined

---

## Glossary Index

| # | Term | Domain | Status |
|---|------|--------|--------|
| 1 | Park / Park Unit | Core Entity | Defined |
| 2 | Asset | Core Entity | Contested |
| 3 | Employee / Staff / Worker / Officer | Core Entity | Draft |
| 4 | Customer / Guest / Visitor | Core Entity | Defined |
| 5 | Species | Core Entity | Defined |
| 6 | Revenue | Financial | Defined |
| 7 | Expenditure | Financial | Defined |
| 8 | Grant Award vs. Grant Application | Financial | Defined |
| 9 | Deferred Maintenance / Maintenance Backlog | Financial | Defined |
| 10 | Facility Condition Index (FCI) | Financial | Defined |
| 11 | Object Code | Financial | Defined |
| 12 | Visit / Visitation | Operational | Contested |
| 13 | Reservation | Operational | Defined |
| 14 | Occupancy Rate | Operational | Defined |
| 15 | Work Order | Operational | Defined |
| 16 | Incident | Operational | Defined |
| 17 | Survey / Observation | Operational | Defined |
| 18 | Lifecycle Status | Classification | Defined |
| 19 | Sensitivity Classification | Classification | Defined |
| 20 | Region | Classification | Defined |
| 21 | Fiscal Year | Classification | Defined |
