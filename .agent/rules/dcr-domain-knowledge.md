---
activation: model_decision
description: Domain context about DCR park operations, revenue cycles, asset management, and organizational structure. Use when making schema or data generation decisions that require understanding the business.
---

# DCR Domain Knowledge

## Agency Profile

The Department of Conservation and Recreation manages 50 park units across 4 administrative regions. Park types include State Parks, State Recreation Areas, State Natural Reserves, State Historic Parks, and State Beaches, spanning approximately 285,000 acres. Annual visitation exceeds 18 million. The workforce includes ~420 FTE staff, ~600 seasonal employees, and ~4,200 active volunteers.

## Regional Structure

- **Region 1** (urban-proximate, flagship parks): Highest visitation, most digital infrastructure, best data system adoption
- **Region 2** (suburban/mixed): Moderate visitation, good adoption but with connectivity gaps in canyon parks
- **Region 3** (rural): Lower visitation, paper-based processes dominate, long-tenured staff
- **Region 4** (remote): Lowest visitation, least digital infrastructure, institutional knowledge held by individuals

Regions 1 and 2 have InfraTrak deployed. Regions 3 and 4 do not. This divide is the most frequently cited data challenge in agency leadership discussions.

## Funding Model

DCR operates under hybrid funding: enterprise fund revenues (camping/recreation fees), declining general fund appropriations, federal grants (LWCF, FEMA, Recreational Trails Program), and concessionaire franchise fees. The enterprise fund is the fastest-growing revenue source; general fund appropriations have declined in real terms over the past decade.

## Seasonal Patterns

- **Peak season**: Memorial Day through Labor Day (late May–early September)
- **Shoulder season**: April–May, September–October
- **Off-season**: November–March (reduced staffing, many campgrounds closed)
- **Seasonal hiring**: Recruitment January–March, onboarding April, separation October
- **Fiscal year**: July 1 – June 30 (state government fiscal year)

## Key Identifier Fragmentation

Three systems maintain independent identifiers for overlapping physical assets:

| System | Identifier | Format Example | Status |
|---|---|---|---|
| GeoParks (DCR-GEO-01) | GIS Feature ID | `GEO-F-00247` | Oldest, most stable |
| VistaReserve (DCR-REV-01) | Inventory Asset ID | `VR-CAMP-1042` | Assigned 2021, new scheme |
| InfraTrak (DCR-AST-01) | Asset Tag | `IT-BLD-R1-0089` | Assigned 2020, Regions 1-2 only |

A crosswalk table was created in 2021 but has not been maintained since 2022. Approximately 20% of mappings are known to be stale or incomplete.

## The "Data Cliff" at March 2021

The VistaReserve migration in March 2021 created a hard boundary in reservation and revenue data. Pre-migration data lives in LegacyRes_Archive with incompatible identifiers and a different data model. Longitudinal analysis spanning this boundary requires manual cross-referencing via a partial, unverified crosswalk spreadsheet.

## Air-Gapped Law Enforcement

RangerShield (DCR-LES-01) is completely air-gapped per FBI CJIS Security Policy. No electronic data feed exists between RangerShield and any other system. All cross-domain use of law enforcement data requires manual extraction, aggregation, and sanitization. This is a permanent architectural constraint.

## Known Single Points of Failure

- **BioSurvey_Legacy**: One person (Chief Biologist) understands the schema, codes, and data entry conventions. The database runs on MS Access approaching its 2 GB limit.
- **GrantTrack_Excel_Master**: Three budget analysts maintain the workbook. Formula dependencies include circular references and hardcoded year values. Two replacement attempts have failed.
