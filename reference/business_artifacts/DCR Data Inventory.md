# Data Inventory: Department of Conservation and Recreation (DCR)

**Document Classification:** Internal — Data Governance
**Version:** 2.0
**Last Updated:** 2026-02-14
**Inventory Steward:** Office of Strategic Technology, DCR Central Administration
**Review Cycle:** Annual (next review scheduled Q1 2027)

---

## Purpose and Scope

The purpose of this document is to give DCR a single, reliable place to answer three questions about its data: where does it live, who is responsible for it, and what condition is it in. Without that foundation, every downstream effort — building a data catalog, reconciling financial reports across systems, or justifying an infrastructure budget to the legislature — starts from an incomplete picture.

This inventory registers the primary data sources that support operations across the Department of Conservation and Recreation, covering 50 park units in four administrative regions. It is the first artifact in DCR's data governance program; it is designed to be actionable on its own but also to feed directly into the technical data catalog and business glossary that will follow.

### How This Document Relates to the Data Catalog and Business Glossary

These three documents serve different customers and answer different questions. Keeping them separate prevents the kind of sprawl where one document tries to do everything and becomes unmaintainable.

**This Document — Data Inventory**
Answers: *What data sources exist, where do they reside, who owns them, and what is their operational condition?*
Audience: Data governance council, IT leadership, executive sponsors, and any downstream process — including automated cataloging — that needs a registry of source systems.
Contains: Source-level identification, ownership, lifecycle status, domain scope, sensitivity classification, integration dependencies, quality assessments, and historical context.
Does not contain: Table or column definitions, data types, schema diagrams, transformation logic, or business term definitions.

**Data Catalog** (to be generated from this inventory)
Answers: *What specific data objects exist within each source, and how are they technically structured?*
Audience: Data engineers, analysts, report developers.
Contains: Schema definitions, table and column inventories, data types, primary and foreign key relationships, data lineage, profiling statistics, and access patterns.

**Business Glossary** (to be generated separately)
Answers: *What do our business terms mean, and how are they measured?*
Audience: Business stakeholders, analysts, data stewards.
Contains: Canonical definitions for terms like "Visit," "Occupancy Rate," "Deferred Maintenance," or "Enterprise Fund Revenue" — including business logic, valid value sets, calculation methodologies, and the mapping of each term to its source of truth.

### Agency Context

DCR manages 50 park units classified across five types — State Parks, State Recreation Areas, State Natural Reserves, State Historic Parks, and State Beaches — spanning approximately 285,000 acres. The agency operates under a hybrid funding model: enterprise fund revenues, declining general fund appropriations, federal grants, and concessionaire franchise fees. Annual visitation exceeds 18 million; the workforce includes approximately 420 FTE staff, 600 seasonal employees, and an estimated 4,200 active volunteers.

The data landscape reflects over four decades of technology adoption, organizational restructuring, and shifting strategic priorities. What this tells us is that the current environment was not designed; it accumulated. A 2021 migration brought reservation and revenue operations onto a modern SaaS platform. A statewide mainframe has anchored financial operations since the 1990s. A partially implemented enterprise asset management system covers roughly half the park system. An air-gapped law enforcement records system operates under federal compliance constraints. And a long tail of spreadsheets, legacy databases, and paper-based processes persists in the areas where enterprise solutions have not reached — or have been resisted.

---

## Inventory Conventions

### Source Identifier Format

Each source is assigned a stable identifier following the pattern `DCR-[DOMAIN]-[SEQ]`, where DOMAIN is a three-letter abbreviation for the primary business domain and SEQ is a two-digit sequence number. These identifiers should be used as foreign keys when cross-referencing sources in the data catalog and business glossary.

### Lifecycle Status Definitions

| Status | Definition |
|---|---|
| **Active — Primary** | Currently operational; designated source of truth for its domain. |
| **Active — Secondary** | Currently operational but not the designated source of truth; may hold supplementary or regional data. |
| **Active — Mandated** | Operational use is required by statute, statewide policy, or federal compliance; DCR has no authority to replace or modify. |
| **Pilot** | Deployed to a limited subset of park units or regions for evaluation; not yet approved for system-wide adoption. |
| **Partially Implemented** | Approved for system-wide use but adoption is incomplete, resulting in parallel processes in non-adopting units. |
| **Decommissioned** | No longer receiving new data; retained in read-only state for historical reference or statutory retention. |
| **Fragmented** | No single instance serves the domain; data is distributed across multiple disconnected tools, files, or practices by park unit or region. |

### Data Sensitivity Classifications

| Classification | Handling |
|---|---|
| **Public** | Publishable without restriction. |
| **Internal** | Restricted to DCR staff and authorized contractors; no public disclosure without review. |
| **Confidential** | Contains PII, financial account data, or personnel records; access restricted to named stewards and authorized roles. |
| **Restricted — Statutory** | Governed by a specific federal or state statute (e.g., CJIS, HIPAA, archaeological protection laws); access needs compliance certification and may be audited. |

---

## Source Inventory

---

### DCR-REV-01: VistaReserve

| Attribute | Detail |
|---|---|
| **System Type** | Enterprise SaaS (multi-tenant, cloud-hosted) |
| **Vendor** | VistaReserve Inc. (contract through 2028 with two optional renewal years) |
| **Implementation Date** | March 2021 |
| **Lifecycle Status** | Active — Primary |
| **Business Domain** | Revenue Operations · Visitor Services · Customer Management |
| **Data Steward** | Director of Revenue Operations, Central Administration |
| **Technical Contact** | IT Applications Team Lead |
| **Sensitivity Classification** | Confidential (contains customer PII including names, email addresses, phone numbers, mailing addresses, and payment transaction references) |

**Authoritative Scope**

VistaReserve is the source of truth for all public-facing commercial transactions occurring after March 2021. Its authority spans:

- *Recreational Inventory:* The canonical registry of all bookable assets — campsites (primitive, electric, full-hookup, group), cabins, lodge rooms, marina slips, picnic shelters, and day-use areas. Each inventory record carries attributes for utility hookup type, ADA accessibility designation, maximum occupancy, pet policy, and seasonal availability windows.
- *Reservations and Transactions:* The full reservation lifecycle (search, hold, booking, modification, cancellation, no-show) and point-of-sale transactions for retail goods (firewood, ice, branded merchandise), day-use entry fees, and equipment rentals processed at staffed contact stations.
- *Customer Profiles:* Guest account records including residency status (used to calculate in-state versus out-of-state differential pricing), purchase history, and annual pass membership status. Veteran and senior discount eligibility flags are stored but verified through a manual process at check-in.
- *Pass and Membership Management:* Annual recreation passport sales, gift pass activations, and promotional campaign codes. Pass revenue is tracked separately from transactional revenue for enterprise fund reporting.
- *Financial Settlement:* Daily batch files summarizing gross revenue by park unit and revenue category, generated for reconciliation against StateGov Financials (DCR-FIN-01) and transmitted via scheduled SFTP.

**Data Quality Assessment**

Transactional data integrity is high for records originating after the March 2021 go-live. The known quality issues are specific and well-documented:

