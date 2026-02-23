# Agent Configuration Format Reference

Detailed format specifications for each supported AI coding agent. This is a point-in-time reference — always verify against the agent's current documentation before creating files.

---

## Gemini CLI / Google Antigravity

**Instruction file:** `GEMINI.md` at project root

- Loaded automatically on every prompt (concatenated with global `~/.gemini/GEMINI.md`)
- Supports `@file.md` import syntax for modular context
- Supports custom filename via `context.fileName` in settings.json
- Hierarchy: global → project root → subdirectories (all concatenated)

**Config directory:** `.gemini/`

**Settings file:** `.gemini/settings.json`
```json
{
  "context": {
    "importFormat": "@",
    "fileFiltering": {
      "respectGitIgnore": true,
      "respectGeminiIgnore": true,
      "enableRecursiveFileSearch": true
    },
    "includeDirectories": [],
    "loadFromIncludeDirectories": false
  },
  "tools": {
    "shell": { "enableInteractiveShell": false }
  },
  "general": {
    "checkpointing": { "enabled": true }
  },
  "mcpServers": {}
}
```

**Ignore file:** `.geminiignore` (same syntax as .gitignore)

**Skills/Rules:** Reads `.agent/skills/` and `.agent/rules/` (Antigravity format).
- Skills: `SKILL.md` with `name` + `description` frontmatter
- Rules: `activation` (always_on | model_decision) + `description` frontmatter

---

## Claude Code

**Instruction file:** `CLAUDE.md` at project root

- Loaded automatically on every prompt
- No @file import syntax — all content must be inline or referenced by path
- Hierarchy: global `~/.claude/CLAUDE.md` → project root → subdirectories (all concatenated)
- Supports `CLAUDE.local.md` for user-specific overrides (not committed)

**Config directory:** `.claude/`

**Settings file:** `.claude/settings.json`
```json
{
  "permissions": {
    "allow": [],
    "deny": []
  }
}
```

**Ignore file:** None dedicated — uses `.gitignore`

**Skills/Rules:** Can read `.agent/skills/` and `.agent/rules/` but does not natively activate them. Skills are invoked through slash commands or explicit instruction in CLAUDE.md.

---

## Cursor

**Instruction file:** `.cursorrules` at project root (legacy) or `.cursor/rules/*.md` (current)

- `.cursorrules`: single file, loaded on every prompt
- `.cursor/rules/`: directory of rule files, each with frontmatter:
  ```yaml
  ---
  description: When this rule applies
  globs: "**/*.py"  # optional file pattern filter
  alwaysApply: true  # or false for conditional loading
  ---
  ```
- Hierarchy: global rules + project rules (all merged)

**Config directory:** `.cursor/`

**Settings file:** `.cursor/settings.json` (VS Code settings format)

**Ignore file:** `.cursorignore` (same syntax as .gitignore)

**Skills/Rules:** Can read `.agent/` format if instructed in .cursorrules, but does not auto-discover.

---

## Windsurf (Codeium)

**Instruction file:** `.windsurfrules` at project root

- Single file, loaded on every prompt
- Plain markdown, no special syntax
- Global rules at `~/.windsurf/global_rules.md`

**Config directory:** `.windsurf/`

**Settings file:** `.windsurf/settings.json`

**Ignore file:** None dedicated — uses `.gitignore`

**Skills/Rules:** Does not natively read `.agent/` format. Must reference skills explicitly in `.windsurfrules`.

---

## Cline

**Instruction file:** `.clinerules` at project root

- Plain markdown, loaded on every prompt
- Also supports `.clinerules/` directory with multiple files

**Config directory:** `.cline/`

**Settings file:** Configured through VS Code extension settings

**Ignore file:** None dedicated — uses `.gitignore`

**Skills/Rules:** Does not natively read `.agent/` format.

---

## The Shared `.agent/` Format

The `.agent/` directory is an open format originated by Antigravity that multiple agents can read:

```
.agent/
├── rules/
│   └── *.md          # YAML frontmatter: activation + description
└── skills/
    └── skill-name/
        ├── SKILL.md   # YAML frontmatter: name + description
        ├── references/ # Supporting docs
        └── scripts/    # Executable helpers
```

**Agents with native `.agent/` support:** Gemini CLI, Antigravity
**Agents that can be taught to use it:** Claude Code (via CLAUDE.md instructions), Cursor (via .cursorrules reference)
**Agents that cannot use it directly:** Windsurf, Cline (must duplicate relevant content into their instruction files)

---

## Cross-Agent Portability Notes

- **System prompt content** is portable — the same project context works in any instruction file, just formatted differently
- **Settings** are NOT portable — each agent has its own schema
- **Ignore files** use the same .gitignore syntax but have different filenames
- **Skills and rules** in `.agent/` are natively supported by Gemini/Antigravity only; other agents need explicit instructions to read them
- When a project supports multiple agents, commit all instruction files (GEMINI.md, CLAUDE.md, .cursorrules) and add each agent's config directory to the other agents' ignore files
