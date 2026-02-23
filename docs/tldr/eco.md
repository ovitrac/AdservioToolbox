# tldr: Eco Mode

## In-Session Toggle (Claude Code)

```
/eco on                  # enable (rm .claude/eco/.disabled)
/eco off                 # disable (touch .claude/eco/.disabled)
/eco status              # show current state + memory stats
/eco                     # same as status
```

## Shell Toggle (persistent)

```
toolboxctl eco on        # writes to .adservio-toolbox.toml
toolboxctl eco off       # writes to .adservio-toolbox.toml
toolboxctl eco           # show current state
```

## Direct Flag File (no deps)

```
rm -f .claude/eco/.disabled      # enable eco
touch .claude/eco/.disabled      # disable eco
test -f .claude/eco/.disabled && echo OFF || echo ON
```

## First-Time Setup

```bash
pip install "memctl[mcp,docs]"

# Install eco mode (scripts bundled in PyPI wheel)
bash "$(memctl scripts-path)/install_eco.sh" --db-root .memory   # install eco mode
bash "$(memctl scripts-path)/install_eco.sh" --dry-run           # preview changes

# To uninstall later:
bash "$(memctl scripts-path)/uninstall_eco.sh"                   # remove (preserves .memory/)
```

## What eco Mode Does

Replaces sequential file reading with memory-backed retrieval:

| Task | Without eco | With eco |
|------|-------------|----------|
| Explore directory | `Read` 5-10 files | `memory_inspect` — one call |
| Find a function | `Glob` + `Read` + `Grep` | `memory_recall("FnName")` |
| Remember across sessions | Cannot | `memory_propose` → `memory_recall` |
| Read .docx/.pdf | Cannot | `memory_recall` (text extracted at sync) |

## Escalation Ladder

```
Level 1: memory_inspect    ← structural overview
Level 2: memory_recall     ← selective content retrieval (FTS5)
Level 3: memory_loop       ← iterative refinement (bounded)
Level 4: Native Read/View  ← last resort (editing, line-level)
```

## Key Files

```
.claude/eco/.disabled      ← flag file (absent = eco ON)
.claude/hooks/eco-hint.sh  ← UserPromptSubmit hook (~50 tokens)
.claude/eco/ECO.md         ← full strategy file
.memory/memory.db          ← SQLite + FTS5 knowledge store
```

**Config key:** `eco.enabled_global` in `.adservio-toolbox.toml`
**Env var:** `ADSERVIO_ECO`
**Default:** installed but inactive (OFF until explicitly enabled)