- *Customer Duplicate Proliferation:* The platform's self-service account creation has produced an estimated 18–22% duplicate rate in the customer profile table; guests routinely create new accounts rather than recovering credentials. No automated deduplication is in place. Revenue Operations staff perform a quarterly manual merge on the top 200 accounts by transaction volume — a workaround that addresses the most visible duplicates but leaves the underlying problem intact.
- *Inventory-to-GIS Identifier Mismatch:* VistaReserve's internal asset identifiers were assigned during the 2021 implementation using a new numbering scheme that does not correspond to the GIS feature IDs in GeoParks Enterprise (DCR-GEO-01) or the asset tags in InfraTrak Lifecycle (DCR-AST-01). A crosswalk table was created manually during implementation but has not been maintained since 2022; it is known to be incomplete for assets added or reclassified after that date.
- *Kiosk Transaction Gaps:* Twelve remote park units operate unstaffed cash-only fee collection kiosks that do not integrate with VistaReserve. Revenue from these kiosks is recorded on paper logs (see Known Gaps) and entered into VistaReserve manually by regional administrative staff on a weekly or biweekly cycle — introducing both latency and transcription errors into revenue reporting for those units.
- *Semi-Structured Metadata in Exports:* VistaReserve's data exports include JSON metadata columns that capture booking context (source channel, device type, promotional codes, modification history, special requests) and customer preference data (communication preferences, campsite preferences, equipment owned). These columns provide analytically valuable detail that is not available in the structured fields but requires parsing to use. A small percentage of booking metadata records contain malformed JSON due to export processing errors in the API — truncated strings or missing closing braces that must be handled defensively during ingestion.

**Integration Dependencies**

- Outbound daily revenue batch to DCR-FIN-01 (StateGov Financials) via SFTP.
- The asset crosswalk table nominally links VistaReserve inventory IDs to DCR-GEO-01 (GeoParks Enterprise) feature IDs and DCR-AST-01 (InfraTrak) asset tags, but this mapping is stale and incomplete.
- Customer email addresses are exported weekly to the agency's email marketing service (not inventoried as a primary data source; it operates as a downstream consumer only).

**Historical Context**

VistaReserve replaced a legacy on-premise reservation system (see DCR-REV-02) that had operated since 2005. The migration was a hard cutover with no parallel-run period, and historical reservation records were not migrated — they reside in the LegacyRes_Archive. This creates a hard boundary, referred to internally as "the data cliff," at March 2021. Any longitudinal analysis of visitation, revenue, or customer behavior spanning the pre- and post-migration periods needs a join across two sources with incompatible identifiers and different data models.

---

### DCR-REV-02: LegacyRes_Archive

| Attribute | Detail |
|---|---|
| **System Type** | Static SQL database dumps and flat file extracts (CSV, fixed-width) stored on agency file server |
| **Original System** | ParkRes Pro (on-premise client-server application, decommissioned) |
| **Operational Period** | 2005–2021 |
| **Lifecycle Status** | Decommissioned (read-only; no new data since March 2021) |
| **Business Domain** | Historical Revenue Operations · Historical Visitor Services |
| **Data Steward** | Director of Revenue Operations, Central Administration (inherited; no dedicated steward) |
| **Technical Contact** | IT Infrastructure Team (storage and backup only) |
| **Sensitivity Classification** | Confidential (contains historical customer PII; subject to the same retention and handling rules as active PII) |

**Authoritative Scope**

LegacyRes_Archive is the sole surviving record of reservation and revenue transaction activity from 2005 through February 2021:

- *Historical Reservations:* Booking records including dates, campsite or facility identifiers (using the pre-2021 numbering scheme), guest names, and transaction amounts. Records from 2005–2012 are stored as fixed-width flat files exported from the original mainframe-era booking module that ParkRes Pro itself replaced; records from 2012–2021 are stored as SQL Server database backups.
- *Historical Revenue Summaries:* Monthly revenue aggregations by park unit, used for legislative budget justifications. These summaries were the primary source for the agency's "20-Year Revenue Trend" report until 2023, when the report was suspended because reconciling pre- and post-migration data proved too labor-intensive to sustain.
- *Legacy Customer Records:* Guest name and address data in formats that predate current PII handling standards. Some records include partial credit card numbers (first six and last four digits) — a practice discontinued in 2014 following a state audit finding.

**Data Quality Assessment**

- *Identifier Incompatibility:* Campsite and facility identifiers follow a scheme that was retired during the 2021 re-mapping project. No automated crosswalk exists between legacy IDs and the identifiers now used in VistaReserve (DCR-REV-01) or GeoParks Enterprise (DCR-GEO-01). A partial manual crosswalk covering the 15 highest-volume parks was created by a seasonal analyst in 2022 and exists as a standalone spreadsheet on a shared drive.
- *Format Heterogeneity:* The archive contains data in at least three distinct formats — fixed-width text, SQL Server backups, and summarized CSV extracts — reflecting the multiple system generations that preceded VistaReserve. There is no unified query interface; analysts must know which format corresponds to which date range.
- *Field-Level Format Inconsistency:* The format heterogeneity extends below the file level into individual fields. Date values are stored as text strings whose format depends on the export era: the 2005–2010 flat-file records use fixed-width `MMDDYYYY` (no delimiters), the 2011–2015 SQL dump records use ISO `YYYY-MM-DD`, and the 2016–2021 CSV exports use abbreviated `M/D/YY`. Guest information is packed into single fields as pipe-delimited strings because the flat-file era's record layout had a fixed-width "guest detail" block rather than separate name, phone, and email fields — a pattern that persisted into later exports even after the underlying system supported separate fields. The legacy fee schedule data, exported alongside reservation records, is structured as a wide table with rate columns for each season and discount percentages stored as text strings including the percent sign.
- *Retention Risk:* The archive resides on an aging file server with no disaster recovery replication. IT has flagged this, but migration to modern storage has not been funded.

**Integration Dependencies**

- None active. This source is read-only and accessed ad hoc by analysts who manually extract and transform data for historical comparisons.
- The partial crosswalk spreadsheet linking legacy site IDs to current VistaReserve IDs is not version-controlled and has no formal steward.

**Historical Context**

ParkRes Pro was deployed in 2005, replacing a mainframe booking module that had been in service since the early 1990s. The 2005 migration was itself incomplete — fixed-width exports from the mainframe era were carried forward as archival files rather than being imported into ParkRes Pro's relational schema. When ParkRes Pro was decommissioned in 2021 to make way for VistaReserve, the same pattern repeated: data was exported and stored rather than migrated. The result is a three-layer archaeological record of reservation data — each layer in a different format with different identifiers — all nominally under the stewardship of a role that has no dedicated time allocated for archive management.

---

### DCR-FIN-01: StateGov Financials (SGF)

