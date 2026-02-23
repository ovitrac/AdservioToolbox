# Changelog

All notable changes to the Adservio Claude Code Toolbox are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] — 2026-02-23

### Added

- **CloakMCP 0.8.2 integration:**
  - MCP server template updated to `cloak serve` (auto-discovers `.cloak/policy.yaml`)
  - Policy anchoring via `cloak policy use` in `install-hooks.sh` (version-gated, falls back to `CLOAK_POLICY` env var for < 0.8.2)
  - `--policy` flag for `install-hooks.sh` (override policy source)
  - `fail_closed` config key (`[cloak]` section) mapped to `CLOAK_FAIL_CLOSED` env var
  - Bundled policies: `mcp_policy.yaml` (10 rules) default, `mcp_policy_enterprise.yaml` (26 rules) for `--hardened`
- **memctl 0.16.0 integration:**
  - Documented `memctl eco on/off/status` as valid eco toggle path
  - Documented `memory_eco` MCP tool for eco toggle via MCP

### Changed

- MCP server registration for CloakMCP: `cloak-mcp-server` replaced by `cloak serve`
- `install-hooks.sh` now has 7 steps (added policy anchoring step)
- E2e test uses CloakMCP bundled policy when available (falls back to inline 5-rule policy)
- Default memctl install spec: `memctl[mcp]` → `memctl[mcp,docs]` — Office and PDF document support out of the box
- Updated docs: L3 cheat sheet, demo CLAUDE.md, CHALLENGE.md

### Fixed

- **Global permissions**: added `Bash(toolboxctl *)` — `toolboxctl eco on` no longer requires approval
- **Global permissions**: added `Read` and `Grep` — slash commands (`/cheat`, `/tldr`, etc.) no longer trigger per-directory approval prompts
- **CLAUDE.md block**: clarified `memory_recall`/`memory_inspect` as MCP-only tools; added CLI equivalents (`memctl search`, `memctl show`) to prevent `memctl recall` misuse
- **Demo CLAUDE.md**: replaced non-existent `recall` subcommand with valid `search, show, eco, status`
- **Challenge 5**: replaced literal AKIA key (redacted by CloakMCP during sessions) with instruction to generate one — guard-write now testable
- **Challenge 3**: clarified MCP tools vs CLI commands with explicit fallback path

## [0.2.1] — 2026-02-23

### Fixed

- **Doctor false negatives**: `toolboxctl doctor` now detects memctl and CloakMCP via CLI (`--version`) instead of `pip show`, fixing false "not installed" reports when tools are in separate pipx venvs
- **Version mismatch**: `toolbox/__init__.py` now tracks `pyproject.toml` version
- **Install source**: `install.sh` installs adservio-toolbox from the GitHub release tarball (not PyPI), with local file fallback and proper upgrade logic
- **GitHub URLs**: Updated repository references from `Adservio-Dev` to `ovitrac`

## [0.2.0] — 2026-02-23

### Added

- **Curl-installable bootstrap** (`scripts/install.sh`):
  - One-liner install with SHA256 checksum verification
  - Capability-based track selection: Track A (pipx) or Track B (pip --user)
  - Distro-aware error messages (Debian, RHEL, Alpine, Arch, SUSE, macOS)
  - Probes Python, pip, and venv modules before selecting install method
  - Never runs `sudo` — prints instructions and lets the user decide
  - Flags: `--version`, `--skip-global`, `--upgrade`, `--uninstall`, `--dry-run`
- **Windows PowerShell skeleton** (`scripts/install.ps1`):
  - Same parameter structure as install.sh
  - Manual instructions provided; full support planned for v0.3.0
- **Global Claude Code wiring** (`toolboxctl install --global`):
  - CloakMCP hooks installed globally in `~/.claude/settings.json` (secrets-only profile, 5 hooks)
  - `Bash(cloak *)` and `Bash(memctl *)` permissions in `~/.claude/settings.local.json`
  - Behavioral rules in `~/.claude/CLAUDE.md` (delimited block, merge strategy)
  - All operations idempotent and reversible via `toolboxctl install --uninstall`
  - Hook entries tagged with `"_source": "adservio-toolbox"` for safe identification
- **Diagnostic command** (`toolboxctl doctor`):
  - Checks: Python, pipx, Claude Code, memctl, CloakMCP, toolboxctl, PATH, global hooks, permissions, CLAUDE.md block
  - Exit codes: 0 = all green, 1 = warnings, 2 = critical missing
  - Detects install method (pipx/pip/system) via path inspection
