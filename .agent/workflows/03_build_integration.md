---
description: Build Integration
---

# 03: Build Integration

// turbo-all

## Prerequisites
- Workflow 02 complete (staging models passing)

## Steps
1. Run skill `using-dbt-for-analytics-engineering` for integration layer
   - Selector: `models/integration`
2. Run `check_model.py` to evaluate the integration layer
   - Command: `python scripts/check_model.py --select models/integration`
   - Do NOT use a PowerShell `foreach` loop to run this per-file. The script accepts directory selectors natively.
   - This replaces the 3-tool sequence for iterative checks
     (check_model.py runs sqlfluff, dbt build, dbt-score, and
     dbt-project-evaluator internally)
3. If CDM validation fails (SQL-INT-03 or SQL-INT-05):
   - Run skill `cdm-exception-request` (see new skill below)
4. Gate: all integration models pass check_model.py