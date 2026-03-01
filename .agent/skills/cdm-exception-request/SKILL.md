---
name: cdm-exception-request
description: Use when an integration model fails CDM validation (SQL-INT-03 or
  SQL-INT-05) and no standard CDM entity provides both semantic correctness and
  adequate column coverage. Guides the analyst through evaluating candidate
  entities, documenting the exception, and registering a custom entity.
user-invocable: false
metadata:
  author: dcr-analytics
---

# CDM Entity Exception Request

## When to Use
- check_model.py reports SQL-INT-03 or SQL-INT-05 failures
- Manual review determines no standard CDM entity is semantically appropriate
- Do NOT use this to skip CDM mapping — exhaust standard entities first

## Steps

1. **Identify the failing model and current CDM mapping.**
   Run: `python scripts/check_model.py --select <model_name>`
   Note which CDM entity is mapped in `seeds/cdm_crosswalk.csv`.

2. **Evaluate candidate CDM entities.**
   For each candidate, assess:
   - Column coverage (how many model columns map to entity columns?)
   - Semantic fit (does the entity's definition match the business concept?)
   - Unmappable attributes (which model columns have no semantic equivalent?)
   Document findings using the format in `reference/CDM_EXCEPTION_int_parks.md`
   sections 2a–2d.

3. **Draft the exception request.**
   Create `reference/CDM_EXCEPTION_<model>.md` following the template:
   - Section 1: Business entity definition, grain, source systems
   - Section 2: Candidate entities evaluated (with verdicts)
   - Section 3: Conclusion — why no standard entity works
   - Section 4: Proposed custom entity (name, extends, columns with CDM lineage)
   - Section 5: Implementation path
   - Section 6: Governance note

4. **Register the custom entity.**
   - Add column definitions to `seeds/cdm_catalogs/` (either in the relevant
     existing catalog CSV or a new `column_catalog_dcr_extensions.csv`)
   - Update `seeds/cdm_crosswalk.csv` to map the integration model to the
     custom entity
   - Update `models/integration/_models.yml` with `meta: cdm_entity:` and
     `meta: cdm_entity_rationale:` referencing the exception document

5. **Re-run validation.**
   `python scripts/check_model.py --select <model_name>`
   SQL-INT-03 and SQL-INT-05 should now pass against the custom entity.

## Acceptance Criteria
- Exception document exists in `reference/` and follows the template
- Custom entity is registered in seeds and resolvable by check_model.py
- Integration model passes all check_model.py checks
