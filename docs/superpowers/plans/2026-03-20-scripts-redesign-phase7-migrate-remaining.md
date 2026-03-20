# Phase 7: Migrate Remaining Scripts — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the remaining flat scripts from `scripts/` root into their respective sub-packages (`governance/`, `cdm/`, `export/`, `inspect/`), update all references, and clean up the scripts root so only `__init__.py` remains.

**Architecture:** Straightforward file moves with import updates. Each script becomes a module inside a new package. Existing functionality is preserved exactly — no behavior changes.

**Tech Stack:** Python 3.10+, existing dependencies only

**Spec:** `docs/superpowers/specs/2026-03-20-scripts-redesign-design.md` (section: "Phase 7: Remaining Scripts")

**Depends on:** Phase 5 (`reviewer/` — the last scripts that reference `check_model.py` directly)

---

### Task 1: Create `governance/` package — migrate `parse_standards.py` and `dbt_score_rules.py`

**Files:**
- Create: `scripts/governance/__init__.py`
- Create: `scripts/governance/parse_standards.py` (from `scripts/parse_standards.py`)
- Create: `scripts/governance/dbt_score_rules.py` (from `scripts/dbt_score_rules.py`)

- [ ] **Step 1: Create package and copy files**

```bash
mkdir -p scripts/governance
```

Copy `scripts/parse_standards.py` → `scripts/governance/parse_standards.py`.
Copy `scripts/dbt_score_rules.py` → `scripts/governance/dbt_score_rules.py`.
Create empty `scripts/governance/__init__.py`.

Update any internal imports if needed (these scripts are standalone, so likely no changes needed).

- [ ] **Step 2: Verify imports work**

Run: `source .venv/Scripts/activate && python -c "from scripts.governance.parse_standards import *; print('OK')"`
Run: `source .venv/Scripts/activate && python -c "from scripts.governance.dbt_score_rules import *; print('OK')"`
Expected: Both print "OK".

- [ ] **Step 3: Commit**

```bash
git add scripts/governance/
git commit -m "feat(governance): migrate parse_standards.py and dbt_score_rules.py"
```

---

### Task 2: Create `cdm/` package — migrate `search_cdm.py`

**Files:**
- Create: `scripts/cdm/__init__.py`
- Create: `scripts/cdm/search.py` (from `scripts/search_cdm.py`)

- [ ] **Step 1: Create package and copy file**

Copy `scripts/search_cdm.py` → `scripts/cdm/search.py`.
Create empty `scripts/cdm/__init__.py`.

Add `__main__.py` if desired for `python -m scripts.cdm` usage:
```python
# scripts/cdm/__main__.py
from scripts.cdm.search import main
import sys
sys.exit(main())
```

- [ ] **Step 2: Verify import**

Run: `source .venv/Scripts/activate && python -c "from scripts.cdm.search import *; print('OK')"`
Expected: "OK"

- [ ] **Step 3: Commit**

```bash
git add scripts/cdm/
git commit -m "feat(cdm): migrate search_cdm.py to cdm/search.py"
```

---

### Task 3: Create `export/` package — migrate `export_mart_data.py`

**Files:**
- Create: `scripts/export/__init__.py`
- Create: `scripts/export/cli.py` (from `scripts/export_mart_data.py`)

- [ ] **Step 1: Create package and copy file**

Copy `scripts/export_mart_data.py` → `scripts/export/cli.py`.
Create empty `scripts/export/__init__.py`.

Add `__main__.py`:
```python
# scripts/export/__main__.py
from scripts.export.cli import main
import sys
sys.exit(main())
```

- [ ] **Step 2: Verify import**

Run: `source .venv/Scripts/activate && python -c "from scripts.export.cli import *; print('OK')"`
Expected: "OK"

- [ ] **Step 3: Commit**

```bash
git add scripts/export/
git commit -m "feat(export): migrate export_mart_data.py to export/cli.py"
```

---

### Task 4: Create `inspect/` package — migrate `inspect_source.py`

**Files:**
- Create: `scripts/inspect/__init__.py`
- Create: `scripts/inspect/cli.py` (from `scripts/inspect_source.py`)

- [ ] **Step 1: Create package and copy file**

Copy `scripts/inspect_source.py` → `scripts/inspect/cli.py`.
Create empty `scripts/inspect/__init__.py`.

Add `__main__.py`:
```python
# scripts/inspect/__main__.py
from scripts.inspect.cli import main
import sys
sys.exit(main())
```

- [ ] **Step 2: Verify import**

Run: `source .venv/Scripts/activate && python -c "from scripts.inspect.cli import *; print('OK')"`
Expected: "OK"

- [ ] **Step 3: Commit**

```bash
git add scripts/inspect/
git commit -m "feat(inspect): migrate inspect_source.py to inspect/cli.py"
```

---

### Task 5: Update all external references and remove flat scripts

**Files:**
- Modify: `CLAUDE.md` — update script paths in Operating Principles and any references
- Modify: `.agent/rules/dbt-project-governance.md` — update any script references
- Delete: `scripts/check_model.py`
- Delete: `scripts/review_model.py`
- Delete: `scripts/summarize_reviews.py`
- Delete: `scripts/parse_standards.py`
- Delete: `scripts/dbt_score_rules.py`
- Delete: `scripts/search_cdm.py`
- Delete: `scripts/export_mart_data.py`
- Delete: `scripts/inspect_source.py`

- [ ] **Step 1: Search for all references to old script paths**

Run grep for each old script path across the project:
- `check_model.py`
- `review_model.py`
- `summarize_reviews.py`
- `parse_standards.py`
- `dbt_score_rules.py`
- `search_cdm.py`
- `export_mart_data.py`
- `inspect_source.py`

Update CLAUDE.md Operating Principles:
- Rule 10: `python scripts/review_model.py` → `python -m scripts.reviewer`
- Rule 25: `python scripts/inspect_source.py` → `python -m scripts.inspect`

- [ ] **Step 2: Delete old flat scripts**

```bash
rm scripts/check_model.py scripts/review_model.py scripts/summarize_reviews.py
rm scripts/parse_standards.py scripts/dbt_score_rules.py scripts/search_cdm.py
rm scripts/export_mart_data.py scripts/inspect_source.py
```

- [ ] **Step 3: Verify no broken imports**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/ -v --timeout=60`
Expected: All tests pass.

- [ ] **Step 4: Verify the scripts root is clean**

Run: `ls scripts/*.py`
Expected: Only `scripts/__init__.py` remains (or nothing if there was no `__init__.py` at root).

- [ ] **Step 5: Commit**

```bash
git add -A scripts/ CLAUDE.md .agent/
git commit -m "refactor: remove flat scripts from scripts/ root, update all references"
```

---

### Task 6: Final verification — full test suite

- [ ] **Step 1: Run all tests**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/ -v --timeout=120`
Expected: All tests pass.

- [ ] **Step 2: Verify all CLI entry points**

```bash
source .venv/Scripts/activate
python -m scripts.grain --help
python -m scripts.llm_context --help
python -m scripts.scaffold --help
python -m scripts.preflight --help
python -m scripts.reviewer --help
python -m scripts.profiler.cli --help
python -m scripts.cdm --help 2>/dev/null || echo "no __main__"
python -m scripts.export --help 2>/dev/null || echo "no __main__"
python -m scripts.inspect --help 2>/dev/null || echo "no __main__"
```
Expected: All print help text.

- [ ] **Step 3: Commit (if any fixes needed)**

```bash
git add -A
git commit -m "fix: post-migration cleanup"
```
