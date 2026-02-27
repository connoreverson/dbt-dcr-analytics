---
activation: on_demand
description: Python and SQL coding conventions for the DCR data generation project. Use when writing Python scripts or making general code convention decisions.
---

# Coding Standards

## Python Conventions

- Target Python 3.10+. Use type hints on all public method signatures.
- Follow PEP 8 with a 100-character line limit for docstrings and comments.
- Each system generator lives in `src/generators/` and is named `dcr_[domain]_[seq]_[systemname].py` (e.g., `dcr_rev_01_vistareserve.py`).
- All generators inherit from `BaseSystemGenerator` in `src/generators/base.py`.
- Use `mimesis` for fake data generation. Do not use `faker` or hand-rolled random strings.
- Seed all random generation deterministically. Each system's seed is derived from its system ID (e.g., hash of `DCR-REV-01`).
- Avoid bare `except` clauses. Catch specific exceptions and log them.
- Use `logging` module, not `print()`, for all status output.

## SQL Conventions

- Schema DDL files live in `schemas/` and are named `dcr_[domain]_[seq].sql` (e.g., `dcr_rev_01.sql`).
- Every `CREATE TABLE` statement must include a `COMMENT ON TABLE` and `COMMENT ON COLUMN` for each column.
- Use `BIGINT` for surrogate primary keys. Use `VARCHAR` for codes and identifiers. Use `DATE` or `TIMESTAMP` for temporal fields. Use `DECIMAL(12,2)` for monetary amounts.
- Primary keys are always named `[table_name]_id` unless the domain demands otherwise (e.g., `asset_tag`).
- Foreign key constraints use the naming pattern `fk_[child_table]_[parent_table]`.
- Check constraints use the naming pattern `chk_[table]_[column_or_rule]`.

## File Organization

- Generated `.duckdb` files go in `output/`, named `dcr_[domain]_[seq]_[systemname].duckdb`.
- Do not commit `.duckdb` files to version control. They are generated artifacts.
- Keep `Business Artifacts/` and `Technical References/` directories read-only. Never modify upstream documentation.
- All temporary files, scratchpad test scripts (`test_*.py`), query logs, and standalone testing databases must be placed in a `tmp/` directory, never at the project root.
- Clean up any generated `tmp/` files or stack trace logs (`err.txt`, `out.log`) once the issue being debugged is resolved.

## Error Handling

- Validate row counts after insertion. If actual count diverges more than 10% from target, log a warning.
- Wrap each system's generation in a transaction. Rollback on any error; do not produce partial databases.
- Log generation statistics (table name, row count, elapsed time) for every table.
