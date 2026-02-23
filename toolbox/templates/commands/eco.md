You are managing the eco mode toggle for the Adservio Toolbox.

Argument received: $ARGUMENTS

eco mode replaces Claude's sequential file browsing with deterministic structural retrieval and persistent cross-file reasoning via 14 `memory_*` MCP tools. Same questions, better answers, fewer tokens, memory that survives between sessions.

Behavior:

- **"on"** → Run `rm -f .claude/eco/.disabled`, then confirm:
  "eco mode enabled. Using memory_inspect, memory_recall, and persistent memory.
  Read .claude/eco/ECO.md for the full strategy."
  Then run `memctl stats --db .memory/memory.db 2>/dev/null` and display a brief summary
  (item count, tier breakdown). If the DB does not exist yet, say "No memory database yet — it will be created on first use."
  Also mention: run `toolboxctl eco on` from the shell to persist the setting across sessions.

- **"off"** → Run `touch .claude/eco/.disabled`, then confirm:
  "eco mode disabled. Using native Read/View only. No memory, no recall, no structural exploration."
  Also mention: run `toolboxctl eco off` from the shell to persist the setting.

- **"status"** → Check if `.claude/eco/.disabled` exists.
  If absent: report eco ON, then run `memctl stats --db .memory/memory.db 2>/dev/null` and show item count + last sync info.
  If present: report eco OFF.

- **No argument** → Same as "status".

Additional context:
- The eco hook (`.claude/hooks/eco-hint.sh`) injects ~50 tokens per turn when enabled
- The escalation ladder: memory_inspect → memory_recall → memory_loop → native Read
- eco is advisory for retrieval, not restrictive for editing
- For the full strategy, read `.claude/eco/ECO.md`
