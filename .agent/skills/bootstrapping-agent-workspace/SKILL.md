---
name: bootstrapping-agent-workspace
description: Use when setting up a project for a new AI coding agent (Gemini, Claude, Cursor, Windsurf, Cline) or when migrating an existing project's agent configuration to support a different agent. Covers system prompts, configuration directories, ignore files, rules, and skills.
---

# Bootstrapping an Agent Workspace

## Overview

Set up a project so that a specific AI coding agent can work in it effectively from the first prompt. This means creating the agent's instruction file, configuration directory, ignore file, and ensuring existing skills and rules are portable.

**Announce at start:** "I'm using the bootstrapping-agent-workspace skill to set up this project for [agent name]."

## When to Use

- User asks to "set up this project for Gemini/Cursor/Windsurf/etc."
- User asks to "bootstrap" or "configure" the project for an AI agent
- User is migrating from one agent to another and wants the new agent to inherit project context
- A new project needs agent configuration from scratch

**When NOT to use:**
- Updating an existing system prompt that's already working (use `writing-system-prompts` directly)
- Creating a new skill for an already-configured agent (use `writing-skills`)

## Quick Reference: Agent Configuration Formats

| Agent | Instruction File | Config Directory | Settings File | Ignore File |
|---|---|---|---|---|
| Gemini CLI / Antigravity | `GEMINI.md` | `.gemini/` | `.gemini/settings.json` | `.geminiignore` |
| Claude Code | `CLAUDE.md` | `.claude/` | `.claude/settings.json` | — (uses .gitignore) |
| Cursor | `.cursorrules` or `.cursor/rules/` | `.cursor/` | `.cursor/settings.json` | — |
| Windsurf | `.windsurfrules` | `.windsurf/` | `.windsurf/settings.json` | — |
| Cline | `.clinerules` | `.cline/` | — | — |

All agents can read `.agent/skills/` and `.agent/rules/` (the shared Antigravity/open format).

See `references/agent-formats.md` for detailed format specifications.

## The Process

### Step 1: Research the Target Agent's Configuration Format

Before creating files, verify the agent's current configuration format. Agent tooling evolves rapidly — settings schemas change, new features appear, old conventions deprecate.

**Actions:**
- Search the agent's official documentation for the latest configuration reference
- Check for format version changes (e.g., Gemini CLI updated its settings.json schema in September 2025)
- Confirm which instruction file name the agent reads (some support multiples)
- Note any agent-specific features: `@file` imports (Gemini), `<rule>` tags (Cursor), `#` section headers (Windsurf)

**Do not skip this step.** Cached knowledge about agent formats may be out of date.

### Step 2: Write the Project-Level System Prompt

**Use the `writing-system-prompts` skill.** It covers the 8 required sections, anti-patterns, and agent-specific adaptation.

The system prompt is the most important file you create. It determines whether the agent understands the project or fumbles through it.

### Step 3: Create Configuration Directory and Settings

Create the agent's config directory (e.g., `.gemini/`) and populate it with a settings file tuned for the project.

**What to configure:**
- Context/file discovery settings (which directories to scan, import format)
- File filtering (respect .gitignore, respect agent-specific ignore)
- Tool permissions (shell access, sandbox mode)
- Checkpointing/session recovery if supported
- MCP server connections if the project uses them

**What NOT to configure:**
- User-level preferences (themes, keybindings, editor) — those belong in the global config, not the project
- Authentication — that's user-specific

### Step 4: Create Ignore File

Create the agent-specific ignore file to exclude noise from the agent's file search and context.

**Standard exclusions:**
- Generated artifacts (build output, compiled files, .duckdb, etc.)
- Package manager caches (node_modules/, .venv/, __pycache__/)
- Build tool output (target/, dist/, logs/)
- IDE and OS files (.vscode/, .idea/, .DS_Store, Thumbs.db)
- Other agents' configuration directories (if agent A is being set up, exclude agent B's config)

### Step 5: Audit Existing `.agent/` Skills and Rules for Portability

If the project already has `.agent/skills/` or `.agent/rules/`, audit them for agent-specific references that would confuse the new agent.

**Search for these patterns:**
- `superpowers:` — Claude Code skill invocation syntax
- `Claude`, `Gemini`, `Cursor` — hardcoded agent names in workflow instructions (keep them when they refer to actual products like "Claude Desktop"; remove when they're cross-references)
- Agent-specific tool names (`TodoWrite`, `AskUserQuestion`, `run_command`) — these vary by agent
- Hardcoded paths to agent config (`~/.claude/`, `~/.gemini/`)

**Replace with agent-agnostic alternatives:**
- `superpowers:skill-name` → "Use the skill-name skill"
- `TodoWrite` → "Update your task tracker" (or remove if the skill doesn't depend on it)
- Agent-specific instructions → generic instructions that any agent can follow

**Do NOT change:**
- Legitimate product references ("configure this for Claude Desktop and Cursor")
- Technical content that happens to mention an agent's name

### Step 6: Add Domain-Specific Governance Rules If Missing

Check whether `.agent/rules/` covers the project's current work phase. If the project is transitioning phases (e.g., from data generation to dbt modeling), the existing rules may not cover the new domain.

**Rule file format:**
```yaml
---
activation: always_on  # or model_decision
description: One-line description of when this rule applies.
---

# Rule Title

[Markdown body with specific, enforceable constraints]
```

**`always_on`** — loaded into every prompt. Use for universal constraints (naming, formatting, architecture).
**`model_decision`** — loaded when the agent decides the rule is relevant. Use for domain context that's only needed sometimes.

### Step 7: Create or Adapt Phase-Appropriate Skills

If the project has a specific near-term task (e.g., "use this SPEC to write a project plan"), create a skill that guides the agent through it.

**Use the `writing-skills` skill** for skill authoring conventions.

## Portability Audit Checklist

Run through this after completing all steps:

- [ ] System prompt references only files that exist in the project
- [ ] System prompt uses the correct import syntax for the target agent
- [ ] Settings file uses the correct schema for the target agent
- [ ] Ignore file excludes the correct artifacts for this project's tech stack
- [ ] No `.agent/skills/` SKILL.md files contain agent-specific invocation syntax
- [ ] No `.agent/rules/` files reference agent-specific tools or config paths
- [ ] At least one rule covers the project's current work phase
- [ ] At least one skill supports the project's immediate next task

## Common Mistakes

**Writing the system prompt last.** The system prompt is the foundation — write it early, not as an afterthought after creating config files.

**Copy-pasting another project's system prompt.** Every project's system prompt must reflect that project's structure, references, and current phase. A copied prompt will have wrong paths, missing references, and stale phase information.

**Ignoring the agent's own config directory.** If you're setting up Gemini, don't forget to exclude `.claude/` from `.geminiignore` and vice versa. Agents shouldn't index each other's config.

**Over-configuring settings.json.** Only set project-level configuration. User preferences (theme, keybindings, editor) belong in the user's global config, not the project.

**Auditing skills by reading only SKILL.md.** Also check `references/` and `scripts/` directories for agent-specific content — it's easy to miss a hardcoded `superpowers:` call inside a reference file.

**Creating rules that duplicate existing ones.** Before adding a governance rule, read all existing rules to ensure you're not creating redundancy or contradictions.
