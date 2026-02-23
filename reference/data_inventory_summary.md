# DCR Data Inventory — Quick Reference

Condensed from `business_artifacts/DCR Data Inventory.md` (Version 2.0, 2026-02-14).

## 10 Inventoried Systems

### DCR-REV-01: VistaReserve
- **Type**: Enterprise SaaS (cloud) | **Since**: March 2021 | **Status**: Active — Primary
- **Domain**: Reservations, revenue, customer management for all 50 parks
- **Key tables**: Bookable assets, reservations, transactions, customer profiles, passes, daily revenue batches
- **Quality issues**: 18–22% customer duplicate rate; stale crosswalk to GIS/asset IDs (unmaintained since 2022); kiosk revenue entered manually with lag; JSON metadata columns on reservations (booking source, promo codes, modifications) and customer profiles (preferences, equipment); ~5% malformed JSON in booking metadata
- **Sensitivity**: Confidential (PII)

### DCR-REV-02: LegacyRes_Archive
- **Type**: Static SQL dumps + flat files | **Period**: 2005–2021 | **Status**: Decommissioned
- **Domain**: Historical reservations and revenue (pre-VistaReserve)
- **Key tables**: Historical reservations, revenue summaries, legacy customer records
- **Quality issues**: Three incompatible formats; legacy IDs incompatible with current systems; partial crosswalk for 15 parks only; date formats vary by export era (MMDDYYYY, YYYY-MM-DD, M/D/YY as text); guest info packed as pipe-delimited strings; fee schedule exported as wide/pivoted table
- **Sensitivity**: Confidential (historical PII, partial card masks)

### DCR-FIN-01: StateGov Financials (SGF)
- **Type**: Statewide mainframe (COBOL) | **Since**: 1994 | **Status**: Active — Mandated
- **Domain**: General ledger, accounts payable, encumbrances, capital projects
- **Key tables**: General ledger (hierarchical: agency/division/program/fund/object_code), AP, vendors, encumbrances, chart of accounts
- **Quality issues**: Monthly batch aggregation loses daily detail; inconsistent object code usage across regions; no asset-level expenditure attribution; daily batch detail preserved as pipe-delimited text in GL memo field; budget activity export mixes appropriations/allotments/expenditures/revenue in one flat table with YYYYMMDD text dates
- **Sensitivity**: Confidential (vendor TINs, bank routing)

### DCR-FIN-02: GrantTrack_Excel_Master
- **Type**: Excel workbook on shared drive | **Since**: 2009 | **Status**: Active — Secondary
- **Domain**: Federal and private grant lifecycle — applications, awards, compliance, match tracking, reimbursements
- **Key tables**: Grant applications, active awards, compliance deadlines, match fund tracking, reimbursement requests
- **Quality issues**: Single point of failure (3 analysts); no version control; circular references in formulas; 2–5% reconciliation gap vs. SGF; raw Excel export carries pivoted fiscal-year columns, mixed date formats, comma-separated contributor names, and pipe-delimited contact info in single fields
- **Sensitivity**: Internal

### DCR-AST-01: InfraTrak Lifecycle
- **Type**: EAM SaaS | **Since**: 2020 (Phase 1) | **Status**: Partially Implemented
- **Domain**: Physical assets, maintenance, condition assessments — Regions 1 & 2 only (28 of 50 parks)
- **Key tables**: Assets, work orders, condition assessments (FCI 0–100), deferred maintenance backlog
- **Quality issues**: Regions 3 & 4 not onboarded (paper processes); ~40% undercount of statewide deferred maintenance; inconsistent new asset registration
- **Sensitivity**: Internal

### DCR-LES-01: RangerShield CAD/RMS
- **Type**: On-premise, air-gapped | **Since**: 2014 (RMS), 2017 (CAD) | **Status**: Active — Mandated (CJIS)
- **Domain**: Incident reports, citations, dispatch, use of force, officer activity
- **Key tables**: Incidents, citations, dispatch logs, use of force reports, officer activity logs, officer roster
- **Quality issues**: Complete air-gap from all other systems; locations as narrative text (not coordinates); manual statistical summaries with 2–4 week lag
- **Sensitivity**: Restricted — Statutory (CJIS)

### DCR-GEO-01: GeoParks Enterprise
- **Type**: ArcGIS geospatial server | **Since**: 2008 | **Status**: Active — Primary
- **Domain**: Legal boundaries, infrastructure, natural resources, cultural resources, recreational features
- **Key tables**: Legal boundaries, infrastructure features (trails, roads, buildings), natural resource layers, cultural resources (restricted), recreational features, parks master dimension
- **Quality issues**: Underground utility positional errors (5+ meters); 1–3 year update lag on some layers; 2-person team for entire agency
- **Sensitivity**: Mixed (cultural resource layers are Restricted — Statutory)

### DCR-NRM-01: BioSurvey_Legacy
- **Type**: Microsoft Access database | **Since**: 1993 | **Status**: Active — Secondary
- **Domain**: Ecological surveys, invasive species, endangered species monitoring, water quality
- **Key tables**: Flora/fauna surveys, invasive species, endangered species monitoring, water quality testing, species codes, survey sites
- **Quality issues**: Three water quality protocol eras (pre-2005, 2005–2018, 2018+); no GPS before 2011; approaching 2 GB Access limit; single-person dependency; mixed-entity observation table (flora/fauna/water quality in one table); E. coli counts stored as text (">2000", "TNTC"); comma-separated alternate species names
- **Sensitivity**: Mixed (endangered species locations are Restricted — Statutory)

### DCR-HCM-01: PeopleFirst HR
- **Type**: Statewide cloud ERP | **Since**: 2011 | **Status**: Active — Mandated
- **Domain**: Positions, employees, payroll, benefits, seasonal workforce
- **Key tables**: Positions, employees, payroll, benefits, leave balances, seasonal workforce
- **Quality issues**: Duty station at org-unit level only (not park-specific); seasonal hiring lag; no specialized certification tracking
- **Sensitivity**: Confidential (SSN, salary, medical leave)

### DCR-VUM-01: TrafficCount_IoT
- **Type**: IoT sensors + vendor cloud | **Since**: 2024 (pilot) | **Status**: Pilot
- **Domain**: Automated visitor counting at 8 park entrances and 12 trailheads (~15% of parks)
- **Key tables**: Vehicle counts, pedestrian/cyclist counts, sensor locations, derived visitor metrics
- **Quality issues**: 85% of parks have no sensors; vehicle occupancy multiplier (2.7) unvalidated since 2019; counts staff/contractor vehicles; no data portability clause in vendor contract
- **Sensitivity**: Public

## Cross-System Patterns

- **Identifier fragmentation**: GeoParks, VistaReserve, and InfraTrak each use different IDs for overlapping physical assets. Crosswalk stale since 2022.
- **Regional adoption divide**: Regions 1–2 digital, Regions 3–4 paper-based. Statewide reports systematically understate rural operations.
- **Financial-to-operational gap**: SGF tracks spending by object code but cannot attribute costs to specific assets. Manual reconciliation required.
- **Air-gapped law enforcement**: Permanent constraint. All cross-domain LE data use requires manual extraction and sanitization.