| Attribute | Detail |
|---|---|
| **System Type** | Statewide enterprise mainframe (COBOL backend with a web-based transaction entry wrapper deployed in 2016) |
| **Hosting** | State Department of Administration central data center (on-premise, state-managed) |
| **Operational Since** | 1994 (DCR has been a tenant agency since the system's inception) |
| **Lifecycle Status** | Active — Mandated |
| **Business Domain** | Financial Management · Accounting · Appropriations · Vendor Payments |
| **Data Steward** | DCR Chief Financial Officer (for DCR-specific data); statewide system administration by the Department of Administration |
| **Technical Contact** | Department of Administration mainframe operations team (external to DCR) |
| **Sensitivity Classification** | Confidential (contains vendor tax identification numbers, bank routing information for ACH payments, and employee reimbursement records) |

**Authoritative Scope**

SGF is the legally mandated source of truth for all state financial transactions. DCR, like every state agency, must record all revenues, expenditures, and encumbrances in SGF to satisfy statutory audit obligations:

- *General Ledger:* All transactions coded to DCR's appropriation structure — General Fund appropriations, Enterprise Fund revenues and expenditures, federal pass-through funds, and dedicated tax receipts. Each transaction is coded to a hierarchical chart of accounts: agency, division, program, fund source, and object code.
- *Accounts Payable:* Payment records for all vendors, contractors, and utility providers; includes purchase order references, invoice data, and payment disbursement dates.
- *Encumbrances:* Pre-committed budget authority for open purchase orders and multi-year contracts, particularly significant for capital improvement projects.
- *Capital Project Budget Tracking:* High-level budget allocations and drawdowns for major infrastructure projects, identified by a state-assigned project code (e.g., "Project 404: North Dam Rehabilitation"). Capital project records in SGF track aggregate financial commitments but not project milestones, physical progress, or asset-level detail.

**Data Quality Assessment**

- *Accuracy Without Granularity:* SGF data passes rigorous annual state audits and is considered highly accurate at the transaction level. The chart of accounts structure, however, was designed for statewide fiscal reporting — not for park-level operational analysis. A maintenance expenditure coded to "Object Code 7340 — Building Repair" cannot be attributed to a specific building, trail, or asset within SGF. Analysts must join SGF expenditure data with work order data from InfraTrak Lifecycle (DCR-AST-01) to understand *what* was repaired, but the two systems share no common key; the join is performed manually using date ranges and dollar amount matching, which is error-prone.
- *Temporal Granularity:* SGF processes transactions in monthly fiscal period batches. Revenue data that arrives from VistaReserve in daily batches is aggregated into monthly periods within SGF, erasing the daily-level detail needed for operational revenue management.
- *Embedded Batch Detail:* While the general ledger aggregates transactions to monthly periods, the daily-level detail from subsidiary system batches is preserved in a text memo field (`batch_detail_text`) on each GL entry as a pipe-delimited string of sub-transactions. This field has been present since the system's 1994 deployment but is not parsed by any downstream system — it exists as an audit trail artifact. The sub-record format is inconsistent: most entries follow an `invoice_ref|amount|description|date` pattern, but a small percentage are truncated, malformed, or contain placeholder text like "SEE ATTACHED" from operators who deferred detail entry.
- *Coding Discipline Variance:* Different DCR regions use inconsistent practices when coding expenditures to SGF's object codes. A Region 1 manager may code a trail bridge repair as "Infrastructure — Bridges" while a Region 3 manager codes an equivalent repair as "Building Repair — Other." This inconsistency undermines cross-regional financial analysis and has been documented in two consecutive internal audit findings without resolution.
- *Consolidated Budget Activity Export:* The mainframe's budget activity reporting function exports appropriations, allotments, expenditures, and revenue postings into a single flat extract (`budget_activity_log`) with an activity type discriminator. Different columns are meaningful for different activity types — vendor references appear only on expenditure records, revenue source codes only on revenue records, appropriation authority citations only on appropriation records. Dates are exported in the mainframe's native `YYYYMMDD` fixed-width format. Operator initials (2–3 uppercase characters) are captured on each entry but do not link to any employee record in the system.

**Integration Dependencies**

- Inbound daily revenue batch from DCR-REV-01 (VistaReserve) via SFTP; aggregated into monthly periods.
- DCR-FIN-02 (GrantTrack_Excel_Master) references SGF appropriation codes and encumbrance numbers but is maintained independently, creating reconciliation friction.
- PeopleFirst HR (DCR-HCM-01) payroll disbursements flow through SGF as a statewide feed; DCR does not control this integration.

**Historical Context**

SGF was deployed statewide in 1994 pursuant to a legislative mandate to centralize financial reporting. The COBOL backend has been continuously operational since then. A web-based transaction entry interface was layered on in 2016 — replacing green-screen terminal access for day-to-day use — but the underlying data model and batch processing architecture remain unchanged. Multiple legislative proposals to replace SGF with a modern ERP have been introduced and abandoned over the past decade due to cost and complexity concerns. The takeaway here seems to be that DCR, like all tenant agencies, has adapted its internal processes around SGF's limitations rather than expecting the system to change.

---

### DCR-FIN-02: GrantTrack_Excel_Master

| Attribute | Detail |
|---|---|
| **System Type** | Multi-tab Microsoft Excel workbook on a shared network drive |
| **Hosting** | DCR Central Administration shared file server (\\\\dcr-fs01\budget\grants\) |
| **In Use Since** | 2009 (current workbook lineage; earlier versions existed as separate files per grant) |
| **Lifecycle Status** | Active — Secondary (critical operational dependency despite not being a sanctioned enterprise system) |
| **Business Domain** | Grant Management · Federal Program Compliance · Match Fund Tracking |
| **Data Steward** | Senior Budget Analyst, Central Budget Office |
| **Technical Contact** | None (maintained entirely by business users) |
| **Sensitivity Classification** | Internal (contains award amounts and federal reporting data but no PII) |

**Authoritative Scope**

This workbook exists because SGF (DCR-FIN-01) records the financial transactions associated with grant expenditures but does not capture grant application status, award terms, reporting deadlines, matching fund obligations, or reimbursement workflows. GrantTrack fills that gap — it is the only source that tracks the full lifecycle of federal and private grants received by DCR:

- *Grant Application Pipeline:* Active applications, submission dates, reviewing agency, and estimated award timelines.
- *Active Awards:* Federal grants (Land and Water Conservation Fund, FEMA hazard mitigation, Recreational Trails Program) and private endowment grants. Each award record includes the award amount, performance period, authorized expenditure categories, and the state or local match percentage.
- *Compliance Deadlines:* Reporting due dates for federal progress reports, financial status reports (SF-425), and performance metrics submissions. Conditional formatting in the workbook highlights deadlines approaching within 30 days.
- *Match Fund Tracking:* Running calculations of match obligations (cash and in-kind) against documented contributions. In-kind match calculations for volunteer labor reference data from VolunTracker records, but this cross-reference is manual — copy-paste from park-level spreadsheets. Individual contributions within a match tracking entry may list multiple contributing parties in a single cell, because the workbook was designed for per-transaction entry rather than per-contributor entry.
- *Reimbursement Requests:* Status tracking for cost-reimbursement claims submitted to federal agencies, including submitted amounts, approved amounts, and dates funds were received. These records cannot be derived from SGF because SGF tracks expenditures at the object code level, not at the individual grant draw level.

**Data Quality Assessment**

- *Single Point of Failure:* Three specific budget analysts maintain this workbook. Institutional knowledge of the tab structure, formula dependencies, and manual cross-reference procedures is not documented anywhere. Staff turnover in this unit would create an immediate operational crisis.
- *Version Control Absence:* The workbook resides on a shared drive with no formal version control. Analysts have adopted an informal convention of appending dates to filenames (e.g., "GrantTrack_Master_20260110_backup.xlsx"), but this is inconsistent. At least four files with similar names exist in the same directory; it is not always clear which is current.
- *Formula Fragility:* Cross-tab references and nested lookup formulas have been incrementally extended over 15+ years. Two tabs contain circular reference warnings that have been suppressed. A 2024 internal review found that some match fund calculations produce incorrect results when grant records span fiscal years — the cause was a hardcoded year reference in a lookup formula.
- *Export Format Irregularities:* When the workbook's tabs are exported to CSV for downstream consumption, the data carries Excel artifacts that reflect decades of inconsistent manual entry. The "Budget Tracking" tab exports as a pivoted table with fiscal year columns rather than normalized rows. Monetary values appear in mixed formats — some with dollar signs and comma separators, some as plain numbers, some as text placeholders ("TBD", "pending") where the analyst deferred entering the amount. Date fields exported from different tabs use different formats depending on which analyst last edited the tab — ISO dates in recently maintained tabs, US-format dates in older tabs, and natural-language dates in the oldest entries. Contact information for grant applicants is stored in single merged cells as pipe-delimited strings. Match fund contributor names are stored as comma-separated lists within single cells because the workbook has no separate contributors reference.
- *Reconciliation Gap:* Grant expenditure totals in this workbook frequently diverge from the corresponding totals in SGF by 2–5%, attributed to timing differences (the workbook is updated when a reimbursement is *submitted*; SGF reflects when the expenditure is *posted*) and to the coding discipline variance described in DCR-FIN-01.

**Integration Dependencies**

- Manual cross-reference to SGF (DCR-FIN-01) appropriation codes and encumbrance numbers.
- Manual cross-reference to volunteer hour totals maintained in park-level spreadsheets and the VolunTracker SaaS instance (see Known Gaps) for in-kind match calculations.
- No automated data feeds in or out; all data entry and reconciliation is manual.

**Historical Context**

Before 2009, individual grants were tracked in separate spreadsheets maintained by whichever program office administered the grant. The Senior Budget Analyst at the time consolidated these into a single workbook to prepare for a federal single audit; the consolidation worked well enough that the workbook became the de facto grant management system. Two attempts to replace it with a purpose-built grant management SaaS application were initiated — in 2017 and again in 2022 — and both were abandoned. The first lost funding during a recession; the second stalled because the selected vendor could not replicate the workbook's match fund tracking logic within the implementation timeline. This is a pattern worth noting: the system persists not because it is robust, but because its business logic has become too embedded and too specific for a straightforward replacement.

---

### DCR-AST-01: InfraTrak Lifecycle

| Attribute | Detail |
|---|---|
| **System Type** | Enterprise Asset Management (EAM) SaaS platform |
| **Vendor** | InfraTrak Systems (contract through 2027) |
| **Implementation Date** | Phase 1 (Regions 1 & 2): 2020. Phase 2 (Regions 3 & 4): originally scheduled for 2022; currently paused. |
| **Lifecycle Status** | Partially Implemented |
| **Business Domain** | Physical Asset Management · Maintenance Operations · Facility Condition Assessment · Capital Planning |
| **Data Steward** | Chief of Facilities and Infrastructure, Central Administration |
| **Technical Contact** | IT Applications Team, with vendor support escalation |
| **Sensitivity Classification** | Internal (contains infrastructure vulnerability assessments that could pose security concerns if disclosed publicly, but no PII) |

**Authoritative Scope**

InfraTrak Lifecycle is intended to be the source of truth for all physical assets owned or maintained by DCR. In practice, its authority is limited to the 28 park units in Regions 1 and 2 where it has been fully deployed:

- *Asset Registry:* Buildings, roads, trails, bridges, dams, water treatment systems, wastewater systems, electrical distribution infrastructure (including individual campsite pedestals), and marine structures. Each asset record carries a unique asset tag, geographic coordinates, construction date (where known), estimated replacement value, and design lifespan.
- *Work Orders:* Corrective and preventative maintenance work orders — labor hours, material costs, contractor invoices, and completion status. Work orders are linked to specific assets, enabling cost-per-asset analysis.
- *Condition Assessments:* Periodic inspection records scoring each asset on a standardized 1–100 Facility Condition Index (FCI) scale. Assessment frequency varies by asset criticality: dams and water systems are assessed annually; standard facilities like restrooms and picnic shelters are on a three-year cycle.
- *Deferred Maintenance Backlog:* Calculated estimates of the cost to bring each asset to "good" condition (FCI ≥ 70), aggregated into a statewide backlog figure used in legislative budget requests.

**Data Quality Assessment**

- *Regional Coverage Gap:* Regions 1 and 2 (28 park units, primarily the "Flagship" and "High Utilization" parks near population centers) have complete and regularly updated asset data. Regions 3 and 4 (22 park units — predominantly rural, remote, and lower-visitation) were never onboarded due to the paused Phase 2 implementation. Assets in these regions are not represented in InfraTrak at all; maintenance activity is recorded on paper work order forms and, in some parks, in locally maintained spreadsheets. The data suggests that InfraTrak under-reports the true statewide deferred maintenance backlog by approximately 40%.
- *Asset Completeness in Onboarded Regions:* Even within Regions 1 and 2, the initial asset registry was loaded from a combination of GIS data from GeoParks Enterprise (DCR-GEO-01) and a 2019 field inventory conducted by a contracted engineering firm. Assets that were not visible during the field inventory — underground utilities, minor outbuildings — are missing. New assets constructed or acquired after 2020 have been inconsistently entered, depending on whether the project manager submitted an asset registration form.
- *Work Order Discipline:* Completion rates are high in Region 1 (estimated 90%+ of maintenance activities result in a closed work order) but noticeably lower in Region 2 (estimated 70%), where maintenance staff have reported unreliable mobile app connectivity in several canyon parks.

**Integration Dependencies**

- Asset tags are nominally linked to VistaReserve (DCR-REV-01) inventory IDs and GeoParks Enterprise (DCR-GEO-01) feature IDs through the same crosswalk table described in DCR-REV-01. The crosswalk's staleness affects InfraTrak equally.
- Work order cost data is not integrated with SGF (DCR-FIN-01). Capital project spending tracked in SGF cannot be automatically attributed to specific assets in InfraTrak; operational maintenance costs in InfraTrak cannot be reconciled against SGF expenditure postings without manual effort.
- Condition assessment scores are exported annually as a static PDF for inclusion in legislative budget request packages. No live data feed exists for this purpose.

**Historical Context**

Before InfraTrak, the agency had no centralized asset management system — maintenance was tracked through paper work orders, regional spreadsheets, and institutional memory held by long-tenured supervisors. The 2018 legislative session, prompted by a dam safety incident at a state park in a neighboring state, authorized and funded a statewide EAM implementation. Phase 1 was completed on schedule in 2020, but Phase 2 funding was redirected to pandemic-related operational costs in 2021 and has not been restored. The current two-tier reality — where half the agency operates with modern asset data and the other half operates on paper — is the single most frequently cited data challenge in DCR leadership discussions and has been flagged in three consecutive legislative audit reports.

---

### DCR-LES-01: RangerShield CAD/RMS

| Attribute | Detail |
|---|---|
| **System Type** | Computer Aided Dispatch (CAD) and Records Management System (RMS), on-premise |
| **Hosting** | Dedicated secure server room at DCR Law Enforcement Division headquarters; CJIS-compliant physical and network controls |
| **Implementation Date** | 2014 (RMS); 2017 (CAD module added) |
| **Lifecycle Status** | Active — Mandated (CJIS Security Policy compliance is a federal statutory obligation for any system handling criminal justice information) |
| **Business Domain** | Law Enforcement · Public Safety · Criminal Justice Records |
| **Data Steward** | Chief of Law Enforcement, DCR Law Enforcement Division |
| **Technical Contact** | Law Enforcement Division IT Specialist (dedicated position with CJIS security clearance) |
| **Sensitivity Classification** | Restricted — Statutory (governed by FBI CJIS Security Policy; access limited to sworn personnel and authorized CJIS-certified staff; subject to triennial FBI audit) |

**Authoritative Scope**

RangerShield is the exclusive source of truth for all law enforcement and criminal justice data generated by DCR's State Park Peace Officers (SPPOs):

- *Incident Reports:* Case reports for criminal offenses (theft, assault, drug offenses, DUI, resource damage, trespass) and non-criminal incidents (medical aids, lost person reports, search and rescue activations, drowning responses, and wildlife encounters that call for officer response).
- *Citations:* All citations and notices to appear issued by SPPOs — parking violations, resource damage penalties, campground rule violations, and traffic infractions within park boundaries. Includes court disposition data for citations that proceed to adjudication.
- *Dispatch Logs:* Time-stamped records of all radio communications, officer location check-ins, call-for-service assignments, and backup requests. Used for officer safety accountability and post-incident review.
- *Use of Force Documentation:* Standardized reports filed when any level of force is applied, from physical control holds through firearm discharge; subject to mandatory internal review.
- *Officer Activity Logs:* Daily logs documenting patrol routes, visitor contacts, resource checks, and administrative time. Used for workload analysis and staffing models.

**Data Quality Assessment**

- *High Internal Integrity:* Data quality within RangerShield is considered high — driven by mandatory report-writing standards, supervisory review before finalization, and the legal consequences of inaccurate records. Citation data is cross-checked against court system feeds.
- *Complete Isolation:* RangerShield is air-gapped from all other DCR systems. There is no electronic data feed between RangerShield and any other inventoried source. This is deliberate — mandated by CJIS policy — but it has significant consequences for agency-wide reporting. When executive leadership needs incident statistics for annual reports, legislative testimony, or park management plans, those statistics are manually compiled by LE Division administrative staff and delivered as static summaries (typically PDF or printed memoranda). The manual compilation introduces a reporting lag of 2–4 weeks.
- *No Geospatial Integration:* Incident locations are recorded as narrative descriptions (e.g., "Campsite 47, Loop B, Tall Pines State Park") rather than as geographic coordinates. These cannot be programmatically joined to GeoParks Enterprise (DCR-GEO-01) spatial layers without manual geocoding.

**Integration Dependencies**

- Inbound: State criminal justice network feed for warrant checks and criminal history lookups (external to DCR; managed by the state Department of Justice).
- Outbound: None automated. Summary statistics are produced manually for internal DCR customers. Uniform Crime Report (UCR) data is submitted to the state reporting authority quarterly via manual data entry.
- The air-gap is absolute and is not expected to change. Any future analytics or reporting integration would need to operate through a sanitized, aggregated statistical extract that satisfies CJIS audit obligations.

**Historical Context**

Prior to 2014, law enforcement records were maintained in paper case files stored at each park unit. The 2014 RMS implementation consolidated all records into a single, centrally managed digital system for the first time; the CAD module was added in 2017 to support real-time dispatch coordination, replacing voice radio with handwritten logs. The system has been expanded incrementally — body camera evidence management was added as a module in 2023 — and is one of the few areas where DCR's data infrastructure is both modern and well-maintained. The non-negotiable compliance pressure of the CJIS Security Policy has, in this case, been a forcing function for sustained investment and data discipline.

---

### DCR-GEO-01: GeoParks Enterprise

| Attribute | Detail |
|---|---|
| **System Type** | Enterprise geospatial server with geodatabase (ArcGIS-based architecture) |
| **Hosting** | On-premise server at DCR Central Administration; published map services accessible to authorized staff via internal network |
| **Operational Since** | 2008 (current platform; GIS program has existed in various forms since the mid-1990s) |
| **Lifecycle Status** | Active — Primary |
| **Business Domain** | Geospatial Data Services · Land Records · Natural Resource Mapping · Facility Mapping |
| **Data Steward** | GIS Program Manager, Planning and Resource Management Division |
| **Technical Contact** | GIS Analyst Team (2 FTE) |
| **Sensitivity Classification** | Mixed — most layers are Internal or Public; specific layers described below are Restricted — Statutory |

**Authoritative Scope**

GeoParks Enterprise is the spatial backbone of the agency — the authoritative source for the geographic location and extent of all DCR-managed lands, facilities, and natural features:

- *Legal Boundaries:* Surveyed parcel boundaries for all 50 park units, including easement boundaries, right-of-way corridors, and inholding parcels (private land within park boundaries). Boundary data is synchronized with the state cadastral database on an annual basis.
- *Infrastructure Layers:* Spatial representations of trails (centerlines with surface type and difficulty attributes), roads (paved and unpaved, with lane and width attributes), buildings (footprints), utility corridors (water, sewer, electric — above and below ground), parking areas, boat ramps, and campsite point locations.
- *Natural Resource Layers:* Vegetation classification polygons (derived from a 2019 statewide aerial survey), hydrological features (streams, lakes, wetland delineations), soil types, and critical habitat designations for listed species.
- *Cultural Resource Layers:* A restricted-access layer set containing the precise locations of documented indigenous archaeological sites, burial grounds, and sacred sites. Access requires written authorization from both the GIS Program Manager and the State Historic Preservation Officer. These layers are excluded from all public-facing map products pursuant to the Archaeological Resources Protection Act.
- *Recreational Features:* Trailhead locations, scenic overlooks, interpretive signage locations, and points of interest used to generate public-facing park maps and web-based trail maps.

**Data Quality Assessment**

- *Positional Accuracy Variance:* Legal boundary data is surveyed-grade (sub-meter accuracy). Infrastructure layers derived from the 2019 aerial survey are accurate to approximately 1–2 meters. Underground utility line data, however — particularly in parks developed before the 1980s — was digitized from hand-drawn as-built drawings and may carry positional errors of 5+ meters. Three construction projects in the past two years encountered underground utilities that were not where GIS data indicated they would be.
- *Temporal Currency:* The GIS team (2 FTE) maintains layers through field GPS collection, processing of as-built construction drawings, and integration of contractor survey deliverables. Given the volume of data and the small team, some layers are updated in near-real-time (trail closures, boundary amendments) while others lag by one to three years (vegetation classification, utility infrastructure updates).
- *Identifier Authority:* GeoParks feature IDs are the longest-standing identifier system in the agency, predating both VistaReserve and InfraTrak. The feature ID scheme was redesigned in 2008 during the platform migration and is considered stable and well-governed. The crosswalk tables that map GeoParks feature IDs to identifiers in the other two systems (described in DCR-REV-01 and DCR-AST-01) have drifted since 2022 — undermining the GIS program's ability to serve as the unifying spatial reference it was designed to be.

**Integration Dependencies**

- GeoParks feature IDs are referenced (via crosswalk tables of varying quality) by DCR-REV-01 (VistaReserve), DCR-AST-01 (InfraTrak Lifecycle), and DCR-NRM-01 (BioSurvey_Legacy).
- Published map services are consumed by VistaReserve's public-facing reservation map widget, though this integration uses a simplified, cached copy of the data that is refreshed quarterly.
- GeoParks data was used as a baseline for the initial asset inventory load into InfraTrak in 2020, but there is no ongoing synchronization.
- Cultural resource restricted layers are not accessible through any integration; they are served only through a dedicated, access-controlled map application within the GIS environment.

**Historical Context**

DCR's GIS program is one of the agency's most mature data capabilities — it evolved from a single desktop workstation in the mid-1990s to a full enterprise server environment. The 2008 platform migration established the current feature ID scheme and geodatabase architecture. The GIS Program Manager has held the position for 14 years and is the primary custodian of institutional knowledge about spatial data lineage. The program's small team size relative to the volume of data it is expected to maintain is a persistent operational risk; the data quality depends heavily on continuity of that specific expertise.

---

### DCR-NRM-01: BioSurvey_Legacy

| Attribute | Detail |
|---|---|
| **System Type** | Microsoft Access desktop database with linked file attachments |
| **Hosting** | Desktop workstation in the Chief Biologist's office, Central Administration; weekly backup to shared network drive |
| **Operational Since** | 1993 |
| **Lifecycle Status** | Active — Secondary (operationally critical but not on a sanctioned enterprise platform) |
| **Business Domain** | Natural Resource Management · Ecological Monitoring · Water Quality · Endangered Species Compliance |
| **Data Steward** | Chief Biologist, Planning and Resource Management Division |
| **Technical Contact** | None (the Chief Biologist is both the domain expert and the sole technical administrator) |
| **Sensitivity Classification** | Mixed — most data is Internal; endangered species location data is Restricted — Statutory (governed by state endangered species statutes that prohibit public disclosure of specific nesting or denning locations) |

**Authoritative Scope**

BioSurvey_Legacy is the most complete record of ecological monitoring data collected across DCR lands over the past three decades:

- *Flora and Fauna Survey Records:* Observation records from structured biological surveys conducted by DCR biologists, partner university researchers, and trained volunteers. Each record includes species identification, observation date, count or density estimate, observer name, and location (recorded as park unit and site name; geographic coordinates were added beginning in 2011 for new records).
- *Invasive Species Observations:* Location and extent records for invasive plant and animal species, including treatment history where management interventions have been attempted.
- *Endangered Species Monitoring:* Annual population counts and reproductive success metrics for species listed under the state Endangered Species Act — nesting plover pairs (monitored at coastal parks since 1995), endemic salamander populations, and several listed plant species. This data is submitted to the state wildlife agency annually as a compliance obligation.
- *Water Quality Testing:* Results from periodic sampling at lakes, rivers, and coastal beaches within park boundaries: dissolved oxygen, pH, E. coli colony counts, turbidity, temperature, and nutrient levels (nitrogen, phosphorus). Sampling protocols have changed twice during the database's lifespan — 1993–2005 under one laboratory methodology, 2005–2018 under a revised methodology, and 2018–present under current EPA-aligned protocols — creating comparability challenges in longitudinal analysis.

**Data Quality Assessment**

- *Methodological Discontinuities:* The three distinct water quality sampling protocol eras mean that any trend analysis across the full 30-year record needs methodology-aware statistical adjustments. These adjustments are understood by the Chief Biologist but are not documented in the database itself.
- *Spatial Precision Variance:* Records created before 2011 identify locations by park unit and site name only; records from 2011 onward include GPS coordinates. Retroactive geocoding of pre-2011 records has been discussed but never funded.
- *Platform Risk:* The database runs on Microsoft Access — a platform with known limitations in concurrent access, record volume, and long-term supportability. The current file is approaching 1.8 GB, near the Access 2 GB limit. The Chief Biologist has implemented an annual archiving routine to keep the active file below the size threshold, but archived files (stored as separate Access databases on the network drive) are not queryable through the primary interface.
- *Bus Factor:* The Chief Biologist is the sole person who fully understands the database schema, the data entry conventions, the species coding system (a custom alphanumeric scheme developed in 1993), and the relationships between survey records, site locations, and sampling protocols. Documentation of the schema and codes exists only as a hand-annotated printout stored in the biologist's office.
- *Mixed-Entity Data Entry Form:* The Access database's primary data entry form writes all field observations — flora surveys, fauna surveys, and water quality readings — to a single `field_observations_raw` table, with an `observation_type` field distinguishing the record type. Columns that apply only to specific observation types (e.g., pH level for water quality, nesting status for fauna) are present on every row but populated only when relevant — and occasionally populated incorrectly when a field technician uses the wrong observation type. The species codes reference table contains a comma-separated `alternate_names` field that the Chief Biologist maintains for field staff convenience. E. coli colony counts in the water quality records are stored as text rather than integers because some readings exceed the laboratory's quantification limit and are recorded as ">2000" or "TNTC" (too numerous to count). While `field_observations_raw` acts as the primary data entry target, purpose-specific tables like `flora_fauna_surveys` or `water_quality_tests` act as derived extracts maintained within Access for reporting convenience.

**Integration Dependencies**

- Survey locations recorded after 2011 can be plotted against GeoParks Enterprise (DCR-GEO-01) layers, but this is a manual GIS overlay — not an automated integration.
- Endangered species data is submitted to the state wildlife agency annually via a formatted Excel export maintained by the Chief Biologist.
- Water quality data for designated public swimming beaches is reported to the state health department during summer months by manually transcribing results into the health department's web portal.
- No other inventoried system depends on or feeds into BioSurvey_Legacy.

**Historical Context**

The database was created in 1993 using Microsoft Access 2.0 by a DCR biologist who preceded the current Chief Biologist. It has been migrated through successive Access versions (97, 2003, 2010, 2016) with minimal schema changes. Two proposals to migrate the data into a modern ecological data management platform — in 2015 and again in 2021 — reached proof-of-concept stage but were not funded. The 2021 proposal estimated a migration cost of $180,000 including data cleaning, schema redesign, and historical record geocoding; it remains in the agency's IT capital request queue. Despite its fragile platform, BioSurvey_Legacy contains irreplaceable longitudinal ecological data that underpins DCR's endangered species compliance posture and informs management decisions about habitat protection, invasive species response, and climate adaptation planning. The tech debt here is substantial, but so is the cost of losing 30 years of continuous monitoring.

---

### DCR-HCM-01: PeopleFirst HR

| Attribute | Detail |
|---|---|
| **System Type** | Statewide Human Capital Management ERP (cloud-hosted, state-administered) |
| **Hosting** | State Department of Human Resources cloud environment |
| **Operational Since** | 2011 (DCR onboarded as part of statewide rollout) |
| **Lifecycle Status** | Active — Mandated |
| **Business Domain** | Human Resources · Payroll · Benefits Administration · Position Management |
| **Data Steward** | DCR Human Resources Manager (for DCR-specific data); statewide system administration by the Department of Human Resources |
| **Technical Contact** | Department of Human Resources IT division (external to DCR) |
| **Sensitivity Classification** | Confidential (contains employee PII, Social Security numbers, salary data, medical leave records, and disciplinary actions) |

**Authoritative Scope**

PeopleFirst is the mandated source of truth for all employee-related data across state government. DCR's footprint within PeopleFirst covers:

- *Position Management:* The authorized position inventory for DCR — each position's classification (e.g., "Park Ranger I," "Park Ranger II," "Maintenance Worker III," "State Park Peace Officer"), pay grade, assigned organizational unit, and funding source (General Fund, Enterprise Fund, or grant-funded). This is the authoritative record of DCR's authorized FTE count.
- *Employee Records:* Demographic information, hire dates, separation dates, classification history, and duty station assignments for all active and separated employees. Records for separated employees are retained pursuant to state records retention schedules.
- *Payroll:* Gross pay, deductions, withholdings, and net pay for each pay period. Payroll disbursements are processed through SGF (DCR-FIN-01) as part of a statewide payroll feed.
- *Benefits:* Health insurance enrollment, retirement plan contributions, and leave balances (annual, sick, compensatory, military).
- *Seasonal Workforce:* Hiring and separation records for the approximately 600 temporary seasonal employees brought on between April and October each year. Seasonal employees hold time-limited appointment types and are subject to different benefits eligibility rules than permanent staff.

**Data Quality Assessment**

- *Duty Station Granularity:* PeopleFirst records an employee's duty station at the organizational unit level (e.g., "Region 2 — Tall Pines District") but does not track the specific park unit where an employee works day-to-day. For multi-park districts where a maintenance crew serves several units, PeopleFirst cannot answer the question "how many staff hours are allocated to Park X?" This forces park managers to maintain unofficial staffing spreadsheets at the unit level — an edge case that, because of DCR's geographic distribution, affects nearly every district.
- *Seasonal Workforce Timing Lag:* The onboarding process for seasonal employees in PeopleFirst is slow relative to operational need. Seasonal hiring decisions are often made by park managers in February and March, but PeopleFirst records are not created until the employee's official start date in April or May. During the gap, seasonal recruitment tracking is performed in a separate custom web application (see Known Gaps) whose data is not reconciled against PeopleFirst until after onboarding is complete.
- *Training and Certification Blind Spot:* PeopleFirst tracks mandatory statewide training completions (ethics, cybersecurity awareness, harassment prevention) but does not track the specialized certifications that are critical to park operations: POST certification for SPPOs, CDL endorsements for heavy equipment operators, wilderness first responder certifications, pesticide applicator licenses, and water treatment operator certifications. These are tracked across at least four separate locations — the Law Enforcement Division's SharePoint site, the Facilities Division's training spreadsheet, individual supervisor files, and in some cases the employee's own records. There is no single source from which the agency can generate a complete certification compliance report.

**Integration Dependencies**

- Payroll disbursements flow from PeopleFirst through SGF (DCR-FIN-01) as part of a statewide automated feed.
- Position data in PeopleFirst determines the organizational hierarchy used for access control in several other systems, including VistaReserve (DCR-REV-01) and InfraTrak Lifecycle (DCR-AST-01) — but this linkage is maintained manually through access request processes rather than automated identity provisioning.
- No integration with DCR's seasonal hiring process or with any certification tracking system.

**Historical Context**

Before PeopleFirst, DCR's HR data was maintained in a prior statewide personnel system that used a different classification code structure. The 2011 migration introduced some inconsistencies in historical tenure calculations for employees who had been with the agency since before the cutover. PeopleFirst is updated by the state on a regular release cycle; DCR has no ability to customize the system's data model or add agency-specific fields. This is why operational workforce data needs — certifications, park-level staffing — are addressed through workarounds outside the system rather than within it.

---

### DCR-VUM-01: TrafficCount_IoT

| Attribute | Detail |
|---|---|
| **System Type** | IoT sensor network with vendor-hosted cloud analytics dashboard |
| **Vendor** | TerraCount Analytics (annual subscription; sensor hardware owned by DCR) |
| **Implementation Date** | 2024 (initial pilot deployment) |
| **Lifecycle Status** | Pilot |
| **Business Domain** | Visitor Use Management · Carrying Capacity Analysis · Operational Planning |
| **Data Steward** | Visitor Use Program Coordinator, Planning and Resource Management Division |
| **Technical Contact** | IT Infrastructure Team (for network connectivity); TerraCount vendor support (for sensor calibration and dashboard) |
| **Sensitivity Classification** | Public (aggregate count data only; no PII is collected or stored) |

**Authoritative Scope**

TrafficCount_IoT provides automated visitor counting data from a sensor network deployed at a limited subset of DCR park units:

- *Vehicle Counts:* Inductive loop counters embedded in road surfaces at park entrance stations, recording vehicle ingress and egress events with timestamps. Deployed at the primary entrance of 8 park units (all in the "Flagship" or "High Utilization" classification tiers).
- *Pedestrian and Cyclist Counts:* Infrared beam-break sensors installed at 12 high-traffic trailheads across 6 park units, recording individual passage events with timestamps and a directional indicator (inbound vs. outbound).
- *Derived Metrics:* The vendor dashboard calculates hourly, daily, and monthly visit estimates using a configurable vehicle occupancy multiplier — currently set to a statewide default of 2.7 persons per vehicle based on a 2019 intercept survey. The accuracy of this multiplier has not been re-validated. Peak congestion hours, day-of-week patterns, and seasonal trend visualizations are generated automatically.

**Data Quality Assessment**

- *Coverage Gap:* Sensors are deployed at approximately 15% of DCR park units (8 of 50), and these are disproportionately the highest-visitation, most-developed parks. No automated count data exists for the remaining 85%, where visitation is estimated using fee receipt counts from VistaReserve (DCR-REV-01), campground occupancy rates, and annual estimates based on park manager professional judgment. These estimation methods are known to significantly undercount day-use visitation at parks where entry is free or unstaffed.
- *Sensor Reliability:* Inductive loop counters are susceptible to undercounting during continuous slow traffic (vehicles passing while the loop is still resetting) and to double-counting when vehicles with trailers cross the sensor. Infrared trailhead counters are triggered by wildlife (deer, large dogs) and tend to count groups passing simultaneously as a single event. The vendor provides calibration adjustment factors, but DCR has not performed independent validation.
- *Data Ownership Ambiguity:* Raw sensor data is transmitted to the TerraCount vendor cloud in real time; DCR accesses it through the vendor's dashboard and can export CSV files. The contract does not explicitly address data portability or retention after contract termination — IT has flagged this as a risk in the vendor management review.
- *No Integration with Reservation Data:* The vehicle counter at a park entrance counts all vehicles — staff, contractors, and concession deliveries included. There is no automated mechanism to correlate vehicle count data with reservation or fee transaction data from VistaReserve, so distinguishing visitor vehicles from operational traffic is not possible at the data level.

**Integration Dependencies**

- No automated integrations with any other inventoried source. Data is consumed through the vendor dashboard or via manual CSV export.
- The Visitor Use Program Coordinator manually combines TrafficCount data with VistaReserve reservation volumes and park manager estimates to produce the agency's annual "System Visitation Report" — the official visitation figure used in legislative communications and federal grant applications.
- Future integration with GeoParks Enterprise (DCR-GEO-01) for spatial visualization of count data has been proposed but is not in development.

**Historical Context**

Before the 2024 pilot, DCR had no automated visitor counting capability. Visitation figures were derived entirely from fee receipts and campground occupancy data — which only captured paying visitors — supplemented by periodic manual traffic counts using hand-held tally counters. The pilot was funded through a federal Recreational Trails Program grant that itself needs annual progress reporting on visitor use metrics; this creates a circular dependency where the grant that funds the counting infrastructure also needs the data the infrastructure produces. The pilot is scheduled for evaluation in late 2026 to determine whether system-wide expansion will be proposed for the next budget cycle.

---

## Appendix: Source Quick-Reference Matrix

| Source ID | System Name | Type | Status | Primary Domain | Sensitivity | Steward |
|---|---|---|---|---|---|---|
| DCR-REV-01 | VistaReserve | Enterprise SaaS | Active — Primary | Revenue / Visitor Services | Confidential | Dir. of Revenue Operations |
| DCR-REV-02 | LegacyRes_Archive | Static Extracts | Decommissioned | Historical Revenue | Confidential | Dir. of Revenue Operations |
| DCR-FIN-01 | StateGov Financials (SGF) | Statewide Mainframe | Active — Mandated | Financial Management | Confidential | DCR CFO |
| DCR-FIN-02 | GrantTrack_Excel_Master | Excel Workbook | Active — Secondary | Grant Management | Internal | Sr. Budget Analyst |
| DCR-AST-01 | InfraTrak Lifecycle | EAM SaaS | Partially Implemented | Asset Management | Internal | Chief of Facilities |
| DCR-LES-01 | RangerShield CAD/RMS | On-Premise Secure | Active — Mandated | Law Enforcement | Restricted — Statutory | Chief of Law Enforcement |
| DCR-GEO-01 | GeoParks Enterprise | Geospatial Server | Active — Primary | Geospatial Services | Mixed | GIS Program Manager |
| DCR-NRM-01 | BioSurvey_Legacy | MS Access Database | Active — Secondary | Natural Resources | Mixed | Chief Biologist |
| DCR-HCM-01 | PeopleFirst HR | Statewide ERP | Active — Mandated | Human Capital | Confidential | DCR HR Manager |
| DCR-VUM-01 | TrafficCount_IoT | IoT / Vendor Cloud | Pilot | Visitor Use Management | Public | Visitor Use Coordinator |

---

## Cross-Source Observations

The patterns below are not attributable to any single source; they reflect the institutional dynamics that have shaped DCR's data landscape over time. What this tells us, collectively, is where the highest-leverage improvements are — and where some constraints are permanent.

### Identifier Fragmentation

Three systems — VistaReserve (DCR-REV-01), InfraTrak Lifecycle (DCR-AST-01), and GeoParks Enterprise (DCR-GEO-01) — each maintain independent identifier schemes for overlapping sets of physical assets. GeoParks feature IDs are the oldest and most stable, but the crosswalk tables that map these to the other two systems have not been actively maintained since 2022. The practical consequence: answering a question as fundamental as "what is the maintenance cost history and current reservation revenue for Campsite 47 at Tall Pines State Park?" needs a manual, multi-source join using an unreliable crosswalk. Resolving this through a master asset identifier registry or a maintained crosswalk has been identified as a priority but has not been resourced.

### The Regional Adoption Divide

DCR's four administrative regions exhibit sharply different levels of data system adoption — a product of both the phased rollout of enterprise systems and cultural differences between urban-proximate and rural park operations. Regions 1 and 2 operate with relatively mature digital data; Regions 3 and 4 operate with paper forms, local spreadsheets, and institutional knowledge held by long-tenured staff. The takeaway here seems to be that any "statewide" report or analysis produced from enterprise systems systematically understates the operational reality of the rural regions. The gap is most acute in asset management — the 40% undercount of the statewide deferred maintenance backlog — but it affects every domain from volunteer hour tracking to visitation estimation.

### The Financial-to-Operational Join Gap

SGF (DCR-FIN-01) is the legal authority for financial data, but its chart of accounts was designed for state-level fiscal reporting — not park-level operational analysis. The result is a persistent inability to connect *how much was spent* (known to SGF) with *what it was spent on* (known to InfraTrak in Regions 1 and 2, or known only to the maintenance supervisor in Regions 3 and 4). This gap forces parallel financial tracking: the GrantTrack workbook for grant-level detail, informal spreadsheets for park-level budget management — none of which is automatically reconciled with the official financial record.

### Air-Gapped Law Enforcement Data

RangerShield (DCR-LES-01) contains data that is directly relevant to park management decisions; incident hotspot analysis could inform trail routing, staffing models, and campground design. CJIS compliance, however, creates an absolute barrier to electronic integration. All cross-domain use of law enforcement data needs manual extraction, aggregation, and sanitization — introducing significant latency and limiting the granularity available to non-LE decision-makers. This is not a deficiency to be resolved but a permanent architectural constraint that any future data integration strategy must accommodate.

### Single-Steward and Single-Platform Risks

Two sources — BioSurvey_Legacy (DCR-NRM-01) and GrantTrack_Excel_Master (DCR-FIN-02) — carry acute institutional risk because their operational continuity depends on a very small number of individuals and on technology platforms that offer no built-in resilience against data loss, corruption, or staff turnover. Both contain data that is either irreplaceable (30 years of ecological monitoring) or operationally critical (federal grant compliance tracking). Both have been identified for replacement in past planning cycles; neither replacement effort has been funded. The risk is compounded by the fact that the business logic embedded in these sources has become specific enough to resist straightforward migration — the same specificity that makes them operationally valuable also makes them hard to replace.

### Known Data Sources Not Inventoried

The following sources are known to exist within DCR's operational environment but are excluded from this inventory because they do not meet the threshold of a managed, identifiable system. They are documented here to ensure visibility into the broader data landscape and to inform scope decisions for the next annual review:

- *Park-Level Volunteer Tracking:* Volunteer hours and contact information are tracked through a SaaS application at the 5 largest parks and individual Excel spreadsheets at the remaining 45. There is no single source of truth for volunteer data; the statewide volunteer economic impact figure reported annually is an estimate derived from incomplete submissions.
- *Concessionaire Revenue Reporting:* Monthly gross receipt reports from private concessionaires are submitted as PDF or Excel email attachments, tracked in a Finance Department spreadsheet. Revenue figures are self-reported by vendors with no systematic audit mechanism.
- *Fleet Management:* Vehicle and heavy equipment maintenance, fuel consumption, and mileage are tracked in a SaaS fleet management tool. It functions well but was excluded from this version to maintain focus on sources with the most complex integration, quality, or governance challenges. It should be included in the next annual review.
- *General Management Plans and Master Plans:* Approved planning documents — some dating to the 1970s — reside as scanned PDFs and native documents on a SharePoint site and file server. Public comment records from planning processes are stored in the same location. This content is unstructured and not queryable.
- *Seasonal Hiring Portal:* A custom web application used by park managers to post seasonal positions and track applicants during the January–March recruitment phase. Applicant data is not reconciled with PeopleFirst until formal onboarding begins.
- *Unstaffed Kiosk Fee Logs:* Paper-based daily revenue logs from 12 park units with cash-only, unstaffed fee collection kiosks. Data from these logs is manually entered into VistaReserve on a weekly or biweekly cycle by regional administrative staff.
- *Certification and Training Records:* Specialized operational certifications (POST, CDL, Wilderness First Responder, Water Treatment Operator, Pesticide Applicator) are tracked across at least four separate locations — the Law Enforcement Division's SharePoint, the Facilities Division's training spreadsheet, individual supervisor files, and in some cases the employee's own records. No consolidated view exists.
- *Weather and Environmental Monitoring:* Several parks operate small weather stations or stream gauges; data from these sensors is collected by third-party research partners (universities, USGS cooperative programs) and is not centrally held by DCR, though it influences operational decisions like burn bans and beach closures.

### Implications for Downstream Work

This inventory is designed to be consumed by the data catalog and business glossary efforts that follow. Several patterns documented here will directly shape those efforts: the identifier fragmentation problem will need to be addressed before a unified catalog can reliably cross-reference assets across systems; the regional adoption divide means the catalog will need to explicitly account for data that exists in enterprise systems for some parks and in paper or spreadsheet form for others; and the air-gapped law enforcement system will need a separate cataloging approach that respects CJIS constraints while still making aggregate statistical metadata available. The single-steward risks around BioSurvey_Legacy and GrantTrack suggest that schema documentation — which would normally be a data catalog deliverable — should be prioritized for those two sources as a form of institutional knowledge capture, even before the broader catalog is complete.
