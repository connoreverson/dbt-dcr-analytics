# Plan: Prepare DCR Analytics for GitHub Publication

## Context

The DCR Analytics dbt project is a comprehensive, locally-hosted reference project for dbt with 10 source systems, 89 SQL models across 3 layers, and 103 governance rules. It needs to be cleaned up, documented, and committed before publishing to GitHub. The user wants it to serve as an excellent reference project for dbt that runs entirely locally.

Current state: 24 modified files uncommitted, 1 untracked file, known broken mart models, a stale feature branch/worktree, no LICENSE file, and some agent scaffolding to trim.

**This plan is designed to be executed by Claude Sonnet or Claude Haiku.** Each step is self-contained with explicit file paths and instructions.

---

## Execution Order Summary

Because Step 1 (git filter-repo) rewrites all commit hashes, the execution order is:

1. **Step 2** — Remove worktree, delete feature branch
2. **Step 12 (partial)** — Commit all 24 outstanding modified files in logical groups
3. **Step 1** — Run git filter-repo to purge VOICE_PROFILE from all history
4. **Step 3** — Fix broken marts, commit
5. **Steps 4-5** — Trim agent scaffolding, remove obsolete files, commit
6. **Steps 6-7** — Add LICENSE, expand .gitignore, commit
7. **Steps 8-9** — Write export script + local CI script, commit
8. **Steps 10-11** — Update README, CLAUDE.md, GEMINI.md, commit
9. **Step 13** — Final validation

---

## Step 1: Remove VOICE_PROFILE from git history entirely

The user wants `reference/VOICE_PROFILE_Connor.md` purged from all history, not just deleted.

```bash
# Use git filter-repo (preferred) or BFG Repo-Cleaner
# First, install git-filter-repo if not present:
pip install git-filter-repo

# Then rewrite history:
git filter-repo --invert-paths --path reference/VOICE_PROFILE_Connor.md --force
```

**Confirmed:** Repo is purely local, never pushed. Safe to rewrite all 55 commits. The worktree must be removed first (Step 2), so execute Step 2 before Step 1.

**Alternative if git-filter-repo is unavailable:**
```bash
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch reference/VOICE_PROFILE_Connor.md' \
  --prune-empty -- --all
```

Also remove the reference from `CLAUDE.md` (line mentioning VOICE_PROFILE_Connor.md in the Key References table and Writing Style section).

---

## Step 2: Close stale feature branch and worktree

The `feature/check-model-auto-checks` branch has 1 commit ahead of main (273ee41: "add 11 automated checks to check_model.py") but is 38 commits behind. The worktree at `worktrees/check-model-auto-checks` needs cleanup.

```bash
# Remove the worktree (may need git worktree prune on Windows)
git worktree remove worktrees/check-model-auto-checks
# If permission denied:
git worktree prune

# Delete the branch — do NOT cherry-pick
git branch -D feature/check-model-auto-checks
```

**Decision:** User confirmed: discard the branch. Do NOT cherry-pick. Just delete.

---

## Step 3: Fix broken mart models

### 3a. Fix `dim_reservation_inventory.sql`

**File:** `models/marts/revenue/dim_reservation_inventory.sql`
**Problem:** References `int_customer_assets.asset_type` which doesn't exist in `int_customer_assets` (that model only produces: `customer_assets_sk`, `customerasset_id`, `_parent_park_sk`, `name`).

**Fix approach:**
1. Run `dbt show --select int_customer_assets --limit 5` to confirm actual columns
2. Run `dbt show --select stg_vistareserve__inventory_assets --limit 5` to see what staging provides
3. Rewrite the model to pull `asset_type` and other asset detail columns from the staging model, and join `int_customer_assets` only for the surrogate key and park FK
4. Update `models/marts/revenue/_models.yml` contract columns to match

### 3b. Fix `fct_pos_transactions.sql`

**File:** `models/marts/revenue/fct_pos_transactions.sql`
**Problem:** Previously reported as referencing `transaction_amount` alias before definition. May already be fixed in uncommitted changes.

**Fix approach:**
1. Run `dbt show --select fct_pos_transactions --limit 1` to test
2. If it fails, inspect the alias ordering and fix
3. If it passes, no action needed

