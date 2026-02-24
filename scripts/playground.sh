#!/usr/bin/env bash
# Per-project playground setup for the Adservio Claude Code Toolbox.
#
# Sets up any project directory as a fully-wired toolbox playground:
# init + CloakMCP hooks + memctl eco hooks + starter CLAUDE.md + verification.
#
# Curl-able:
#   curl -fsSL https://raw.githubusercontent.com/ovitrac/AdservioToolbox/main/scripts/playground.sh \
#     | bash -s -- --dir /path/to/project
#
# Author: Olivier Vitrac, PhD, HDR | olivier.vitrac@adservio.fr | Adservio
# ---

set -euo pipefail

TOTAL_STEPS=7

# ---------------------------------------------------------------------------
# ANSI helpers (TTY-aware, macOS-safe)
# ---------------------------------------------------------------------------

if [ -t 1 ]; then
    _B="\033[1m"    _R="\033[0m"
    _GREEN="\033[32m" _YELLOW="\033[33m" _RED="\033[31m" _CYAN="\033[36m"
else
    _B="" _R="" _GREEN="" _YELLOW="" _RED="" _CYAN=""
fi

step()  { printf "${_B}${_CYAN}[STEP %s/%s]${_R} %s\n" "$1" "$TOTAL_STEPS" "$2"; }
ok()    { printf "${_GREEN}[OK]${_R}    %s\n" "$1"; }
info()  { printf "${_CYAN}[INFO]${_R}  %s\n" "$1"; }
warn()  { printf "${_YELLOW}[WARN]${_R}  %s\n" "$1"; }
err()   { printf "${_RED}[ERROR]${_R} %s\n" "$1" >&2; }

# ---------------------------------------------------------------------------
# Arguments
# ---------------------------------------------------------------------------

ARG_DIR=""
ARG_HARDENED=false
ARG_DB_ROOT=".memory"
ARG_SKIP_HOOKS=false
ARG_FORCE=false
ARG_TEARDOWN=false
ARG_DRY_RUN=false

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Per-project setup for the Adservio Claude Code Toolbox.
Sets up toolbox wiring (init + hooks + starter CLAUDE.md) in a project directory.

Options:
  --dir <path>      Target project directory (default: current directory)
  --hardened        Use CloakMCP hardened profile (enterprise policy, 26 rules)
  --db-root <path>  memctl database root (default: .memory)
  --skip-hooks      Skip hook installation (init + CLAUDE.md only)
  --force           Overwrite existing files
  --teardown        Remove playground wiring (preserves .memory/ and user config)
  --dry-run         Preview actions without executing
  -h, --help        Show this help

Examples:
  $(basename "$0")                                    # setup in cwd
  $(basename "$0") --dir ~/projects/my-app            # specific directory
  $(basename "$0") --hardened                         # enterprise CloakMCP profile
  $(basename "$0") --teardown --dir ~/projects/my-app # remove wiring
  $(basename "$0") --dry-run                          # preview

Curl one-liner:
  curl -fsSL https://raw.githubusercontent.com/ovitrac/AdservioToolbox/main/scripts/playground.sh \\
    | bash -s -- --dir /path/to/project
EOF
    exit 0
}

while [ $# -gt 0 ]; do
    case "$1" in
        --dir)
            shift
            if [ $# -eq 0 ]; then err "--dir requires a path argument"; exit 1; fi
            ARG_DIR="$1"
            ;;
        --hardened)     ARG_HARDENED=true ;;
        --db-root)
            shift
            if [ $# -eq 0 ]; then err "--db-root requires a path argument"; exit 1; fi
            ARG_DB_ROOT="$1"
            ;;
        --skip-hooks)   ARG_SKIP_HOOKS=true ;;
        --force)        ARG_FORCE=true ;;
        --teardown)     ARG_TEARDOWN=true ;;
        --dry-run)      ARG_DRY_RUN=true ;;
        -h|--help)      usage ;;
        *)              err "Unknown argument: $1"; exit 1 ;;
    esac
    shift
done

# Resolve target directory
if [ -n "$ARG_DIR" ]; then
    TARGET_DIR="$ARG_DIR"
else
    TARGET_DIR="$(pwd)"
fi

# macOS-safe absolute path resolution (no readlink -f)
_realpath() {
    (cd "$1" 2>/dev/null && pwd)
}

# ===========================================================================
# TEARDOWN PATH
# ===========================================================================

