---
name: planning-from-spec
description: Use when you have a vertical slice specification (SPEC) and need to produce a detailed, ordered project plan with bite-sized implementation tasks. This skill transforms a SPEC document into an executable plan.
---

# Planning from a Specification

## Overview

Transform a vertical slice specification into a detailed project plan that an engineer can follow task-by-task without ambiguity. The plan must respect the SPEC's layer ordering, the dbt Project Standards' 103 rules, and the CDM conformance requirements.

**Announce at start:** "I'm using the planning-from-spec skill to create a project plan from the specification."

## Prerequisites

Before writing the plan, read and internalize:

1. The SPEC document (e.g., `reference/SPEC_vertical_slice_revenue.md`)
2. `reference/dbt_project_standards.md` — the 103 governance rules
3. `.agent/rules/dbt-project-governance.md` — layer discipline, naming, testing, CDM requirements
5. Relevant CDM metadata in `source_data/cdm_metadata/` for entity mapping

## Plan Structure

The plan must follow this structure:

```markdown
# [Slice Name] Project Plan

**Source Specification:** [path to SPEC file]
**Goal:** [One sentence from the SPEC's problem statement]
**Architecture:** [2-3 sentences summarizing the layer-by-layer approach]
**Tech Stack:** [Key technologies from the SPEC]
**Success Criteria:** [Pulled from the SPEC's success metrics]

---

## Phase 0: Project Initialization
[Tasks for Layer 0 from the SPEC]

## Phase 1: Source Definitions
[Tasks for Layer 1]

## Phase 2: Base Models (if applicable)
[Tasks for Layer 2]

## Phase 3: Staging Models
[Tasks for Layer 3]

## Phase 4: Integration Models
[Tasks for Layer 4]

## Phase 5: Mart Models
[Tasks for Layer 5]

## Phase 6: Seeds, Macros, and Singular Tests

## Phase 7: Linting and Governance Verification

## Phase 8: End-to-End Validation
```

## Task Granularity

Each task within a phase should be a single, verifiable action taking 2-10 minutes:

````markdown
### Task N.M: [Descriptive Name]

**Files:**
- Create: `exact/path/to/file.sql`
- Create: `exact/path/to/_models.yml`

**Steps:**
1. [Specific action with exact file content or reference to the SPEC section]
2. [Verification step — run a command, check output]
3. [Commit step if applicable]

**Verification:**
- `dbt compile --select model_name` succeeds
- sqlfluff lint passes
- [Any SPEC-defined acceptance criteria]

**Standards Compliance:**
- [List specific rule IDs this task satisfies, e.g., ALL-NAME-01, SQL-STG-01]
````

## Phase-Specific Guidance

### Phase 0: Project Initialization
- Create virtual environment, install dependencies, pin versions
- Scaffold dbt project structure per the SPEC's Layer 0 table
- Configure `dbt_project.yml`, `profiles.yml`, `packages.yml`
- Configure sqlfluff and dbt-score
- Verify: `dbt debug` passes, `dbt deps` installs, sqlfluff runs

### Phase 1: Source Definitions
- One task per source system in scope
- Create `_sources.yml` with all tables, columns, descriptions, and tests
- Reference the Data Inventory for column-level detail
- Verify: `dbt compile` succeeds, `dbt source freshness` runs (if applicable)

### Phase 2-3: Base and Staging Models
- One task per model
- Each task: write SQL, write YAML properties, write tests, verify
- Follow CTE structure from Standards (import, rename, cast, transform, final)
- Base models handle complex source cleanup (deduplication, entity splitting)
- Staging models handle renaming, type casting, standard transformations

### Phase 4: Integration Models
- Start with `int_parks` — it's the anchor dimension for all future slices
- Map columns to CDM entity fields per the SPEC's CDM mapping table
- Include surrogate key generation via `dbt_utils.generate_surrogate_key`
- Cross-reference across source systems where the SPEC calls for it
- Verify CDM conformance against `source_data/cdm_metadata/`

### Phase 5: Mart Models
- Dimensions before facts (dimension PKs are FK targets in facts)
- Report model last (it joins facts and dimensions)
- Include aggregation balance tests for facts

### Phase 6: Seeds, Macros, Singular Tests
- Seeds: create CSV files and `_seeds.yml` per the SPEC
- Macros: implement helper macros per the SPEC (source system tags, string cleaning, park ID casting)
- Singular tests: implement reconciliation and validation tests per the SPEC

### Phase 7: Linting and Governance
- Run sqlfluff on all files, fix violations
- Run dbt-score, ensure thresholds met
- Run dbt-project-evaluator, resolve any DAG or naming violations
- Map each of the 103 Standards rules to its verification method

### Phase 8: End-to-End Validation
- `dbt build --full-refresh` with zero errors
- Row count validation per the SPEC's success metrics
- Revenue reconciliation test passes
- All singular tests pass

## Open Questions

If the SPEC contains open questions (it usually does), the plan must:
1. List each open question prominently at the top of the plan
2. State the SPEC's recommended resolution if one exists
3. Flag questions that block specific tasks
4. Recommend which questions to resolve before starting vs. which can be deferred

## Saving the Plan

Save the completed plan to: `reference/plans/YYYY-MM-DD-{slice-name}-project-plan.md`

## After the Plan

Present the plan to the user for review. Offer to:
1. Walk through any phase in more detail
2. Adjust task granularity (more or fewer steps)
3. Reorder phases if dependencies allow
4. Begin execution of Phase 0