- **Release pipeline** (`scripts/build-release.sh`):
  - Builds sdist (tar.gz), zip archive, copies install scripts
  - Generates SHA256SUMS with optional GPG signature (`--sign`)
  - Flags: `--version`, `--sign`, `--dry-run`, `--clean`
- **GitHub Actions workflow** (`.github/workflows/release.yml`):
  - Triggered on tag push (`v*`) or manual `workflow_dispatch`
  - Builds assets, extracts changelog, creates GitHub Release
  - Pre-release flag support for manual dispatch
- **End-to-end test** (`scripts/test-e2e.sh`):
  - Full 9-step pipeline: pre-flight checks, clean venv, editable install, demo project with fake secrets, CloakMCP + memctl hook installation, 17 automated verifications
  - Demo project includes `CHALLENGE.md` with 7 challenges for interactive stress testing
  - Bundled `docs/` (cheat sheets, TLDR cards, workflows) so slash commands stay within demo scope
  - Memory pre-seeded via `memctl pull` (2 demo entries)
  - One-command launcher (`bash .e2e/launch.sh`)
  - Arguments: `--clean`, `--skip-install`, `--dry-run`, `-h`
- **Standalone hook installer** (`scripts/install-hooks.sh`):
  - 6-step installer for any project directory
  - CloakMCP-first ordering enforced (CloakMCP replaces hooks, memctl appends)
  - Arguments: `--dir`, `--hardened`, `--db-root`, `--dry-run`, `--uninstall`, `-h`
- **Global Claude Code permissions** in `toolboxctl install`:
  - Injects `Bash(cloak *)` and `Bash(memctl *)` into `~/.claude/settings.local.json`
  - Eliminates per-command authorization prompts across all projects
  - Idempotent: no duplicates on re-run
- **New module** `toolbox/global_wiring.py`:
  - Manages `~/.claude/` directory: hooks, permissions, CLAUDE.md
  - Merge strategy: CloakMCP hooks merged into existing hooks (not replaced)
  - CLAUDE.md managed via `<!-- ADSERVIO_TOOLBOX BEGIN -->` / `<!-- END -->` markers
- **New module** `toolbox/doctor.py`:
  - Diagnostic checks for all components and global wiring
  - Platform-aware (detects OS, install method)

### Changed

- `scripts/install.sh` now uses capability-based track selection (pip + venv → pipx; pip only → pip --user)
- `scripts/install.sh` no longer runs `sudo` — prints distro-specific instructions instead
- `pyproject.toml` license field updated to SPDX string format (setuptools deprecation fix)
- Documentation updated: README, cheat sheets (L1/L2/L3), TLDR cards, workflow guide

### Fixed

- Memory seeding uses `memctl pull` (stdin) instead of `memctl push` (which requires `--source` files)

## [0.1.0] — 2026-02-22

### Added

- **CLI entrypoint** (`toolboxctl`) with six subcommands:
  - `install` — install memctl + CloakMCP into current Python environment
  - `init` — wire `.claude/commands/`, create `.adservio-toolbox.toml`
  - `status` — deterministic status report (pasteable in issues)
  - `eco` — toggle eco mode (on/off/show)
  - `env` — export config as shell env vars or JSON
  - `playground` — isolated venv with smoke tests
- **Configuration system** (`.adservio-toolbox.toml`):
  - TOML reader with `tomllib` (3.11+) / `tomli` fallback (3.10)
  - Env var bridge: config values map to `ADSERVIO_ECO`, `MEMCTL_*`, `CLOAK_*`
  - Precedence: CLI flags > env vars > config file > compiled defaults
- **Slash commands** for Claude Code:
  - `/cheat [L1|L2|L3]` — leveled cheat sheets
  - `/tldr [topic]` — concise reference cards
  - `/eco [on|off]` — eco mode display and toggle
  - `/why <topic>` — rationale and invariant explanations
  - `/how <task>` — step-by-step operational guides
- **Documentation**:
  - Cheat sheets: L1 (daily), L2 (workflows), L3 (advanced)
  - TLDR cards: claude-code, toolboxctl, memctl, cloakmcp, eco
  - Workflow: first-session getting started guide
- **MCP server registrations** in `.claude/settings.json` for memctl and CloakMCP
- **Eco mode**: installed but inactive by default, toggleable globally or per-session