if $ARG_TEARDOWN; then
    printf '%b\n' "\n${_B}Adservio Toolbox — Per-Project Teardown${_R}\n"

    # Validate target
    if [ ! -d "$TARGET_DIR" ]; then
        err "Directory does not exist: $TARGET_DIR"
        exit 1
    fi
    TARGET_DIR="$(_realpath "$TARGET_DIR")"
    info "Target: $TARGET_DIR"

    # Step 3: Remove CloakMCP hooks
    step 3 "Remove CloakMCP hooks"
    CLOAK_SCRIPTS=$(cloak scripts-path 2>/dev/null || true)
    if [ -n "$CLOAK_SCRIPTS" ] && [ -f "$CLOAK_SCRIPTS/install_claude.sh" ]; then
        DRY_FLAG=""
        if $ARG_DRY_RUN; then DRY_FLAG="--dry-run"; fi
        if $ARG_DRY_RUN; then
            info "[dry-run] Would run: (cd $TARGET_DIR && bash $CLOAK_SCRIPTS/install_claude.sh --uninstall)"
        else
            (cd "$TARGET_DIR" && bash "$CLOAK_SCRIPTS/install_claude.sh" --uninstall $DRY_FLAG) || warn "CloakMCP uninstall returned non-zero"
        fi
        ok "CloakMCP hooks removed"
    else
        warn "CloakMCP scripts-path not available, skipping."
    fi

    # Step 4: Remove memctl eco hooks
    step 4 "Remove memctl eco hooks"
    MEMCTL_SCRIPTS=$(memctl scripts-path 2>/dev/null || true)
    if [ -n "$MEMCTL_SCRIPTS" ] && [ -f "$MEMCTL_SCRIPTS/uninstall_eco.sh" ]; then
        DRY_FLAG=""
        if $ARG_DRY_RUN; then DRY_FLAG="--dry-run"; fi
        if $ARG_DRY_RUN; then
            info "[dry-run] Would run: (cd $TARGET_DIR && bash $MEMCTL_SCRIPTS/uninstall_eco.sh)"
        else
            (cd "$TARGET_DIR" && bash "$MEMCTL_SCRIPTS/uninstall_eco.sh" $DRY_FLAG) || warn "memctl eco uninstall returned non-zero"
        fi
        ok "memctl eco hooks removed"
    else
        warn "memctl scripts-path not available, skipping."
    fi

    # Step 5: Remove .adservio-toolbox.toml
    step 5 "Remove toolbox config"
    CONFIG_FILE="$TARGET_DIR/.adservio-toolbox.toml"
    if [ -f "$CONFIG_FILE" ]; then
        if $ARG_DRY_RUN; then
            info "[dry-run] Would remove: $CONFIG_FILE"
        else
            rm -f "$CONFIG_FILE"
            ok "Removed $CONFIG_FILE"
        fi
    else
        info "No config file found, skipping."
    fi

    # Step 6: Remove .claude/commands/ (toolbox-managed only)
    step 6 "Remove toolbox slash commands"
    COMMANDS_DIR="$TARGET_DIR/.claude/commands"
    if [ -d "$COMMANDS_DIR" ]; then
        # Remove only known toolbox commands
        TOOLBOX_CMDS="cheat.md tldr.md eco.md why.md how.md"
        REMOVED=0
        for cmd_file in $TOOLBOX_CMDS; do
            if [ -f "$COMMANDS_DIR/$cmd_file" ]; then
                if $ARG_DRY_RUN; then
                    info "[dry-run] Would remove: $COMMANDS_DIR/$cmd_file"
                else
                    rm -f "$COMMANDS_DIR/$cmd_file"
                fi
                REMOVED=$((REMOVED + 1))
            fi
        done
        # Remove directory only if empty
        if ! $ARG_DRY_RUN && [ -d "$COMMANDS_DIR" ] && [ -z "$(ls -A "$COMMANDS_DIR" 2>/dev/null)" ]; then
            rmdir "$COMMANDS_DIR"
            info "Removed empty .claude/commands/"
        fi
        ok "Removed $REMOVED toolbox command(s)"
    else
        info "No .claude/commands/ found, skipping."
    fi

    # Step 7: Summary
    step 7 "Teardown summary"
    echo ""
    printf '%b\n' "${_B}=== Teardown Summary ===${_R}"
    printf "  Target:    %s\n" "$TARGET_DIR"
    if $ARG_DRY_RUN; then
        info "Dry run complete. No changes were made."
    else
        info "Toolbox wiring removed."
        info "Preserved: .memory/ database, .claude/settings.json (non-toolbox entries)"
        info "To fully remove memory: rm -rf $TARGET_DIR/.memory"
    fi
    exit 0
