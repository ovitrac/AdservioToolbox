# First Session — Getting Started with the Adservio Toolbox

## Prerequisites

- Python 3.10+ installed (system Python is fine)
- Claude Code installed (`npm install -g @anthropic-ai/claude-code`)

## Step 1: Install the Toolbox

### Option A: One-liner (recommended)

```bash
curl -fsSL https://github.com/Adservio-Dev/AdservioToolbox/releases/download/v0.2.0/install.sh \
  -o install.sh && bash install.sh
```

This installs memctl, CloakMCP, and toolboxctl via pipx, wires Claude Code globally, and runs diagnostics.

### Option B: Manual (pipx)

```bash
pipx install memctl[mcp,docs]
pipx install cloakmcp
pipx install adservio-toolbox
toolboxctl install --global
```

### Option C: Development mode

```bash
git clone <repo-url> AdservioToolbox
cd AdservioToolbox
pip install -e .
toolboxctl install
toolboxctl install --global
```

## Step 2: Verify Installation

```bash
toolboxctl doctor

# Expected:
#   Python       3.12.x            ✓
#   pipx         1.4.x             ✓
#   Claude Code  2.x.x             ✓
#   memctl       0.15.x            ✓  (pipx)
#   cloakmcp     0.8.x             ✓  (pipx)
#   toolboxctl   0.2.0             ✓  (pipx)
#   PATH         cloak, memctl     ✓
#   Global hooks ~/.claude/        ✓  CloakMCP secrets-only
#   Permissions  cloak *, memctl * ✓
#   CLAUDE.md    ~/.claude/        ✓  Toolbox block present
```

## Step 3: Initialize Your Project

```bash
# Go to your project
cd /path/to/your-project

# Initialize memory workspace
memctl init

# Wire Claude Code integration
toolboxctl init

# This creates:
#   .claude/commands/{cheat,tldr,eco,why,how}.md  — slash commands
#   .claude/settings.json                          — MCP server registrations
#   .adservio-toolbox.toml                         — toolbox configuration
```

## Step 4: Verify Project Setup

```bash
toolboxctl status

# Expected:
#   Component   Value
#   ──────────  ────────────────────
#   toolboxctl  0.2.0
#   Python      3.12.x
#   memctl      0.15.x
#   CloakMCP    0.8.x
#   Config      .adservio-toolbox.toml
#   Eco mode    off
#   Commands    /cheat, /consolidate, /diff, /eco, /export, ...
```

## Step 5: Start a Claude Code Session

```bash
# Inject toolbox config as env vars (so memctl/CloakMCP read them)
eval "$(toolboxctl env)"

# Start Claude Code
claude
```

### Slash commands available in-session:

| Command | What it does |
|---------|-------------|
| `/cheat` | Daily essentials (L1 cheat sheet) |
| `/cheat 2` | Workflows: eco, memctl, CloakMCP |
| `/cheat 3` | Advanced: MCP, policies, hooks, release pipeline |
| `/tldr memctl` | memctl quick reference |
| `/tldr cloakmcp` | CloakMCP quick reference |
| `/eco` | Show/toggle eco mode |
| `/why <topic>` | Explain rationale for a design decision |
| `/how <task>` | Step-by-step operational guide |

## Step 6: Install Per-Project Hooks (Optional)

Global CloakMCP hooks are already active (from Step 1). For per-project hooks:

### CloakMCP hooks (secret protection)

```bash
bash "$(cloak scripts-path)/install_claude.sh"                       # secrets-only (5 hooks)
bash "$(cloak scripts-path)/install_claude.sh" --profile hardened     # + Bash safety + read guard (7 hooks)

# To uninstall later:
bash "$(cloak scripts-path)/install_claude.sh" --uninstall
```

### memctl hooks (eco mode)

```bash
# Install eco mode (hook + strategy + /eco slash command)
bash "$(memctl scripts-path)/install_eco.sh" --db-root .memory

# To uninstall later:
bash "$(memctl scripts-path)/uninstall_eco.sh"
```

> **Note:** `toolboxctl init` (Step 3) already registered the memctl MCP server in
> `.claude/settings.json`. You only need `install_mcp.sh` if you want to
> register memctl globally (`~/.claude/settings.json`) or for Claude Desktop:
> `bash "$(memctl scripts-path)/install_mcp.sh"`

### Or use the standalone hook installer

```bash
bash scripts/install-hooks.sh --dir /path/to/project
bash scripts/install-hooks.sh --dir /path/to/project --hardened
```

## Step 7: Use the Safe RAG Loop

The recommended pattern for secure AI-assisted development:

```bash
# 1. Before working — sanitize secrets (or automatic if hooks installed)
cloak pack --policy .cloak/policy.yaml --dir src/

# 2. Work with Claude Code (secrets are TAG-xxx, safe to expose)
claude

# 3. Store findings in memory (from within the session or CLI)
echo "Decision: use JWT with RS256" | memctl pull --title "auth decision" --tags "auth,architecture"

# 4. After session — restore secrets (or automatic if hooks installed)
cloak unpack --dir src/

# 5. Next session — recall context
memctl push "authentication" --source src/auth/
```

With CloakMCP hooks installed, steps 1 and 4 are automatic (SessionStart/SessionEnd).

## Step 8: Enable Eco Mode (Optional)

```bash
# Enable globally via toolbox
toolboxctl eco on

# Verify
toolboxctl eco
# → Eco mode is currently: on

# Disable when needed
toolboxctl eco off
```

## What's Next?

- `/cheat 2` — workflow patterns (safe RAG loop, memory tiers, policy config)
- `/cheat 3` — advanced topics (MCP servers, policy inheritance, hooks, release pipeline)
- `toolboxctl playground` — test everything in an isolated venv
- Each project has its own README with full documentation:
  - **memctl**: `pip show memctl` → Homepage link, or `memctl --help`
  - **CloakMCP**: `pip show cloakmcp` → Homepage link, or `cloak --help`
