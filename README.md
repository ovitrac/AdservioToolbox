# Adservio Claude Code Toolbox

**A local-first AI operating environment for professional development teams.**

The Adservio Toolbox integrates:

- **[CloakMCP](https://pypi.org/project/cloakmcp/)** — deterministic secret boundary enforcement
- **[memctl](https://pypi.org/project/memctl/)** — policy-governed project memory (SQLite + FTS5)
- **Claude Code** — AI-assisted development

into a single, reproducible, installation-controlled workflow.

No vendoring. No source copying. No hidden coupling.

Each component retains its independent lifecycle.
The toolbox orchestrates them via environment configuration and Claude Code wiring.

---

## Architecture

```
                 AdservioToolbox
           ┌────────────────────────┐
Files ───► │  CloakMCP  (boundary)  │  "What is allowed to leave the machine?"
           │         ↓              │
           │     Claude Code        │
           │         ↓              │
           │  memctl   (memory)     │  "What is allowed to persist?"
           └────────────────────────┘
```

**Closed operational loop:** sanitize → work → store → recall → sanitize.

```
Phase 1 — Install tooling (pipx from PyPI)
┌────────────────────────────────────────┐
│  pipx install memctl[mcp,docs]         │  → memctl, memctl-serve on PATH
│  pipx install cloakmcp                 │  → cloak on PATH
│  pipx install adservio-toolbox         │  → toolboxctl on PATH
└────────────────────────────────────────┘
           ↓ then ↓
Phase 2 — Wire Claude Code
┌────────────────────────────────────────┐
│  toolboxctl install --global           │
│    → CloakMCP hooks in ~/.claude/      │
│    → Permissions in settings.local     │
│    → Behavioral rules in CLAUDE.md     │
│    → toolboxctl doctor validates all   │
└────────────────────────────────────────┘
```

**The toolbox never imports memctl or CloakMCP at the Python level.**
It installs, configures, and wires them — nothing more.

| Scope | What | When |
|-------|------|------|
| **Global** (`~/.claude/`) | CloakMCP hooks, tool permissions (Bash/Read/Grep), CLAUDE.md block | `toolboxctl install --global` |
| **Per-project** (`.claude/`) | Slash commands, eco hooks, MCP servers, memory | `toolboxctl init` |

---

## Design Principles

- **No vendoring** — memctl and CloakMCP are installed from PyPI origin.
- **Thin orchestration** — no Python-level imports between projects.
- **Deterministic configuration** — single `.adservio-toolbox.toml`, explicit precedence.
- **Local sovereignty** — no cloud dependency, all processing on-premises.
- **Closed governance loop** — sanitize → work → store → recall → sanitize.
- **Isolated validation** — playground environment with smoke tests.
- **Idempotent operations** — every command is safe to run twice.
- **Independent lifecycles** — each tool has its own version, upgrade, and uninstall.

---

## Quick Install

### One-liner (Linux / macOS)

```bash
curl -fsSL https://github.com/ovitrac/AdservioToolbox/releases/download/v0.3.0/install.sh \
  -o install.sh \
  && curl -fsSL https://github.com/ovitrac/AdservioToolbox/releases/download/v0.3.0/SHA256SUMS \
  -o SHA256SUMS \
  && (shasum -a 256 -c SHA256SUMS 2>/dev/null || sha256sum -c SHA256SUMS) \
  && bash install.sh
```

This installs all three tools via pipx, wires Claude Code globally, and runs `toolboxctl doctor`.

**Prerequisites:** bash, Python 3.10+ (system Python is fine).

### Manual installation

```bash
# 1. Install tools via pipx (recommended) or pip
pipx install memctl[mcp,docs]
pipx install cloakmcp
pipx install adservio-toolbox

# 2. Wire Claude Code globally (hooks + permissions + behavioral rules)
toolboxctl install --global

# 3. Verify
toolboxctl doctor

# 4. Initialize a project
cd /path/to/your-project
toolboxctl init
```

### Install tracks

The installer selects the best available method:

| Track | Requirements | Method |
|-------|-------------|--------|
| **A** (recommended) | Python + pip + venv | pipx (isolated environments) |
| **B** (fallback) | Python + pip | `pip install --user` (less isolation) |

If Python is missing, the installer prints distro-specific install instructions and exits.

### Upgrade / Uninstall

```bash
# Upgrade all tools
bash install.sh --upgrade

# Uninstall everything (tools + global wiring)
bash install.sh --uninstall
```

### Expected doctor output

```
$ toolboxctl doctor

  Adservio Toolbox — Doctor

  Python       3.12.3                  ✓
  pipx         1.4.3                   ✓
  Claude Code  2.1.x                   ✓
  memctl       0.16.x                  ✓  (pipx)
  cloakmcp     0.9.x                   ✓  (pipx)
  toolboxctl   0.3.0                   ✓  (pipx)
  PATH         cloak, memctl           ✓
  Global hooks ~/.claude/              ✓  CloakMCP secrets-only (5 hooks)
  Permissions  cloak/memctl/toolboxctl ✓  + Read, Grep
  CLAUDE.md    ~/.claude/              ✓  Toolbox block present
```

---

## What This Enables

With the Toolbox installed and configured:

- **Secrets are automatically vaulted** before AI exposure (CloakMCP hooks).
- **AI-generated knowledge is persistently structured** across memory tiers (memctl STM → MTM → LTM).
- **Retrieval becomes deterministic** — FTS5 full-text search with configurable token budgets.
- **Claude sessions become reproducible** — shared config, slash commands, environment bridge.
- **Policies are explicit and auditable** — detection rules, severity levels, inheritance chains.
- **Integration is validated in isolation** — `toolboxctl playground` runs smoke tests in a clean venv.
- **End-to-end validated** — `scripts/test-e2e.sh` builds a full demo project with 17 automated checks and an interactive challenge test.

---

## Subcommands

| Command | Purpose |
|---------|---------|
| `toolboxctl install [--fts fr\|en\|raw] [--upgrade]` | Install memctl + CloakMCP into current Python environment |
| `toolboxctl install --global` | Wire Claude Code globally (hooks + permissions + CLAUDE.md) |
| `toolboxctl install --uninstall` | Remove global wiring |
| `toolboxctl init [--force] [--fts ...]` | Wire `.claude/commands/`, create config |
| `toolboxctl status` | Deterministic status report |
| `toolboxctl doctor` | Diagnostic check (all components, PATH, hooks, permissions) |
| `toolboxctl eco [on\|off]` | Toggle eco mode |
| `toolboxctl env [--json]` | Export config as env vars |
| `toolboxctl playground [--clean]` | Isolated venv with smoke tests |

## Slash Commands

After `toolboxctl init`, these are available in Claude Code sessions:

| Command | Purpose | Source |
|---------|---------|--------|
| `/cheat [1\|2\|3]` | Leveled cheat sheet (L1=daily, L2=workflows, L3=advanced) | toolbox |
| `/tldr [topic]` | Concise reference card | toolbox |
| `/eco [on\|off]` | Show or toggle eco mode | toolbox + memctl |
| `/why <topic>` | Explain rationale and invariants | toolbox |
| `/how <task>` | Step-by-step operational guide | toolbox |
| `/scan [path]` | Index a folder into memory | memctl |
| `/recall <query>` | Search memory (FTS5) | memctl |
| `/remember <text>` | Store an observation | memctl |
| `/reindex [preset]` | Rebuild FTS index | memctl |
| `/forget all` | Reset memory | memctl |
| `/consolidate` | Merge STM into MTM | memctl |
| `/status` | Memory health dashboard | memctl |
| `/export` | Export memory as JSONL | memctl |
| `/diff` | Show memory diff since last session | memctl |

The first 5 commands are installed by `toolboxctl init`. The remaining are added by `memctl install_eco.sh`.

---

## Configuration

`toolboxctl init` creates `.adservio-toolbox.toml` in the project root:

```toml
[eco]
enabled_global = false

[memctl]
db = ".memory/memory.db"
fts = "fr"
budget = 2200
tier = "stm"

[cloak]
policy = ".cloak/policy.yaml"
mode = "enforce"
fail_closed = false
```

**Precedence:** CLI flags > env vars > `.adservio-toolbox.toml` > compiled defaults.

Inject into your shell: `eval "$(toolboxctl env)"`

---

## Eco Mode

Eco mode reduces token usage and defers memory consolidation. Installed by default, **inactive until enabled**:

```bash
toolboxctl eco on       # enable globally
toolboxctl eco off      # disable globally
export ADSERVIO_ECO=1   # per-session
```

---

## Hook Installation

After `toolboxctl install --global`, CloakMCP hooks are wired globally. For per-project hooks, both sub-projects bundle their installer scripts in the PyPI wheel — no git clone required:

```bash
# CloakMCP hooks — automatic secret sanitization at session boundaries
bash "$(cloak scripts-path)/install_claude.sh"                       # secrets-only (5 hooks)
bash "$(cloak scripts-path)/install_claude.sh" --profile hardened     # + Bash safety guard (6 hooks)
bash "$(cloak scripts-path)/install_claude.sh" --uninstall            # remove hooks

# memctl hooks — eco mode (token-efficient retrieval)
bash "$(memctl scripts-path)/install_eco.sh" --db-root .memory        # eco hook + strategy + /eco
bash "$(memctl scripts-path)/uninstall_eco.sh"                        # remove eco (preserves .memory/)
```

See `/cheat 3` or `docs/cheat/L3.md` for the full list of installer scripts, profiles, and options.

---

## End-to-End Testing

The toolbox includes a full integration test and a standalone hook installer:

```bash
# Full e2e: clean venv → install → demo project → hooks → 17 checks
bash scripts/test-e2e.sh

# Launch the demo (activates venv, cd's into demo project, starts Claude)
bash .e2e/launch.sh

# Inside Claude Code, run the interactive challenge:
# "read CHALLENGE.md and execute all 7 challenges"

# Standalone hook installer for any project
bash scripts/install-hooks.sh --dir /path/to/project
bash scripts/install-hooks.sh --dir /path/to/project --hardened
bash scripts/install-hooks.sh --dir /path/to/project --uninstall

# Cleanup
bash scripts/test-e2e.sh --clean
```

The 7 challenges exercise: eco mode activation, secret redaction, memory recall, slash commands, write guard, audit trail, and backup exfiltration testing.

---

## Release Pipeline

Releases are built locally and published via GitHub Releases:

```bash
# Build release assets (sdist, zip, scripts, SHA256SUMS)
bash scripts/build-release.sh

# Build with version override
bash scripts/build-release.sh --version 0.2.0

# Build with GPG signature
bash scripts/build-release.sh --sign

# Clean release artifacts
bash scripts/build-release.sh --clean
```

Or use the GitHub Actions workflow — push a `v*` tag to trigger an automated release.

---

## Operational Guarantees (v0.3.0)

- **Idempotent installer** — `toolboxctl install` and `toolboxctl init` are safe to run repeatedly.
- **Deterministic status** — `toolboxctl status` output is stable and pasteable into issues.
- **Explicit config precedence** — CLI flags > env vars > TOML > compiled defaults.
- **Isolated playground validation** — `toolboxctl playground` tests in a clean venv, never touches your environment.
- **Zero coupling** — sub-projects are installed, not imported; no shared Python state.
- **Independent release cadence** — memctl, CloakMCP, and the toolbox version independently.
- **Capability-based installer** — detects Python, pip, venv and selects the best install track; never runs sudo.
- **Reversible global wiring** — `toolboxctl install --uninstall` cleanly removes hooks, permissions, and CLAUDE.md block.
- **Document-ready** — `memctl[mcp,docs]` includes Office and PDF support; no extra install steps.

---

## Requirements

- Python 3.10+ (system Python is fine)
- Claude Code (`npm install -g @anthropic-ai/claude-code`)
- pipx (recommended, installed automatically by the bootstrap script)

## License

MIT — see [LICENSE](LICENSE).
