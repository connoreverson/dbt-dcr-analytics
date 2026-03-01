---
description: Setup dbt Environment
---

# 01: Setup dbt Environment

// turbo

## Steps
1. Activate virtual environment per CLAUDE.md Operating Principle 10
2. Run `pip install -r requirements.txt`
3. Run `dbt deps`
4. Run `dbt seed`
5. Gate: `dbt debug` exits clean
