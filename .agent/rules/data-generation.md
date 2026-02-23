---
activation: always_on
description: Patterns and constraints for generating realistic fake data with mimesis and DuckDB. Applied during all data generation work.
---

# Data Generation Rules

## Mimesis Configuration

- Use `mimesis.Generic` with locale `en` as the primary provider.
- Initialize with a deterministic seed derived from the system ID: `seed = int(hashlib.md5(system_id.encode()).hexdigest()[:8], 16)`.
- For domain-specific values not covered by mimesis (park names, species codes, object codes), use curated value lists in `src/utils/data_profiles.py` and select from them using the seeded random instance.

## Volume Targets

Target row counts are calibrated for large datasets (10,000s) suitable for dbt development and analytics testing:

| Table Type | Target Range | Examples |
|---|---|---|
| Dimension / Reference | 20–500 rows | parks, species codes, chart of accounts, officer roster |
| Operational / Transactional | 1,000–20,000 rows | reservations, work orders, payroll, dispatch logs |
| Historical / Archive | 10,000–50,000 rows | legacy reservations, historical revenue summaries |
| Derived / Aggregated | 500–3,000 rows | daily revenue batches, derived visitor metrics |

## Relational Integrity

- **Dimension-first generation**: Always create parent/dimension tables before child/fact tables.
- **FK population by selection**: When populating a foreign key column, select a random valid value from the already-generated parent table. Never generate FK values independently of the parent.
- **No orphans**: Every child record must reference an existing parent. Post-generation validation must confirm zero orphaned FK references.
- **Crosswalk tables are informational**: Crosswalk tables linking identifiers across systems do not have enforced FK constraints to the other system's database. They document plausible mappings only.

## Simulating Data Quality Issues

The Data Inventory documents specific quality problems. Reproduce these intentionally:

- **VistaReserve customer duplicates**: Generate 18–22% duplicate customer profiles (same name/email, different customer_id) to simulate the known duplicate proliferation.
- **Stale crosswalks**: In crosswalk tables, mark ~20% of records as `is_current = false` with `last_verified_date` before 2023.
- **InfraTrak regional gaps**: Only generate assets for park units in Regions 1 and 2 (28 of 50 parks). Regions 3 and 4 should have zero asset records.
- **BioSurvey GPS gaps**: For survey records dated before 2011, set `gps_latitude` and `gps_longitude` to NULL. Records from 2011 onward should have coordinates.
- **BioSurvey protocol eras**: Water quality test records should use one of three `test_protocol` values depending on the test date: `pre_2005` (before 2005), `revised_2005_2018` (2005–2018), `epa_current` (2018+).
- **SGF coding inconsistency**: For the same type of expenditure, vary the `object_code` used across different regions to simulate the documented coding discipline variance.
- **GrantTrack reconciliation gap**: Grant expenditure totals should diverge from corresponding SGF totals by 2–5% to simulate timing differences.

## Generating Denormalized and Messy Data

For source systems documented as having structural messiness (see schema-design.md "Intentional Normalization Exceptions"), the following generation patterns apply:

**Mixed-format monetary values (GrantTrack, LegacyRes)**:
Use weighted random selection: ~70% clean decimal ("12500.00"), ~15% with currency formatting ("$12,500.00"), ~10% rounded integer ("12500"), ~5% non-numeric placeholder ("TBD", "pending", blank). Tie the format to the record's age — older records are more likely to have inconsistent formatting.

**Mixed-format date strings (GrantTrack, LegacyRes, SGF)**:
Use era-correlated format selection. GrantTrack: ISO for recent records, US-format for mid-era, natural-language for oldest. LegacyRes: format determined by `data_format_source` value. SGF: always YYYYMMDD fixed-width.

**Comma-separated multi-values (GrantTrack, BioSurvey)**:
Generate 1–4 values per cell, joined with ", " (comma-space). Ensure ~10% of records have only one value (no comma) to test parsing edge cases.

**Pipe-delimited composite fields (GrantTrack, LegacyRes, SGF)**:
Generate composite values with the documented delimiter. Include ~5-10% of records with missing segments or inconsistent delimiter usage to simulate real-world data entry errors.

**JSON metadata (VistaReserve)**:
Generate valid JSON for the majority of records using `json.dumps()`. For booking_metadata specifically, introduce ~5% malformed JSON (truncated strings, missing braces) to simulate export corruption. For preferences_json, generate 100% valid JSON (this is a well-implemented SaaS feature).

**Mixed-entity tables (BioSurvey, SGF)**:
Generate all entity types into the single table with the documented type discriminator. For columns irrelevant to a given entity type, use NULL for ~95% of records and non-NULL "leakage" values for ~5% to simulate data entry errors.

**Tables without primary keys (GrantTrack award_budget_by_fiscal_year, LegacyRes legacy_fee_schedule_wide)**:
Do not add PK constraints. Generate ~3% duplicate or near-duplicate rows to simulate copy-paste errors. Ensure the downstream dbt team must handle deduplication in a base model.

## Temporal Realism

Each system has a documented operational period. Respect these boundaries:

| System | Valid Date Range |
|---|---|
| DCR-REV-01 VistaReserve | 2021-03-01 → present |
| DCR-REV-02 LegacyRes_Archive | 2005-01-01 → 2021-02-28 |
| DCR-FIN-01 StateGov Financials | 1994-01-01 → present (generate 2020+) |
| DCR-FIN-02 GrantTrack | 2009-01-01 → present |
| DCR-AST-01 InfraTrak | 2020-01-01 → present |
| DCR-LES-01 RangerShield | 2014-01-01 → present (CAD from 2017+) |
| DCR-GEO-01 GeoParks | 2008-01-01 → present |
| DCR-NRM-01 BioSurvey | 1993-01-01 → present |
| DCR-HCM-01 PeopleFirst | 2011-01-01 → present |
| DCR-VUM-01 TrafficCount | 2024-01-01 → present |

Within each system, ensure logical date ordering: parent records precede children, check-out follows check-in, payment follows invoice, etc.
