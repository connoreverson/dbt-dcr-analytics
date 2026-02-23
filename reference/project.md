# Project Context: DCR DuckDB Source Data Generator

## What this project does

This project generates realistic synthetic source-system databases for the Department of Conservation and Recreation (DCR). DCR operates 50 park units across 4 regions with 10 distinct operational data systems — from a modern SaaS reservation platform to a 30-year-old Microsoft Access ecological database.

Each system gets its own DuckDB database file populated with fake data that mirrors the structure, volume, and documented quality characteristics of the real systems.

## Why it exists

These databases serve as the upstream source layer for a dbt (data build tool) project that will model, transform, and unify DCR data for analytics. This project is strictly the "source generation" layer — it produces the raw material that dbt consumes. The dbt project is separate and is not built here.

The synthetic data approach avoids the need for access to real (often sensitive) government data while preserving the structural complexity, relational patterns, and known quality issues that make DCR's data landscape challenging to work with.

## Who consumes the output

- **dbt developers** will define sources pointing to these .duckdb files and build staging, intermediate, and mart models on top of them.
- **Data analysts** testing queries or dashboards against realistic data volumes.
- **Data governance teams** validating schema documentation and data dictionary completeness.

## Key design decisions

1. **One database per system** — mirrors DCR's real architecture where systems are operationally disconnected. No cross-database joins enforced at the source layer.
2. **Relational integrity within, not between** — FK constraints exist within each system's database. Crosswalk tables document inter-system mappings but do not enforce them.
3. **Intentional quality issues** — the Data Inventory documents specific problems (duplicates, stale crosswalks, regional gaps). The synthetic data reproduces these intentionally so that dbt models can be built to handle them.
4. **Deterministic generation** — seeded random data so regeneration produces identical output. This supports reproducible dbt testing.

## Source Fidelity Design

1. **Normalization varies by system maturity.** Sources simulate the normalization level appropriate to their real-world technology. SaaS platforms (VistaReserve, InfraTrak) export relatively clean relational data with occasional JSON metadata fields. Legacy databases (BioSurvey Access, LegacyRes flat files) export data with 1NF violations — multi-valued attributes in single columns, mixed-entity tables, and type inconsistencies. Spreadsheet-based systems (GrantTrack) export with the most structural issues — pivoted layouts, mixed formats, and no referential integrity. The mainframe system (SGF) exports with COBOL-era conventions — fixed-width date formats, packed text fields, and mixed-entity activity logs.

2. **This variation is intentional.** The downstream dbt project's staging and base model layers need to exercise the full range of transformations described in the project standards: parsing composite values (SQL-STG-12), recasting types (SQL-STG-10), standardizing formats (SQL-STG-11), splitting mixed-entity tables (SQL-BASE-07), and handling complex deduplication (SQL-BASE-09). Sources that are pre-normalized would bypass these patterns.

3. **The messiest sources are the ones documented as fragile.** GrantTrack, BioSurvey, and LegacyRes are explicitly described in the Data Inventory as having single-person dependencies, no version control, and platform limitations. Their structural messiness in the synthetic data reflects this.

## Relationship to other documents

- **Business Artifacts/DCR Data Inventory.md** — the authoritative source for system descriptions. Schema designs are inferred from this document.
- **Technical References/** — Google Antigravity documentation and example patterns that informed the project structure.
- **context/data-inventory-summary.md** — condensed quick-reference version of the inventory.
