---
description: Build Marts
---

# 04: Build Marts

// turbo

## Prerequisites
- Workflow 03 complete (integration models passing)

## Steps
1. Run skill `using-dbt-for-analytics-engineering` for marts layer
   - Selector: `models/marts`
2. Run `check_model.py` per-model for each mart model
   - Command: `python scripts/check_model.py --select <model_name>`
3. Gate: all mart models pass check_model.py