### 3c. Validate `fct_park_occupancy_daily_snapshot.sql`

**File:** `models/marts/revenue/fct_park_occupancy_daily_snapshot.sql` (new, untracked)
**Action:** Run `dbt build --select fct_park_occupancy_daily_snapshot` to validate it builds. Fix any issues. Note: `dim_date` exists at `models/marts/core/dim_date.sql`.

### 3d. Run full dbt build

After fixes:
```bash
source .venv/Scripts/activate
dbt build
```

Document any remaining failures. All models should build clean before publishing.

---

## Step 4: Remove/trim agent scaffolding files

### Files to DELETE:
- `.ai/prompts/dbt-model-reviewer.md` — Generic compliance audit template, not used in project workflow
- `.agent/rules/agent-autonomy.md` — Content duplicates CLAUDE.md operating principles #10 and #24

### Files to TRIM:
- **CLAUDE.md**: Remove references to:
  - `VOICE_PROFILE_Connor.md` (deleted in Step 1)
  - The "Writing Style" section at the bottom that references the voice profile
  - The `agent-autonomy.md` entry from the Rules table (deleted above)

- **GEMINI.md**: Same removals as CLAUDE.md, plus review for any personal/internal references

### Files to KEEP (no changes):
- All `.agent/rules/` (except agent-autonomy.md): project-specific governance
- All `.agent/skills/`: mix of generic dbt and project-specific (both valuable as reference)
- `.ai/prompts/dbt-implementer.md` and `spec-planner.md`: project-specific
- `.claude/agents/`: project-specific subagent definitions
- `.claude/settings.local.json`: project-specific tool allowlist
- `.gemini/settings.json` and `.geminiignore`: project-specific

---

## Step 5: Remove obsolete reference files

Review and remove reference docs that are no longer needed for the published state:

- **KEEP:** `reference/dbt_project_standards.md`, `reference/dbt_project_standards.json`, `reference/SPEC_vertical_slice_revenue.md`, `reference/data_dictionary.md`, `reference/data_inventory_summary.md`, `reference/architectural_review.md`, `reference/business_artifacts/*`, all `reference/CDM_EXCEPTION_*.md` files
- **KEEP:** `reference/plans/` — all plan files (user wants these in version control)
- **DELETE** (if it exists and is empty/obsolete): `reference/project.md`
- **DELETE:** `.claude/review-queue.md` — internal review tracking, not needed for publication

---

## Step 6: Add LICENSE file

Create `LICENSE` at repo root with MIT license text. Use the current year (2026) and the copyright holder name from `git log --format='%an' -1`.

---

## Step 7: Expand .gitignore

Add cross-platform editor and OS entries:

```gitignore
# Existing
target/
dbt_packages/
logs/
.venv/
tmp/
__pycache__/
*.pyc
worktrees/

# Editor files
*.swp
*.swo
*~
.vscode/
.idea/

# OS files
.DS_Store
Thumbs.db

# Python
*.egg-info/
dist/
build/

# Exported data
output/

# User config
.user.yml
```

Also check: is `.user.yml` currently tracked? If so, remove from tracking (`git rm --cached .user.yml`).

---

## Step 8: Write `scripts/export_mart_data.py`

Create a Python script that exports all mart model data for consumption.

**Location:** `scripts/export_mart_data.py`

**Behavior:**
1. Connect to `target/dcr_analytics.duckdb`
2. Query each mart model table (from `main` schema or `main_marts_*` schemas)
3. Export to CSV and/or Parquet in an `output/` directory
4. Print summary of rows exported per model
5. Support `--format csv|parquet|both` flag
6. Support `--select <model_name>` to export specific models

**Dependencies:** `duckdb` and `pandas` (both already in requirements.txt)

Add `output/` to `.gitignore`.

---

## Step 9: Write `scripts/ci_local.sh`

Create a local CI-like test runner that mimics what a GitHub Actions workflow would do.

**Location:** `scripts/ci_local.sh` (bash script, simpler and more transparent)