fi

# ===========================================================================
# SETUP PATH
# ===========================================================================

printf '%b\n' "\n${_B}Adservio Toolbox — Per-Project Setup${_R}\n"

# ===========================================================================
# STEP 1: Verify prerequisites
# ===========================================================================

step 1 "Verify prerequisites"

MISSING=0
for tool in toolboxctl memctl cloak; do
    if command -v "$tool" >/dev/null 2>&1; then
        ok "$tool: $(command -v "$tool")"
    else
        err "$tool not found in PATH"
        case "$tool" in
            toolboxctl) info "Install: pipx install adservio-toolbox" ;;
            memctl)     info "Install: pipx install memctl[mcp,docs]" ;;
            cloak)      info "Install: pipx install cloakmcp" ;;
        esac
        MISSING=$((MISSING + 1))
    fi
done

if [ "$MISSING" -gt 0 ]; then
    err "$MISSING required tool(s) missing."
    info "Quick install: curl -fsSL https://github.com/ovitrac/AdservioToolbox/releases/latest/download/install.sh | bash"
    exit 2
fi

# ===========================================================================
# STEP 2: Validate target directory
# ===========================================================================

step 2 "Validate target directory: $TARGET_DIR"

if [ ! -d "$TARGET_DIR" ]; then
    if $ARG_DRY_RUN; then
        info "[dry-run] Would create directory: $TARGET_DIR"
    else
        mkdir -p "$TARGET_DIR"
        ok "Created directory: $TARGET_DIR"
    fi
fi

if [ -d "$TARGET_DIR" ]; then
    TARGET_DIR="$(_realpath "$TARGET_DIR")"
fi
ok "Target: $TARGET_DIR"

# ===========================================================================
# STEP 3: toolboxctl init
# ===========================================================================

step 3 "Initialize toolbox configuration"

INIT_ARGS=""
if $ARG_FORCE; then INIT_ARGS="--force"; fi

if [ -f "$TARGET_DIR/.adservio-toolbox.toml" ] && ! $ARG_FORCE; then
    info "Config already exists: $TARGET_DIR/.adservio-toolbox.toml (use --force to overwrite)"
else
    if $ARG_DRY_RUN; then
        info "[dry-run] Would run: (cd $TARGET_DIR && toolboxctl init --profile playground $INIT_ARGS)"
    else
        (cd "$TARGET_DIR" && toolboxctl init --profile playground $INIT_ARGS)
        ok "toolboxctl init completed"
    fi
fi

# ===========================================================================
# STEP 4: CloakMCP hooks (MUST be first — replaces entire hooks key)
# ===========================================================================

if $ARG_SKIP_HOOKS; then
    step 4 "CloakMCP hooks — SKIPPED (--skip-hooks)"
else
    step 4 "Install CloakMCP hooks"

    CLOAK_SCRIPTS=$(cloak scripts-path 2>/dev/null || true)

    if [ -z "$CLOAK_SCRIPTS" ] || [ ! -d "$CLOAK_SCRIPTS" ]; then
        err "Could not resolve CloakMCP scripts-path."
        err "Ensure cloakmcp >= 0.6.3 is installed: pipx install cloakmcp"
        exit 1
    fi

    CLOAK_PROFILE="secrets-only"
    if $ARG_HARDENED; then
        CLOAK_PROFILE="hardened"
    fi

    info "Profile: $CLOAK_PROFILE"
    if $ARG_DRY_RUN; then
        info "[dry-run] Would run: (cd $TARGET_DIR && bash $CLOAK_SCRIPTS/install_claude.sh --profile $CLOAK_PROFILE)"
    else
        (cd "$TARGET_DIR" && bash "$CLOAK_SCRIPTS/install_claude.sh" --profile "$CLOAK_PROFILE")
    fi
    ok "CloakMCP hooks installed ($CLOAK_PROFILE)"
fi

# ===========================================================================
# STEP 5: memctl eco hooks (appends to UserPromptSubmit)
# ===========================================================================

if $ARG_SKIP_HOOKS; then
    step 5 "memctl eco hooks — SKIPPED (--skip-hooks)"
