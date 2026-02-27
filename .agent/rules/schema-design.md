---
activation: on_demand
description: Relational schema design constraints and patterns for DCR DuckDB databases. Use when designing schemas or writing DDL.
---

# Schema Design Rules

## Primary Keys

- Every table has a single-column surrogate primary key of type `BIGINT`, auto-generated via `GENERATED ALWAYS AS IDENTITY`.
- Name the PK column `[table_name]_id` unless the business domain uses a specific identifier (e.g., `asset_tag` in InfraTrak, `badge_number` in RangerShield). In those cases, include both the surrogate PK and the business identifier as a unique constraint.

## Foreign Keys

- Define explicit `FOREIGN KEY` constraints for all parent-child relationships within a system.
- Name FK constraints: `fk_[child_table]_[parent_table]`.
- All FK columns must be `NOT NULL` unless the relationship is genuinely optional (document the business reason in a column comment).
- Do not create cross-database FK constraints. Systems are independent.

## Check Constraints

- Use check constraints for enumerated value domains (status codes, type codes, category codes).
- Name check constraints: `chk_[table]_[description]`.
- Examples:
  - `CHECK (reservation_status IN ('confirmed', 'cancelled', 'no_show', 'completed'))`
  - `CHECK (check_out_date > check_in_date)`
  - `CHECK (facility_condition_index BETWEEN 0 AND 100)`

## Data Types

| Domain | DuckDB Type | Notes |
|---|---|---|
| Surrogate keys | `BIGINT` | Auto-generated identity |
| Business identifiers | `VARCHAR` | Asset tags, badge numbers, species codes |
| Names, descriptions | `VARCHAR` | No artificial length limits in DuckDB |
| Monetary amounts | `DECIMAL(12,2)` | Two decimal places for currency |
| Dates | `DATE` | For calendar dates without time |
| Timestamps | `TIMESTAMP` | For events requiring time-of-day precision |
| Counts, quantities | `INTEGER` | Non-negative where applicable |
| Rates, percentages | `DECIMAL(5,2)` | 0.00–100.00 range |
| Boolean flags | `BOOLEAN` | For binary attributes |
| Geographic coords | `DOUBLE` | Latitude and longitude as separate columns |
| Narrative text | `VARCHAR` | Location descriptions, memo fields |

## Table Comments

Every table must have a `COMMENT ON TABLE` statement explaining:
1. What business entity or process the table represents
2. Which DCR system it belongs to (by system ID)
3. The approximate expected row count

Every column must have a `COMMENT ON COLUMN` statement explaining:
1. What the column represents in business terms
2. Valid value ranges or enumerated values
3. Whether NULLs are expected and why

## Crosswalk Tables

Crosswalk tables document identifier mappings between systems. They follow a specific pattern:

```sql
CREATE TABLE crosswalk_[source]_to_[target] (
    crosswalk_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    [source_system]_id VARCHAR NOT NULL,
    [target_system]_id VARCHAR,
    last_verified_date DATE,
    is_current BOOLEAN DEFAULT true,
    crosswalk_source VARCHAR
);
```

- `is_current` flags whether the mapping is believed to be accurate.
- `crosswalk_source` documents how the mapping was established (e.g., `manual_2022`, `field_inventory`, `automated_load`).
- Target ID may be NULL if the mapping is incomplete or unverified.

## Schema per System

Each system's DDL lives in a single `.sql` file in `schemas/`. The file should:
1. Drop existing tables if they exist (for idempotent re-runs)
2. Create all tables with constraints
3. Add all comments
4. Be executable as a standalone script against an empty DuckDB database

## Intentional Normalization Exceptions

The following systems have tables that intentionally violate normal form conventions to simulate realistic source data characteristics. These exceptions are documented in the Data Inventory and must not be "fixed" during schema design.

| System | Table | Violation | Rationale |
|--------|-------|-----------|-----------|
| DCR-FIN-02 | `award_budget_by_fiscal_year` | 1NF: Repeating fiscal year column groups | Simulates Excel pivot-table export |
| DCR-FIN-02 | `match_fund_tracking.contributors` | 1NF: Comma-separated values | Simulates Excel merged cell entry |
| DCR-FIN-02 | `grant_applications.primary_contact` | 1NF: Pipe-delimited composite value | Simulates Excel merged cell entry |
| DCR-FIN-02 | `compliance_deadlines.due_date/submission_date` | Type: VARCHAR storing mixed date formats | Simulates inconsistent manual Excel entry |
| DCR-NRM-01 | `field_observations_raw` | Mixed entities in one table | Simulates Access single-form data entry |
| DCR-NRM-01 | `species_codes.alternate_names` | 1NF: Comma-separated values | Simulates Access convenience field |
| DCR-NRM-01 | `field_observations_raw.ecoli_count` | Type: VARCHAR storing mixed numeric/text | Simulates lab result threshold notation |
| DCR-REV-02 | `legacy_reservations` dates | Type: VARCHAR storing era-dependent date formats | Simulates multi-era flat-file exports |
| DCR-REV-02 | `legacy_reservations.guest_info` | 1NF: Pipe-delimited composite value | Simulates flat-file packed fields |
| DCR-REV-02 | `legacy_fee_schedule_wide` | 1NF: Repeating season/rate column groups | Simulates exported fee schedule |
| DCR-FIN-01 | `general_ledger.batch_detail_text` | 1NF: Pipe-delimited sub-records | Simulates mainframe packed memo field |
| DCR-FIN-01 | `budget_activity_log` | Mixed entities in one table | Simulates mainframe consolidated export |
| DCR-FIN-01 | `budget_activity_log.effective_date` | Type: VARCHAR storing YYYYMMDD | Simulates mainframe fixed-width export |
| DCR-REV-01 | `reservations.booking_metadata` | Semi-structured: JSON in VARCHAR | Simulates SaaS API metadata export |
| DCR-REV-01 | `customer_profiles.preferences_json` | Semi-structured: JSON in VARCHAR | Simulates SaaS profile data export |

For these tables:
- PK constraints may be absent if the source system has no concept of a primary key (Excel exports, flat-file fee schedules)
- FK constraints may be absent even when a logical relationship exists (the source system doesn't enforce it)
- CHECK constraints on enumerated values should still be used where the source system would enforce them (e.g., Access lookup fields), but omitted where it wouldn't (Excel free-text cells)
- `COMMENT ON TABLE` and `COMMENT ON COLUMN` statements are still required and should describe both the business meaning and the known data quality issues
