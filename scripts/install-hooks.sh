#!/usr/bin/env bash
# Standalone hook installer for the Adservio Claude Code Toolbox.
#
# Installs CloakMCP hooks + memctl eco hooks into any project directory.
# Requires toolboxctl, memctl, and cloak to be in PATH.
#
# Critical ordering: CloakMCP hooks REPLACE the entire "hooks" key in
# .claude/settings.json. memctl eco APPENDS to UserPromptSubmit, preserving
# existing hooks. Therefore CloakMCP must always be installed first.
#
# Author: Olivier Vitrac, PhD, HDR | olivier.vitrac@adservio.fr | Adservio
# ---

set -euo pipefail

TOTAL_STEPS=6

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
ARG_DRY_RUN=false
ARG_UNINSTALL=false

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Install CloakMCP + memctl eco hooks into a project directory.

Options:
  --dir <path>      Target project directory (default: current directory)
  --hardened        Use CloakMCP hardened profile (adds Bash safety guard)
  --db-root <path>  memctl database root (default: .memory)
  --dry-run         Preview actions without executing (passed through to installers)
  --uninstall       Remove all hooks from the target directory
  -h, --help        Show this help

Examples:
  $(basename "$0")                          # install in cwd
  $(basename "$0") --dir /path/to/project   # install in specific dir
  $(basename "$0") --hardened               # hardened CloakMCP profile
  $(basename "$0") --uninstall              # remove hooks
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
        --dry-run)      ARG_DRY_RUN=true ;;
        --uninstall)    ARG_UNINSTALL=true ;;
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
# STEP 1: Verify required tools in PATH
# ===========================================================================

step 1 "Verify required tools"

MISSING=0
for tool in toolboxctl memctl cloak; do
    if command -v "$tool" >/dev/null 2>&1; then
        ok "$tool: $(command -v "$tool")"
    else
        err "$tool not found in PATH"
        MISSING=$((MISSING + 1))
    fi
done

if [ "$MISSING" -gt 0 ]; then
    err "$MISSING required tool(s) missing. Install via: toolboxctl install"
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

TARGET_DIR="$(_realpath "$TARGET_DIR")"
ok "Target: $TARGET_DIR"

# ===========================================================================
# STEP 3: Run toolboxctl init if needed
# ===========================================================================

step 3 "Ensure toolbox configuration"

if [ -f "$TARGET_DIR/.adservio-toolbox.toml" ]; then
    info "Config already exists: $TARGET_DIR/.adservio-toolbox.toml"
else
    info "Running toolboxctl init ..."
    if $ARG_DRY_RUN; then
        info "[dry-run] Would run: (cd $TARGET_DIR && toolboxctl init)"
    else
        (cd "$TARGET_DIR" && toolboxctl init)
        ok "toolboxctl init completed"
    fi
fi

# ===========================================================================
# Uninstall path
# ===========================================================================

if $ARG_UNINSTALL; then
    step 4 "Uninstall CloakMCP hooks"

    CLOAK_SCRIPTS=$(cloak scripts-path 2>/dev/null || true)
    if [ -n "$CLOAK_SCRIPTS" ] && [ -f "$CLOAK_SCRIPTS/install_claude.sh" ]; then
        DRY_FLAG=""
        if $ARG_DRY_RUN; then DRY_FLAG="--dry-run"; fi
        info "Running CloakMCP uninstall ..."
        (cd "$TARGET_DIR" && bash "$CLOAK_SCRIPTS/install_claude.sh" --uninstall $DRY_FLAG)
        ok "CloakMCP hooks removed"
    else
        warn "CloakMCP scripts-path not available, skipping."
    fi

    step 5 "Uninstall memctl eco hooks"

    MEMCTL_SCRIPTS=$(memctl scripts-path 2>/dev/null || true)
    if [ -n "$MEMCTL_SCRIPTS" ] && [ -f "$MEMCTL_SCRIPTS/uninstall_eco.sh" ]; then
        DRY_FLAG=""
        if $ARG_DRY_RUN; then DRY_FLAG="--dry-run"; fi
        info "Running memctl eco uninstall ..."
        (cd "$TARGET_DIR" && bash "$MEMCTL_SCRIPTS/uninstall_eco.sh" $DRY_FLAG)
        ok "memctl eco hooks removed"
    else
        warn "memctl scripts-path not available, skipping."
    fi

    step 6 "Post-uninstall verification"

    if ! $ARG_DRY_RUN; then
        info "Running toolboxctl status ..."
        (cd "$TARGET_DIR" && toolboxctl status) || true
    fi

    ok "Uninstall complete."
    exit 0