**Steps the script should run in order:**
1. `dbt deps` — install packages
2. `dbt seed` — load seed data
3. `dbt build` — build all models and run tests
4. `sqlfluff lint models/` — lint all SQL (full project scope for final CI)
5. `dbt-score score` — run governance scoring
6. `python scripts/check_model.py --select state:modified` (or a subset) — run custom governance checks

**Exit codes:** Each step should fail-fast (exit on first failure) with a clear error message.

**Note:** Also create a stub `.github/workflows/ci.yml` as documentation of what CI *would* look like, with a comment explaining it's for reference only since the project runs locally with DuckDB.

---

## Step 10: Update README.md for publication

The README already has 56KB of content. Revise it for a public audience:

1. **Add badges** at the top (optional): dbt version, license
2. **Ensure the "Getting Started" section** is complete and accurate:
   - Clone, create venv, pip install, dbt deps, dbt seed, dbt build
   - Mention all 10 source .duckdb files are included (no external data needed)
3. **Add a "Quick Start" section** near the top for impatient readers
4. **Add "Running Tests" section** referencing `scripts/ci_local.sh`
5. **Add "Exporting Data" section** referencing `scripts/export_mart_data.py`
6. **Remove any internal/WIP language** — phrases like "in active implementation", "Phase 2 in progress", etc. Frame as a complete reference project
7. **Add "AI-Assisted Development" section** explaining the .agent/, .claude/, .gemini/ directories as a reference for using AI coding assistants with dbt projects
8. **Credit section** at the bottom

---

## Step 11: Update CLAUDE.md and GEMINI.md for publication

- Remove references to deleted files (VOICE_PROFILE, agent-autonomy.md)
- Remove "Current Phase" section that says "active implementation" — replace with project-complete framing or remove
- Remove the `.claude/projects/*/memory/MEMORY.md` reference (that's user-local, not in repo)
- Ensure both files are self-consistent after removals

---

## Step 12: Commit changes in logical groups

Stage and commit in this order (each its own commit, using conventional commit style):

1. **`chore: commit outstanding model and YAML improvements`** — The existing 24 uncommitted modified files, grouped logically into sub-commits if natural groupings exist (e.g., staging YAML updates, mart model fixes, config changes)
2. *(git filter-repo runs here — rewrites all history)*
3. **`fix(marts): fix broken dim_reservation_inventory and validate all mart models`** — Step 3
4. **`chore: trim agent scaffolding for publication`** — Steps 4-5 (deletions + CLAUDE.md/GEMINI.md updates)
5. **`chore: add MIT license and expand gitignore`** — Steps 6-7
6. **`feat(scripts): add mart data export and local CI scripts`** — Steps 8-9
7. **`docs: prepare README, CLAUDE.md, GEMINI.md for publication`** — Steps 10-11

---

## Step 13: Final validation

After all commits:
```bash
source .venv/Scripts/activate
dbt build                           # All models pass
sqlfluff lint models/               # No violations
bash scripts/ci_local.sh            # Full CI passes
python scripts/export_mart_data.py  # Exports successfully
```

Verify:
- [ ] No uncommitted changes (`git status` is clean)
- [ ] No stale branches (`git branch` shows only `main`)
- [ ] No stale worktrees (`git worktree list` shows only main)
- [ ] `git log --oneline` shows clean, conventional commit messages
- [ ] README renders correctly
- [ ] No secrets, credentials, or personal paths in any tracked file
- [ ] `.gitignore` covers all generated artifacts
- [ ] LICENSE file exists at root

---

## Execution Notes for Sonnet/Haiku

- **Shell:** Git Bash on Windows. Activate venv with `source .venv/Scripts/activate`.
- **DuckDB quirk:** `check_model.py` holds DuckDB open; run sqlfluff separately after it completes.
- **Encoding:** Prefix Python scripts with `PYTHONUTF8=1` to avoid cp1252 errors with rich console output.
- **dbt commands:** Always run from the project root. Profiles are in `profiles.yml` at root (not `~/.dbt/`).
- **Known test failure:** `not_null_int_visits__contact_sk` fails because walk-up visits have no contact — this is intentional data quality demonstration, not a bug. Document in README.
- **Windows git worktree:** If `git worktree remove` fails with "Permission denied", use `git worktree prune` then `git branch -D`.