else
    step 5 "Install memctl eco hooks"

    MEMCTL_SCRIPTS=$(memctl scripts-path 2>/dev/null || true)

    if [ -z "$MEMCTL_SCRIPTS" ] || [ ! -d "$MEMCTL_SCRIPTS" ]; then
        err "Could not resolve memctl scripts-path."
        err "Ensure memctl >= 0.12.3 is installed: pipx install memctl[mcp,docs]"
        exit 1
    fi

    info "DB root: $ARG_DB_ROOT"
    if $ARG_DRY_RUN; then
        info "[dry-run] Would run: (cd $TARGET_DIR && bash $MEMCTL_SCRIPTS/install_eco.sh --db-root $ARG_DB_ROOT)"
    else
        (cd "$TARGET_DIR" && bash "$MEMCTL_SCRIPTS/install_eco.sh" --db-root "$ARG_DB_ROOT")
    fi
    ok "memctl eco hooks installed"
fi

# ===========================================================================
# STEP 6: Starter CLAUDE.md
# ===========================================================================

step 6 "Project CLAUDE.md"

CLAUDE_MD="$TARGET_DIR/CLAUDE.md"

# toolboxctl init (step 3) already injected the toolbox block.
# If user wants a starter header, create it only if file is new.
if $ARG_DRY_RUN; then
    info "[dry-run] Would ensure CLAUDE.md has toolbox block"
elif [ ! -f "$CLAUDE_MD" ]; then
    PROJECT_NAME=$(basename "$TARGET_DIR")
    printf "# CLAUDE.md — %s\n\n" "$PROJECT_NAME" > "$CLAUDE_MD"
    printf "*Add your project-specific instructions below.*\n\n" >> "$CLAUDE_MD"
    # Re-run init to inject block into the new file
    (cd "$TARGET_DIR" && toolboxctl init --profile playground --force) >/dev/null 2>&1
    ok "Created CLAUDE.md with toolbox block"
else
    info "CLAUDE.md already exists (toolbox block injected by init)"
fi

# ===========================================================================
# STEP 7: Verify + activation hints
# ===========================================================================

step 7 "Verify installation"

PASS=0
FAIL=0

_check_file() {
    local label="$1"
    local path="$2"
    if $ARG_DRY_RUN; then
        info "[dry-run] Would check: $label"
        return 0
    fi
    if [ -f "$path" ]; then
        ok "PASS: $label"
        PASS=$((PASS + 1))
    else
        err "FAIL: $label ($path not found)"
        FAIL=$((FAIL + 1))
    fi
}

_check_dir() {
    local label="$1"
    local path="$2"
    if $ARG_DRY_RUN; then
        info "[dry-run] Would check: $label"
        return 0
    fi
    if [ -d "$path" ]; then
        ok "PASS: $label"
        PASS=$((PASS + 1))
    else
        err "FAIL: $label ($path not found)"
        FAIL=$((FAIL + 1))
    fi
}

_check_file ".adservio-toolbox.toml"    "$TARGET_DIR/.adservio-toolbox.toml"
_check_dir  ".claude/commands/"         "$TARGET_DIR/.claude/commands"
_check_file "CLAUDE.md"                 "$TARGET_DIR/CLAUDE.md"

if ! $ARG_SKIP_HOOKS; then
    _check_file ".claude/settings.json" "$TARGET_DIR/.claude/settings.json"
fi

# Summary banner
echo ""
printf '%b\n' "${_B}=== Per-Project Setup Summary ===${_R}"
if $ARG_DRY_RUN; then
    info "Dry run complete. No changes were made."
else
    printf "  Target:    %s\n" "$TARGET_DIR"
    if ! $ARG_SKIP_HOOKS; then
        CLOAK_PROFILE="secrets-only"
        if $ARG_HARDENED; then CLOAK_PROFILE="hardened"; fi
        printf "  CloakMCP:  %s\n" "$CLOAK_PROFILE"
        printf "  memctl:    db-root=%s\n" "$ARG_DB_ROOT"
    else
        printf "  Hooks:     skipped\n"
    fi
    printf "  Checks:    ${_GREEN}%d passed${_R}" "$PASS"
    if [ "$FAIL" -gt 0 ]; then
        printf ", ${_RED}%d failed${_R}" "$FAIL"
    fi
    echo ""

    if [ "$FAIL" -gt 0 ]; then
        err "$FAIL verification check(s) failed."
        exit 1
    fi

    echo ""
    info "Activation steps:"
    printf "  ${_CYAN}1.${_R} cd %s\n" "$TARGET_DIR"
    printf "  ${_CYAN}2.${_R} memctl init              # initialize memory database\n"
    printf "  ${_CYAN}3.${_R} eval \"\$(toolboxctl env)\"  # inject config into shell\n"
    printf "  ${_CYAN}4.${_R} claude                    # start Claude Code session\n"
    echo ""
    ok "Per-project setup complete."
fi
