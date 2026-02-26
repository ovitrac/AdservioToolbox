<div align="center">

# Adservio Claude Code Toolbox

### Install once. Every session, secrets are vaulted and memory persists.

**Orchestrates [CloakMCP](https://pypi.org/project/cloakmcp/) + [memctl](https://pypi.org/project/memctl/) for Claude Code — fully local, no cloud.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Version](https://img.shields.io/badge/version-0.5.2-orange.svg)](https://github.com/ovitrac/AdservioToolbox/releases)
[![Tests](https://img.shields.io/badge/e2e-18%20passing-brightgreen.svg)](#try-it--end-to-end-demo)
[![Doctor](https://img.shields.io/badge/doctor-12%2F12%20passing-brightgreen.svg)](#verification)
[![Challenges](https://img.shields.io/badge/challenges-7%2F7%20passing-brightgreen.svg)](#try-it--end-to-end-demo)
[![Components](https://img.shields.io/badge/components-CloakMCP%20%2B%20memctl-blueviolet.svg)](#architecture)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

[Quick Start](QUICKSTART.md) • [Architecture](#architecture) • [Install](#quick-install) • [Subcommands](#subcommands) • [Try It](#try-it--end-to-end-demo) • [Configuration](#configuration) • [Recovery](#secret-recovery) • [Changelog](CHANGELOG.md)

</div>

---

CloakMCP redacts secrets before Claude sees your files. memctl gives Claude persistent memory across sessions. Nothing leaves your machine.

No vendoring. No source copying. No hidden coupling. Each component retains its independent lifecycle — the toolbox orchestrates them via configuration and Claude Code hooks.

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
| **Global** (`~/.claude/`) | CloakMCP safety seatbelt, tool permissions (Bash/Read/Grep), CLAUDE.md block | `toolboxctl install --global` |
| **Per-project** (`.claude/`, `.toolbox/`) | Slash commands, eco hooks, MCP servers, CLAUDE.md overlay, manifest, memory | `toolboxctl init [--profile]` |

**Layer doctrine:** GLOBAL=safety seatbelt (CloakMCP only), PROJECT=overlay (references GLOBAL), ECO.md=activation docs (memctl guidance). No memctl workflow instructions in CLAUDE.md blocks.

---

## What This Is (and Isn't)

**The honest case for the toolbox:**

> It does solve a real problem. Developers using Claude Code with private repos are exposing API keys,
> database URIs, and credentials to the model with no protection layer. CloakMCP's pack/unpack lifecycle
> is the only tool that operates at the Claude Code session boundary — not at commit time, not in CI,
> but at the moment of LLM exposure. That's a genuine gap in the market.

> memctl's persistent, tier-based memory solves a second real problem: Claude Code sessions are stateless
> by default. Having FTS5-searchable, token-budgeted memory that survives session restarts is valuable,
> especially in large codebases.

**The honest case against:**

> Regex-based secret detection is not AST-aware — creative obfuscation (splitting a key across variables,
> base64-encoding) will bypass any regex scanner. That's a trade-off boundary, not a bug. CloakMCP
> is a lightweight, language-agnostic preprocessor, not a language-specific static analyzer.

> If your repo has no secrets, CloakMCP is pure cost. This product is for repos where
> `git log -p | grep -i password` returns results you'd rather it didn't, and where those repos
> get shared with LLMs daily — enterprise codebases, client projects, infrastructure configs.

**Fair summary:**

> The toolbox is a genuine productivity and safety layer for professional Claude Code usage.
> It's not magic and it's not zero-cost — but for teams working with sensitive codebases and AI daily,
> the alternative is doing this manually or not doing it at all.

### Trade-off Boundaries

These are design choices, not bugs:

- **"Three tools duct-taped together"** — CloakMCP alone has 7 hook scripts, a YAML policy engine,
  an encrypted vault, a manifest system, an audit log, and a session state machine. When it works,
  it's invisible. When it breaks, the user is debugging a state machine they didn't know existed.
  The v0.9.1 auto-recovery fix was exactly this — patching a silent failure mode. The answer is
  better diagnostics (`toolboxctl rescue`), not fewer moving parts.

- **"Regex-based, not AST-aware"** — AST-aware detection would require language-specific parsers
  for every file type (Python, Java, YAML, JSON, .env, shell...). CloakMCP is a lightweight,
  language-agnostic preprocessor. The regex approach trades recall for simplicity and speed.
  Creative obfuscation will bypass any regex scanner — that's documented in CloakMCP's
  `SECURITY.md` under "inference vs exfiltration."

- **"Solo dev overhead"** — If your repo has no secrets, CloakMCP is pure cost. The product is for repos
  where `git log -p | grep -i password` returns results, and those repos get shared with LLMs daily.

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

The simplest install uses the bootstrap script published with every [GitHub Release](https://github.com/ovitrac/AdservioToolbox/releases):

```bash
curl -fsSL https://github.com/ovitrac/AdservioToolbox/releases/latest/download/install.sh | bash
```

This downloads `install.sh` from the latest release, installs all three tools via pipx, wires Claude Code globally, and runs `toolboxctl doctor`.

To verify the script checksum before running:

```bash
curl -fsSL https://github.com/ovitrac/AdservioToolbox/releases/latest/download/install.sh \
  -o install.sh \
  && curl -fsSL https://github.com/ovitrac/AdservioToolbox/releases/latest/download/SHA256SUMS \
  -o SHA256SUMS \
  && (shasum -a 256 -c SHA256SUMS 2>/dev/null || sha256sum -c SHA256SUMS) \
  && bash install.sh
```

To pin a specific version (e.g., `v0.4.5`):

```bash
curl -fsSL https://github.com/ovitrac/AdservioToolbox/releases/download/v0.4.5/install.sh | bash
```

### Windows (PowerShell)

```powershell
irm https://github.com/ovitrac/AdservioToolbox/releases/latest/download/install.ps1 -OutFile install.ps1
powershell -ExecutionPolicy Bypass -File install.ps1
```

Options: `-Upgrade`, `-Uninstall`, `-SkipGlobal`, `-Version 0.5.1`, `-DryRun`.

### Cross-platform (Python — works everywhere)

If you prefer a single installer that works on Windows, macOS, and Linux without Bash or PowerShell:

```bash
curl -fsSL https://github.com/ovitrac/AdservioToolbox/releases/latest/download/install.py -o install.py
python3 install.py          # Linux / macOS
python install.py           # Windows
```

`install.py` is pure Python (stdlib only) — no pip needed to run it.

**Prerequisites:** Python 3.10+ (system Python is fine).
**Need Python?** See [Installing Python](docs/INSTALLING_PYTHON.md) for platform-specific instructions, user-mode options, and the uv escape hatch.

### What the installers do

All three installers (`install.sh`, `install.ps1`, `install.py`) perform the same steps:

1. Detect Python version and check for `pip` + `venv`
2. Install or bootstrap `pipx` (if not present)
3. Install `memctl[mcp,docs]`, `cloakmcp`, and `adservio-toolbox` via pipx
4. Run `toolboxctl install --global` to wire Claude Code (hooks, permissions, CLAUDE.md)
5. Run `toolboxctl doctor` to validate the installation

On Windows, hooks are wired using Python entrypoints (`.py`) instead of Bash scripts — no Git Bash required.

Each release is built automatically by GitHub Actions when a `v*` tag is pushed.
Release assets include: `install.sh`, `install.ps1`, `install.py`, source archive, and `SHA256SUMS`.

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

### Per-project setup

Use `scripts/playground.sh` to set up any project directory with a single command (init + hooks + starter CLAUDE.md):

```bash
bash scripts/playground.sh --dir /path/to/project

# Or curl-able (no repository clone needed)
curl -fsSL https://raw.githubusercontent.com/ovitrac/AdservioToolbox/main/scripts/playground.sh \
  | bash -s -- --dir /path/to/project

# Enterprise CloakMCP profile
bash scripts/playground.sh --dir /path/to/project --hardened

# Remove wiring
bash scripts/playground.sh --teardown --dir /path/to/project
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

# Or upgrade individually via pipx
pipx upgrade memctl
pipx upgrade cloakmcp
pipx upgrade adservio-toolbox

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
  memctl       0.17.x                  ✓  (pipx)
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
- **Deterministic incident remediation** — `toolboxctl rescue` diagnoses, recovers, verifies, and writes an audit-grade incident report.
- **Reproducible project wiring** — `scripts/playground.sh` sets up any directory with correct hook ordering, starter config, and teardown support.

---

## Subcommands

| Command | Purpose |
|---------|---------|
| `toolboxctl install [--fts fr\|en\|raw] [--upgrade]` | Install memctl + CloakMCP into current Python environment |
| `toolboxctl install --global` | Wire Claude Code globally (hooks + permissions + CLAUDE.md) |
| `toolboxctl install --uninstall` | Remove global wiring |
| `toolboxctl init [--force] [--fts ...] [--profile minimal\|dev\|playground]` | Wire `.claude/commands/`, config, CLAUDE.md block, manifest |
| `toolboxctl deinit [--force]` | Remove toolbox wiring (preserves `.memory/`, hooks, user content) |
| `toolboxctl update [--check] [--quiet] [--json] [--global] [--project]` | Upgrade memctl, CloakMCP, and toolbox via pipx/pip |
| `toolboxctl status` | Deterministic status report |
| `toolboxctl doctor [--strict\|--ci]` | Diagnostic check (all components, PATH, hooks, permissions, policy lint) |
| `toolboxctl eco [on\|off]` | Toggle eco mode |
| `toolboxctl env [--json]` | Export config as env vars |
| `toolboxctl playground [--clean]` | Isolated venv with smoke tests |
| `toolboxctl rescue [--dir DIR] [--from-backup [ID]] [--with-memory] [--memory-only] [--json]` | Guided secret recovery + memory health advisory |

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

## Secret Recovery

If a CloakMCP session crashes and files remain packed with `TAG-xxxx` placeholders, `toolboxctl rescue` provides a guided recovery workflow:

```bash
toolboxctl rescue               # diagnose + guided recovery in cwd
toolboxctl rescue --dir ./proj  # target a specific directory
toolboxctl rescue --dry-run     # preview without changes
toolboxctl rescue --from-backup # list available backups
toolboxctl rescue --with-memory      # include memory health advisory
toolboxctl rescue --memory-only      # memory checks only (skip secrets)
toolboxctl rescue --json --with-memory  # full diagnostic as JSON
```

Rescue diagnoses the state (stale session, residual tags, vault integrity), reports severity, asks for confirmation, then runs the appropriate `cloak recover`/`restore`/`verify` sequence. Each run writes an incident report (`.cloak-rescue-report.json`) for audit evidence.

`--with-memory` appends a read-only memory health advisory (via `memctl doctor/status/stats`). `--memory-only` runs memory checks without secret recovery. `--json` emits structured JSON to stdout for CI/support integration.

**Exit codes:** `0` = clean/recovered, `1` = dir missing, `2` = cloak missing, `3` = verification failed after remediation.

See `docs/cheat/L2.md` for the full recovery guide.

---

## Hook Installation

After `toolboxctl install --global`, CloakMCP hooks are wired globally. For per-project hooks, both sub-projects bundle their installer scripts in the PyPI wheel — no git clone required:

```bash
# CloakMCP hooks — automatic secret sanitization at session boundaries
bash "$(cloak scripts-path)/install_claude.sh"                       # secrets-only (5 hooks)
bash "$(cloak scripts-path)/install_claude.sh" --profile hardened     # + Bash safety + read guard (7 hooks)
bash "$(cloak scripts-path)/install_claude.sh" --uninstall            # remove hooks

# memctl hooks — eco mode (token-efficient retrieval)
bash "$(memctl scripts-path)/install_eco.sh" --db-root .memory        # eco hook + strategy + /eco
bash "$(memctl scripts-path)/uninstall_eco.sh"                        # remove eco (preserves .memory/)
```

See `/cheat 3` or `docs/cheat/L3.md` for the full list of installer scripts, profiles, and options.

---

## Try It — End-to-End Demo

**The best way to test the installation and discover how the toolbox works.**

The e2e script builds a self-contained demo project with fake secrets, CloakMCP hooks,
memctl memory, and a 7-challenge interactive stress test:

```bash
# 1. Build the demo (clean venv → install → demo project → hooks → 18 checks)
bash scripts/test-e2e.sh

# 2. Launch Claude Code inside the demo project
bash .e2e/default/launch.sh

# 3. Inside the Claude session, type:
#      execute CHALLENGE.md
#    Claude will walk you through all 7 challenges interactively.
```

Here is what a typical run looks like (7/7 PASS on a fresh install):

| # | Challenge | Result | Notes |
|---|-----------|--------|-------|
| 1 | Eco mode activation | PASS | memctl status confirms active, 2 STM items |
| 2 | Secret redaction | PASS | All 3 variables show `TAG-*` placeholders. No raw values visible |
| 3 | Memory recall | PASS | `memctl search` returns redacted inventory |
| 4 | Slash commands | PASS | `/cheat L1`, `/tldr cloakmcp`, `/why eco` all produce document-backed output |
| 5 | Write guard | PASS | `cloak-guard-write` blocked an AKIA\* key — rule `aws_access_keys`, severity critical |
| 6 | Audit trail | PASS | 4 events logged: 2× `session_pack`, 2× `guard_deny` with rule + severity |
| 7 | Backup exfiltration | PASS (no leak) | No raw secrets found. `.cloak-backups/` absent |

Every safety layer exercised in a live session — no documentation to read first.

```bash
# Standalone hook installer (for your own projects)
bash scripts/install-hooks.sh --dir /path/to/project
bash scripts/install-hooks.sh --dir /path/to/project --hardened
bash scripts/install-hooks.sh --dir /path/to/project --uninstall

# Cleanup
bash scripts/test-e2e.sh --clean
```

---

## Release Pipeline

Releases are automated via GitHub Actions. Pushing a `v*` tag triggers the workflow:

```bash
git tag -a v0.4.5 -m "Release 0.4.5"
git push origin v0.4.5
# → GitHub Actions builds and publishes the release automatically
```

The workflow (`.github/workflows/release.yml`):
1. Runs `scripts/build-release.sh` to produce release assets
2. Extracts the changelog section for that version
3. Creates a GitHub Release with all assets attached

**Published assets per release:**

| Asset | Purpose |
|-------|---------|
| `install.sh` | Bootstrap installer (Linux / macOS) |
| `install.ps1` | Bootstrap installer (Windows) |
| `adservio-toolbox-X.Y.Z.tar.gz` | Source archive |
| `SHA256SUMS` | Checksums for all assets |

Users install via `curl` from the release URL — no repository clone needed (see [Quick Install](#quick-install)).

For local builds (development or pre-release testing):

```bash
bash scripts/build-release.sh                  # build from pyproject.toml version
bash scripts/build-release.sh --version 0.4.0  # override version
bash scripts/build-release.sh --sign            # GPG-sign SHA256SUMS
bash scripts/build-release.sh --clean           # remove release/ directory
```

---

## Operational Guarantees

- **Idempotent installer** — `toolboxctl install` and `toolboxctl init` are safe to run repeatedly.
- **Deterministic status** — `toolboxctl status` output is stable and pasteable into issues.
- **Explicit config precedence** — CLI flags > env vars > TOML > compiled defaults.
- **Isolated playground validation** — `toolboxctl playground` tests in a clean venv, never touches your environment.
- **Zero coupling** — sub-projects are installed, not imported; no shared Python state.
- **Independent release cadence** — memctl, CloakMCP, and the toolbox version independently.
- **Capability-based installer** — detects Python, pip, venv and selects the best install track; never runs sudo.
- **Reversible global wiring** — `toolboxctl install --uninstall` cleanly removes hooks, permissions, and CLAUDE.md block.
- **Reversible project wiring** — `toolboxctl deinit` removes all toolbox artifacts while preserving `.memory/`, hooks, and user CLAUDE.md content.
- **Auto-updater** — `toolboxctl update` detects install method (pipx/pip) and upgrades all components; `--check` for dry-run version comparison.
- **CLAUDE.md injection** — `toolboxctl init` injects a marker-based block into project CLAUDE.md (non-destructive, idempotent, reversible).
- **Layer doctrine** — GLOBAL block is a safety seatbelt (CloakMCP only); PROJECT block is an overlay (references GLOBAL); no memctl guidance in either.
- **Profile-driven init** — `--profile minimal|dev|playground` controls project wiring content; profile recorded in manifest for scoped updates.
- **Policy lint** — `toolboxctl doctor` checks for doctrine violations; `--strict`/`--ci` promotes warnings to errors.
- **Scoped block refresh** — `toolboxctl update --global`/`--project` refreshes CLAUDE.md blocks without upgrading packages.
- **Document-ready** — `memctl[mcp,docs]` includes Office and PDF support; no extra install steps.

---

## Requirements

- Python 3.10+ (system Python is fine)
- Claude Code (`npm install -g @anthropic-ai/claude-code`)
- pipx (recommended, installed automatically by the bootstrap script)

## License

MIT — see [LICENSE](LICENSE).
