---
name: writing-system-prompts
description: Use when writing or substantially revising a project-level instruction file (GEMINI.md, CLAUDE.md, .cursorrules, .windsurfrules, .clinerules) for an AI coding agent. Covers the required sections, anti-patterns, and agent-specific adaptation.
---

# Writing System Prompts

## Overview

A project-level system prompt is the single most important file for an AI agent working in your codebase. It tells the agent who it is in this project, what to read, what it's allowed to do, and what to work on right now. A good system prompt means the agent's first response is useful. A bad one means every conversation starts with the agent asking "what is this project?"

**Announce at start:** "I'm using the writing-system-prompts skill to write the project instruction file."

## When to Use

- Creating a new instruction file for a project that doesn't have one
- Rewriting an instruction file that has become stale, bloated, or ineffective
- Adapting an existing instruction file for a different agent
- The project has changed phases and the system prompt needs to reflect it

**When NOT to use:**
- Minor edits to an existing, working system prompt (just edit it directly)
- Writing skills or rules (use `writing-skills` or see the bootstrap skill's Step 6)

## Before You Write

Read the project thoroughly. You cannot write a good system prompt from memory or assumption.

**Mandatory reads:**
1. The project's directory structure (`ls`, `tree`, or equivalent)
2. Any existing README, documentation, or specification files
3. Existing `.agent/rules/` and `.agent/skills/` if present
4. Any existing instruction files for other agents (CLAUDE.md, .cursorrules, etc.)
5. The project's primary configuration files (package.json, dbt_project.yml, Cargo.toml, etc.)

**Understand before writing:**
- What the project does and who consumes its output
- What technology stack it uses
- What the project's current phase or next milestone is
- What governance or standards the project follows
- Whether the project has a voice/style guide for documentation

## The 8 Required Sections

Every project system prompt must include these sections, in this order. Scale each section to the project's complexity — a small utility needs one sentence per section; a multi-system analytics project needs a paragraph.

### 1. Role Statement

One to three sentences establishing who the agent is in this project. Not a generic "you are a helpful assistant" — a specific role grounded in the project's domain.

**Good:** "You are a data engineering agent working on the DCR Analytics project for the Department of Conservation and Recreation. This project has two phases: synthetic source data generation using Python/DuckDB, and a dbt analytical pipeline that transforms those sources into governed, CDM-conforming models."

**Bad:** "You are a helpful coding assistant. Help the user with their project."

### 2. Project Structure

An annotated directory tree showing the key directories and what they contain. The agent needs spatial orientation — it should know where to look before it starts searching.

```markdown
## Project Structure
project-root/
├── src/           # Application source code
├── tests/         # Test suites
├── docs/          # Documentation and plans
├── config/        # Configuration files
└── scripts/       # Build and deployment scripts
```

Include annotations for any directory whose purpose is not obvious from its name.

### 3. Key References

A list of the most important files the agent should read before making decisions. Use the agent's native import/reference syntax where supported.

- **Gemini:** `@file.md` syntax for automatic import
- **Claude:** Direct file paths (agent reads them on demand)
- **Cursor:** File paths with instructions to read them
- **All agents:** Brief annotation of what each file contains and when to read it

**Include at minimum:** primary specification or requirements document, coding standards, domain knowledge references, and project context.

### 4. Authority and Guardrails

Three explicit lists: what the agent **may** do freely, what it **must** do always, and what it **must ask before** doing.

This section prevents two failure modes:
- The agent is too cautious and asks permission for trivial actions
- The agent is too aggressive and makes decisions that should involve the user

**Structure:**
```markdown
**You may:** [list of autonomous actions]
**You must:** [list of always-on constraints]
**Ask the user before:** [list of decisions requiring approval]
```

Mark read-only directories explicitly. Call out any files the agent should never modify.

### 5. Operating Principles

Numbered, specific, enforceable statements about how work should be done in this project. These are the project's non-negotiable conventions.

**Good principles are:**
- Specific enough to verify ("Use snake_case for all file names")
- Grounded in the project's actual constraints ("Relational integrity within systems, not between them")
- Actionable ("Run sqlfluff before considering a model complete")

**Bad principles are:**
- Vague ("Write clean code")
- Generic ("Follow best practices")
- Aspirational but unverifiable ("Optimize for readability")

Aim for 5-10 principles. More than 10 suggests some should be rules in `.agent/rules/` instead.

### 6. Technology Stack

A table of the project's technologies, their roles, and any notable constraints. The agent needs to know what tools are available and what versions matter.

```markdown
| Component | Technology | Notes |
|---|---|---|
| Language | Python 3.10+ | Type hints required |
| Database | DuckDB | One file per source system |
| Framework | dbt-core + dbt-duckdb | View/table materialization only |
```

### 7. Current Phase

What the project is working on right now and what "done" looks like for that phase. This is the most frequently stale section — update it when the project's focus shifts.

**Good:** "The project is in planning phase. The immediate task is to use SPEC_vertical_slice_revenue.md to produce a detailed project plan for the Revenue & Reservations vertical slice."

**Bad:** (absent, or describing a phase the project completed months ago)

### 8. Writing and Communication Style

If the project has a voice guide, style conventions, or documentation standards, reference them here. If not, state the minimum expectations (formal/informal, audience, terminology preferences).

This section is optional for code-only projects but important for any project that produces documentation, plans, or user-facing content.

## Anti-Patterns

**The everything prompt.** Cramming every rule, every file description, and every historical decision into the system prompt. Result: the agent ignores most of it due to context saturation. Move detailed rules to `.agent/rules/` and detailed workflows to `.agent/skills/`.

**The nothing prompt.** "This is a Python project. Help me code." Result: the agent has no orientation and asks basic questions or makes wrong assumptions on every turn.

**The stale prompt.** A system prompt written six months ago that describes the project's initial setup phase when the project is now in production. The "Current Phase" section is the first thing to go stale — update it when priorities change.

**The copied prompt.** Taking another project's system prompt and changing the project name. Every system prompt must be written from a fresh read of the actual project's files, structure, and current state.

**Guardrails without teeth.** Saying "follow the coding standards" without specifying which file contains them or how to verify compliance. Every constraint must be traceable to a specific file, tool, or command.

**Missing references.** Mentioning a specification or standards document in the principles but not listing it in the Key References section. The agent needs both the instruction and the path.

## Agent-Specific Adaptation

The same content works across agents, but the packaging differs:

| Feature | Gemini | Claude | Cursor |
|---|---|---|---|
| File imports | `@file.md` auto-loads | Paths in text (agent reads on demand) | Paths in text |
| Modular context | Split into multiple GEMINI.md files | Single CLAUDE.md (or subdirectory CLAUDE.md files) | `.cursor/rules/*.md` with frontmatter |
| Rule activation | Via `.agent/rules/` frontmatter | Inline in CLAUDE.md or referenced | `alwaysApply` / `globs` in frontmatter |
| Max practical length | ~2000 lines (with imports) | ~500 lines (always loaded) | ~500 lines per rule file |

**Key constraint:** Claude Code loads CLAUDE.md into every prompt, so keep it concise and move heavy reference material to `.agent/` files that the agent reads on demand. Gemini's `@file` imports add content automatically — use them for stable references, but be aware they increase every prompt's token count.

## Common Mistakes

**Writing the prompt before reading the project.** The prompt must reflect the project as it actually is, not as you imagine it. Read the directory tree, the config files, and at least one specification document before writing a single line.

**Forgetting the Current Phase section.** Without it, the agent doesn't know what to work on and either asks or guesses. Neither is productive.

**Listing references without annotations.** "@data_dictionary.md" tells the agent nothing. "@data_dictionary.md — Column-level definitions for all source tables; read before writing staging models" tells it exactly when and why to open that file.

**Using relative language for constraints.** "Try to follow the standards" is weaker than "The 103 rules in dbt Project Standards.md are not suggestions. Every model must comply." Agents respond to specific, imperative constraints.