fi

# ===========================================================================
# STEP 4: CloakMCP hooks (MUST be first — replaces entire hooks key)
# ===========================================================================

step 4 "Install CloakMCP hooks"

CLOAK_SCRIPTS=$(cloak scripts-path 2>/dev/null || true)

if [ -z "$CLOAK_SCRIPTS" ] || [ ! -d "$CLOAK_SCRIPTS" ]; then
    err "Could not resolve CloakMCP scripts-path."
    err "Ensure cloakmcp >= 0.6.3 is installed: pip install cloakmcp"
    exit 1
fi

CLOAK_PROFILE="secrets-only"
if $ARG_HARDENED; then
    CLOAK_PROFILE="hardened"
fi

CLOAK_ARGS="--profile $CLOAK_PROFILE"
if $ARG_DRY_RUN; then
    CLOAK_ARGS="$CLOAK_ARGS --dry-run"
fi

info "Profile: $CLOAK_PROFILE"
info "Installing CloakMCP hooks ..."
(cd "$TARGET_DIR" && bash "$CLOAK_SCRIPTS/install_claude.sh" $CLOAK_ARGS)
ok "CloakMCP hooks installed ($CLOAK_PROFILE)"

# ===========================================================================
# STEP 5: memctl eco hooks (appends to UserPromptSubmit)
# ===========================================================================

step 5 "Install memctl eco hooks"

MEMCTL_SCRIPTS=$(memctl scripts-path 2>/dev/null || true)

if [ -z "$MEMCTL_SCRIPTS" ] || [ ! -d "$MEMCTL_SCRIPTS" ]; then
    err "Could not resolve memctl scripts-path."
    err "Ensure memctl >= 0.12.3 is installed: pip install memctl[mcp]"
    exit 1
fi

MEMCTL_ARGS="--db-root $ARG_DB_ROOT"
if $ARG_DRY_RUN; then
    MEMCTL_ARGS="$MEMCTL_ARGS --dry-run"
fi

info "DB root: $ARG_DB_ROOT"
info "Installing memctl eco hooks ..."
(cd "$TARGET_DIR" && bash "$MEMCTL_SCRIPTS/install_eco.sh" $MEMCTL_ARGS)
ok "memctl eco hooks installed"

# ===========================================================================
# STEP 6: Verify + status
# ===========================================================================

step 6 "Verify installation"

PASS=0
FAIL=0

check_file() {
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

check_dir() {
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

check_file ".adservio-toolbox.toml"  "$TARGET_DIR/.adservio-toolbox.toml"
check_dir  ".claude/commands/"       "$TARGET_DIR/.claude/commands"
check_file ".claude/settings.json"   "$TARGET_DIR/.claude/settings.json"
check_dir  ".claude/hooks/"          "$TARGET_DIR/.claude/hooks"

# Status report
if ! $ARG_DRY_RUN; then
    echo ""
    info "Running toolboxctl status ..."
    (cd "$TARGET_DIR" && toolboxctl status) || true
fi

# Summary
echo ""
printf '%b\n' "${_B}=== Hook Installation Summary ===${_R}"
if $ARG_DRY_RUN; then
    info "Dry run complete. No changes were made."
else
    printf "  Target:   %s\n" "$TARGET_DIR"
    printf "  CloakMCP: %s\n" "$CLOAK_PROFILE"
    printf "  memctl:   db-root=%s\n" "$ARG_DB_ROOT"
    printf "  Checks:   ${_GREEN}%d passed${_R}" "$PASS"
    if [ "$FAIL" -gt 0 ]; then
        printf ", ${_RED}%d failed${_R}" "$FAIL"
    fi
    echo ""

    if [ "$FAIL" -gt 0 ]; then
        err "$FAIL verification check(s) failed."
        exit 1
    fi
    ok "All hooks installed successfully."
fi
