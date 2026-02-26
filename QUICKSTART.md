# Quick Start

Get the Adservio Claude Code Toolbox running in under 2 minutes.

---

## 1. Install

**Linux / macOS (one-liner):**

```bash
curl -fsSL https://github.com/ovitrac/AdservioToolbox/releases/latest/download/install.sh | bash
```

**Windows (PowerShell):**

```powershell
irm https://github.com/ovitrac/AdservioToolbox/releases/latest/download/install.ps1 -OutFile install.ps1
powershell -ExecutionPolicy Bypass -File install.ps1
```

**Cross-platform (Python — works everywhere):**

```bash
curl -fsSL https://github.com/ovitrac/AdservioToolbox/releases/latest/download/install.py -o install.py
python3 install.py       # Linux / macOS
python install.py        # Windows
```

All three installers do the same thing: install `memctl`, `cloakmcp`, and `adservio-toolbox` via pipx, wire Claude Code globally, and run `toolboxctl doctor`.

On Windows, hooks use Python entrypoints (`.py`) — no Git Bash required.

**Need Python?** See [Installing Python](docs/INSTALLING_PYTHON.md).

**Manual alternative:**

```bash
pipx install memctl[mcp,docs]
pipx install cloakmcp
pipx install adservio-toolbox
toolboxctl install --global
toolboxctl doctor
```

---

## 2. Initialize a project

```bash
cd /path/to/your-project
toolboxctl init
```

This creates `.claude/commands/` (slash commands), MCP server registrations, config file, and a CLAUDE.md block.

**With a profile:**

```bash
toolboxctl init --profile dev          # adds .claude/PROJECT.md (build/test/lint template)
toolboxctl init --profile playground   # adds CHALLENGE.md pointer
```

---

## 3. Verify

```bash
toolboxctl doctor
```

Expected output — all green:

```
  Python       3.12.x                  ok
  pipx         1.x.x                   ok
  Claude Code  2.x.x                   ok
  memctl       0.18.x                  ok  (pipx)
  cloakmcp     0.9.x                   ok  (pipx)
  toolboxctl   0.4.x                   ok  (pipx)
  PATH         cloak, memctl           ok
  Global hooks ~/.claude/              ok  CloakMCP secrets-only (5 hooks)
  Permissions  cloak/memctl/toolboxctl ok  + Read, Grep
  CLAUDE.md    ~/.claude/              ok  Toolbox block present
```

---

## 4. Try the interactive demo

The best way to discover how everything works:

```bash
# Build the demo project (clean venv, fake secrets, hooks, memory)
bash scripts/test-e2e.sh

# Launch Claude Code inside the demo
bash .e2e/default/launch.sh

# Inside the Claude session, type:
#   execute CHALLENGE.md
```

Claude walks you through 7 challenges: eco mode, secret redaction, memory recall, slash commands, write guard, audit trail, and exfiltration testing.

---

## 5. Daily usage

Once installed, everything is automatic. Start Claude Code in any initialized project:

```bash
cd your-project
claude
```

CloakMCP vaults secrets at session start, restores them at session end. memctl persists knowledge across sessions. Slash commands (`/cheat`, `/tldr`, `/eco`, `/why`, `/how`) are always available.

**Useful commands:**

```bash
toolboxctl eco on               # enable eco mode (token-efficient retrieval)
toolboxctl status                # deterministic status report
toolboxctl update                # upgrade all tools
toolboxctl rescue                # recover from CloakMCP session crash
toolboxctl deinit                # remove project wiring (reversible)
toolboxctl install --uninstall   # remove global wiring
```

---

## Next steps

- [README](README.md) — full architecture, design principles, trade-offs
- [Changelog](CHANGELOG.md) — version history
- `/cheat 1` — daily cheat sheet (inside Claude Code)
- `/cheat 2` — workflow reference
- `/cheat 3` — advanced operations
