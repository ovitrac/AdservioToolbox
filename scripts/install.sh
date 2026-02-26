#!/usr/bin/env bash
# Adservio Claude Code Toolbox — Bootstrap Installer
#
# Installs the toolbox and its dependencies (memctl, CloakMCP) via pipx,
# then optionally wires Claude Code globally (hooks, permissions, CLAUDE.md).
#
# Prerequisites: bash, Python 3.10+ (system Python is fine).
# If Python is not present, install it using your distribution package manager.
#
# Usage:
#   bash install.sh                    # install everything + global wiring
#   bash install.sh --skip-global      # install tools only
#   bash install.sh --version 0.2.0    # pin to a specific version
#   bash install.sh --upgrade          # upgrade existing installations
#   bash install.sh --uninstall        # reverse everything
#
# One-liner (with checksum verification):
#   curl -fsSL https://github.com/ovitrac/AdservioToolbox/releases/download/vX.Y.Z/install.sh -o install.sh \
#     && curl -fsSL https://github.com/ovitrac/AdservioToolbox/releases/download/vX.Y.Z/SHA256SUMS -o SHA256SUMS \
#     && (shasum -a 256 -c SHA256SUMS 2>/dev/null || sha256sum -c SHA256SUMS) \
#     && bash install.sh
#
# Author: Olivier Vitrac, PhD, HDR | olivier.vitrac@adservio.fr | Adservio
# ---

set -euo pipefail

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TOOLBOX_SPEC="adservio-toolbox"
TOOLBOX_VERSION="__TOOLBOX_VERSION__"
GITHUB_REPO="ovitrac/AdservioToolbox"
MEMCTL_SPEC="memctl[mcp,docs]"
CLOAKMCP_SPEC="cloakmcp"
TOTAL_STEPS=7
MIN_PYTHON_MAJOR=3
MIN_PYTHON_MINOR=10

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

ARG_VERSION=""
ARG_SKIP_GLOBAL=false
ARG_UPGRADE=false
ARG_UNINSTALL=false
ARG_DRY_RUN=false

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Adservio Claude Code Toolbox — Bootstrap Installer.

Installs memctl, CloakMCP, and toolboxctl via pipx, then wires Claude Code
globally (CloakMCP hooks, permissions, behavioral rules).

Prerequisites:
  bash, Python 3.10+ (system Python is fine).

Options:
  --version VER    Pin all packages to version VER (e.g., 0.2.0)
  --skip-global    Install tools only, do not wire ~/.claude/
  --upgrade        Upgrade existing installations
  --uninstall      Remove global wiring and uninstall all packages
  --dry-run        Preview actions without executing
  -h, --help       Show this help

Exit codes:
  0  Success
  1  Error during installation
  2  Missing prerequisite (Python < 3.10, no pip)

Install tracks:
  Track A  Python + pip + venv available → uses pipx (recommended)
  Track B  Python + pip available (no venv) → uses pip --user (less isolation)

Examples:
  bash install.sh                        # full install + global wiring
  bash install.sh --version 0.2.0        # pinned install
  bash install.sh --skip-global          # tools only, no Claude wiring
  bash install.sh --upgrade              # upgrade all tools
  bash install.sh --uninstall            # clean removal
EOF
    exit 0
}

while [ $# -gt 0 ]; do
    case "$1" in
        --version)
            shift
            if [ $# -eq 0 ]; then
                err "--version requires a version argument (e.g., 0.2.0)"
                exit 1
            fi
            ARG_VERSION="$1"
            ;;
        --skip-global)  ARG_SKIP_GLOBAL=true ;;
        --upgrade)      ARG_UPGRADE=true ;;
        --uninstall)    ARG_UNINSTALL=true ;;
        --dry-run)      ARG_DRY_RUN=true ;;
        -h|--help)      usage ;;
        *)              err "Unknown argument: $1"; exit 1 ;;
    esac
    shift
done

# ---------------------------------------------------------------------------
# Dry-run wrapper
# ---------------------------------------------------------------------------

run() {
    if $ARG_DRY_RUN; then
        info "[dry-run] $*"
        return 0
    fi
    "$@"
}

# ---------------------------------------------------------------------------
# Distro detection (for actionable error messages)
# ---------------------------------------------------------------------------

detect_distro() {
    # Returns a distro identifier: debian, rhel, alpine, macos, unknown
    if [ -f /etc/os-release ]; then
        # shellcheck disable=SC1091
        . /etc/os-release
        case "${ID:-}" in
            ubuntu|debian|linuxmint|pop)  echo "debian" ;;
            rhel|centos|fedora|rocky|alma) echo "rhel" ;;
            alpine)                        echo "alpine" ;;
            arch|manjaro)                  echo "arch" ;;
            opensuse*|sles)               echo "suse" ;;
            *)                            echo "unknown" ;;
        esac
    elif [ "$(uname -s)" = "Darwin" ]; then
        echo "macos"
    else
        echo "unknown"
    fi
}

print_python_install_hint() {
    local distro
    distro=$(detect_distro)
    echo ""
    err "Python ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR}+ is required but not found."
    echo ""
    info "Install Python for your platform:"
    echo ""
    case "$distro" in
        debian)
            info "  sudo apt-get update && sudo apt-get install -y python3 python3-venv python3-pip"
            ;;
        rhel)
            info "  sudo dnf install -y python3 python3-pip"
            ;;
        alpine)
            info "  apk add python3 py3-pip"
            ;;
        arch)
            info "  sudo pacman -S python python-pip"
            ;;
        suse)
            info "  sudo zypper install -y python3 python3-pip python3-venv"
            ;;
        macos)
            if command -v brew >/dev/null 2>&1; then
                info "  brew install python@3.12"
            else
                info "  Install Homebrew (https://brew.sh), then: brew install python@3.12"
                info "  Or download from https://www.python.org/downloads/"
            fi
            ;;
        *)
            info "  Download from https://www.python.org/downloads/"
            ;;
    esac
    echo ""
    info "Detailed guide: https://github.com/ovitrac/AdservioToolbox/blob/main/docs/INSTALLING_PYTHON.md"
    echo ""
    info "Then re-run this script."
}

print_pip_install_hint() {
    local distro
    distro=$(detect_distro)
    echo ""
    err "Python pip module is required but not available."
    echo ""
    info "Install pip for your platform:"
    echo ""
    case "$distro" in
        debian)
            info "  sudo apt-get install -y python3-pip"
            ;;
        rhel)
            info "  sudo dnf install -y python3-pip"
            ;;
        alpine)
            info "  apk add py3-pip"
            ;;
        arch)
            info "  sudo pacman -S python-pip"
            ;;
        suse)
            info "  sudo zypper install -y python3-pip"
            ;;
        macos)
            info "  pip is included with Homebrew Python: brew install python@3.12"
            info "  Or: python3 -m ensurepip --user"
            ;;
        *)
            info "  python3 -m ensurepip --user"
            info "  Or download from https://pip.pypa.io/en/stable/installation/"
            ;;
    esac
    echo ""
    info "Then re-run this script."
}

print_venv_install_hint() {
    local distro
    distro=$(detect_distro)
    echo ""
    warn "Python venv module is not available."
    warn "pipx requires venv to create isolated environments."
    echo ""
    info "Install venv for your platform:"
    echo ""
    case "$distro" in
        debian)
            info "  sudo apt-get install -y python3-venv"
            ;;
        rhel)
            info "  (venv is included with python3 on RHEL/Fedora — no action needed)"
            ;;
        alpine)
            info "  (venv is included with python3 on Alpine — no action needed)"
            ;;
        arch)
            info "  (venv is included with python on Arch — no action needed)"
            ;;
        suse)
            info "  sudo zypper install -y python3-venv"
            ;;
        macos)
            info "  (venv is included with Homebrew Python — no action needed)"
            ;;
        *)
            info "  Check your distribution docs for python3-venv or equivalent."
            ;;
    esac
    echo ""
}

# ---------------------------------------------------------------------------
# Python detection (macOS + Linux)
# ---------------------------------------------------------------------------

find_python() {
    for candidate in python3 python; do
        if command -v "$candidate" >/dev/null 2>&1; then
            local ver
            ver=$("$candidate" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null) || continue
            local major minor
            major="${ver%%.*}"
            minor="${ver#*.}"
            if [ "$major" -ge "$MIN_PYTHON_MAJOR" ] && [ "$minor" -ge "$MIN_PYTHON_MINOR" ]; then
                PYTHON="$candidate"
                PYTHON_VER="$ver"
                return 0
            fi
        fi
    done
    return 1
}

# ---------------------------------------------------------------------------
# Capability probes (pip, venv)
# ---------------------------------------------------------------------------

HAS_PIP=false
HAS_VENV=false
IS_EXTERNALLY_MANAGED=false

probe_capabilities() {
    # Check pip module
    if "$PYTHON" -m pip --version >/dev/null 2>&1; then
        HAS_PIP=true
    fi

    # Check venv module (pipx needs this)
    if "$PYTHON" -c "import venv" >/dev/null 2>&1; then
        HAS_VENV=true
    fi

    # Detect PEP 668 externally-managed Python (Ubuntu 23.04+, Debian 12+, Fedora 38+)
    # These systems block `pip install` without --break-system-packages.
    local sysconfig_dir
    sysconfig_dir=$("$PYTHON" -c "import sysconfig; print(sysconfig.get_path('stdlib'))" 2>/dev/null) || true
    if [ -n "$sysconfig_dir" ] && [ -f "${sysconfig_dir}/EXTERNALLY-MANAGED" ]; then
        IS_EXTERNALLY_MANAGED=true
    fi
}

print_pipx_system_install_hint() {
    local distro
    distro=$(detect_distro)
    echo ""
    warn "This Python is externally managed (PEP 668)."
    warn "pip install --user is blocked by the system to protect system packages."
    echo ""
    info "Install pipx from your system package manager instead:"
    echo ""
    case "$distro" in
        debian)
            printf "  ${_B}sudo apt install -y pipx && pipx ensurepath${_R}\n"
            ;;
        rhel)
            printf "  ${_B}sudo dnf install -y pipx && pipx ensurepath${_R}\n"
            ;;
        arch)
            printf "  ${_B}sudo pacman -S python-pipx && pipx ensurepath${_R}\n"
            ;;
        suse)
            printf "  ${_B}sudo zypper install -y python3-pipx && pipx ensurepath${_R}\n"
            ;;
        macos)
            printf "  ${_B}brew install pipx && pipx ensurepath${_R}\n"
            ;;
        *)
            info "  See https://pipx.pypa.io/stable/installation/"
            ;;
    esac
    echo ""
    info "Then re-run this script. pipx will install tools in isolated"
    info "virtual environments — no conflict with system packages."
    echo ""
}

# ---------------------------------------------------------------------------
# pipx helpers
# ---------------------------------------------------------------------------

probe_pipx_health() {
    # Returns 0 if pipx is installed and functional, 1 otherwise.
    # Guards against stale shims, broken venvs, or removed Python interpreters.
    command -v pipx >/dev/null 2>&1 || return 1
    pipx --version >/dev/null 2>&1 || return 1
    return 0
}

ensure_pipx() {
    # Try to get a working pipx. Called only when PIPX_READY is false
    # and pip is available (PEP 668 not blocking).
    if probe_pipx_health; then
        ok "pipx found: $(pipx --version 2>/dev/null || echo 'available')"
        return 0
    fi

    # pipx on PATH but broken?
    if command -v pipx >/dev/null 2>&1; then
        warn "pipx found on PATH but not functional — attempting reinstall via pip"
    else
        info "pipx not found — installing via pip …"
    fi

    # PEP 668: externally-managed Python blocks pip install --user
    # (defense-in-depth — caller should have caught this already)
    if $IS_EXTERNALLY_MANAGED; then
        print_pipx_system_install_hint
        return 1
    fi

    # Try pip install --user (no sudo)
    if run "$PYTHON" -m pip install --user pipx 2>/dev/null; then
        # Ensure ~/.local/bin is on PATH
        run "$PYTHON" -m pipx ensurepath 2>/dev/null || true
        # Re-check with functional probe
        if probe_pipx_health; then
            ok "pipx installed"
            return 0
        fi
        # pipx installed but not on PATH yet — try with full path
        local pipx_path
        pipx_path="$HOME/.local/bin/pipx"
        if [ -x "$pipx_path" ] && "$pipx_path" --version >/dev/null 2>&1; then
            ok "pipx installed at $pipx_path (add ~/.local/bin to PATH)"
            # Use full path for this session
            PIPX_CMD="$pipx_path"
            return 0
        fi
    fi

    # pip install --user failed (corporate lockdown, other reasons)
    warn "Could not bootstrap pipx via pip."
    return 1
}

pipx_cmd() {
    # Use the resolved pipx command (may be full path if not on PATH)
    "${PIPX_CMD:-pipx}" "$@"
}

pipx_install() {
    local spec="$1"
    local display_name="$2"
    local extra_args=()

    if $ARG_UPGRADE; then
        # pipx upgrade if already installed, install otherwise
        if pipx_cmd list --short 2>/dev/null | grep -q "^${display_name} "; then
            info "Upgrading $display_name …"
            run pipx_cmd upgrade "$display_name"
            ok "$display_name upgraded"
            return 0
        fi
    fi

    if [ -n "$ARG_VERSION" ]; then
        spec="${spec}==${ARG_VERSION}"
    fi

    # Check if already installed
    if pipx_cmd list --short 2>/dev/null | grep -q "^${display_name} "; then
        if ! $ARG_UPGRADE; then
            ok "$display_name already installed (use --upgrade to force)"
            return 0
        fi
    fi

    info "Installing $display_name …"
    run pipx_cmd install "$spec" "${extra_args[@]+"${extra_args[@]}"}"
    ok "$display_name installed"
}

pip_fallback_install() {
    local spec="$1"
    local display_name="$2"
    local extra_args=()

    if $ARG_UPGRADE; then
        extra_args+=("--upgrade")
    fi

    if [ -n "$ARG_VERSION" ]; then
        spec="${spec}==${ARG_VERSION}"
    fi

    info "Installing $display_name via pip --user (fallback) …"
    run "$PYTHON" -m pip install --user "$spec" "${extra_args[@]+"${extra_args[@]}"}"
    ok "$display_name installed (pip --user)"
}

# ===========================================================================
# UNINSTALL PATH
# ===========================================================================

if $ARG_UNINSTALL; then
    # Need Python for pip fallback detection
    find_python || PYTHON="python3"

    step 1 "Remove global Claude Code wiring"

    if command -v toolboxctl >/dev/null 2>&1; then
        run toolboxctl install --uninstall
        ok "Global wiring removed"
    else
        warn "toolboxctl not found — skipping global wiring removal"
    fi

    step 2 "Uninstall packages"

    USE_PIPX=false
    if command -v pipx >/dev/null 2>&1; then
        USE_PIPX=true
    fi

    for pkg in adservio-toolbox cloakmcp memctl; do
        if $USE_PIPX && pipx_cmd list --short 2>/dev/null | grep -q "^${pkg} "; then
            info "Removing $pkg (pipx) …"
            run pipx_cmd uninstall "$pkg"
            ok "$pkg uninstalled"
        elif command -v "$PYTHON" >/dev/null 2>&1 && "$PYTHON" -m pip show "$pkg" >/dev/null 2>&1; then
            info "Removing $pkg (pip) …"
            run "$PYTHON" -m pip uninstall -y "$pkg"
            ok "$pkg uninstalled"
        else
            info "$pkg not installed — skipping"
        fi
    done

    echo ""
    ok "Uninstall complete."
    exit 0
fi

# ===========================================================================
# INSTALL PATH
# ===========================================================================

echo ""
printf '%b\n' "${_B}Adservio Claude Code Toolbox — Installer${_R}"
echo ""
info "Prerequisites: bash, Python ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR}+"
echo ""

# ===========================================================================
# STEP 1: Check Python + capabilities
# ===========================================================================

step 1 "Check Python ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR}+ and package tools"

# --- 1a: Find Python ---
if ! find_python; then
    print_python_install_hint
    exit 2
fi
ok "Python $PYTHON_VER ($PYTHON)"

# --- 1b: Check pipx health first (pipx-first policy) ---
# If pipx is already present and functional, pip is not needed at all.
# Modern distros (Ubuntu 24.04+, Debian 12+, Fedora 38+) often ship pipx
# from the system package manager without shipping pip.
PIPX_READY=false
if probe_pipx_health; then
    PIPX_READY=true
    ok "pipx functional ($(pipx --version 2>/dev/null))"
fi

# --- 1c: Probe pip/venv/PEP668 only if pipx is not ready ---
if ! $PIPX_READY; then
    probe_capabilities

    if $HAS_PIP; then
        ok "pip available (for pipx bootstrap)"
    fi
    if $HAS_VENV; then
        ok "venv available"
    else
        warn "venv not available — pipx bootstrap may need it"
    fi

    # No pipx AND no pip → only path is OS package manager
    if ! $HAS_PIP; then
        echo ""
        err "Neither pipx nor pip is available."
        err "pipx is required to install tools in isolated environments."
        print_pipx_system_install_hint
        exit 2
    fi

    # pip available but PEP 668 blocks pip install --user → can't bootstrap pipx
    if $IS_EXTERNALLY_MANAGED; then
        echo ""
        err "pip is available but this Python is externally managed (PEP 668)."
        err "Cannot bootstrap pipx via pip — the system blocks pip install --user."
        print_pipx_system_install_hint
        exit 2
    fi
fi

# ===========================================================================
# STEP 2: Select install track
# ===========================================================================

step 2 "Select install track"

USE_PIPX=false
PIPX_CMD=""
INSTALL_TRACK=""

if $PIPX_READY; then
    # pipx already verified in Step 1 — use it directly (no pip needed)
    USE_PIPX=true
    INSTALL_TRACK="A"
    ok "Track A: pipx (pre-installed, isolated environments)"
elif ensure_pipx; then
    # Bootstrapped pipx via pip
    USE_PIPX=true
    INSTALL_TRACK="A"
    ok "Track A: pipx (bootstrapped via pip)"
else
    # pipx bootstrap failed — fall back to pip --user
    INSTALL_TRACK="B"
fi

if [ "$INSTALL_TRACK" = "B" ]; then
    ok "Track B: pip --user"
    warn "Less isolation than pipx. Consider installing pipx from your package manager."
    warn "Binaries go to ~/.local/bin — ensure it is on your PATH."
fi

# ===========================================================================
# STEP 3: Install memctl
# ===========================================================================

step 3 "Install memctl"

if $USE_PIPX; then
    pipx_install "$MEMCTL_SPEC" "memctl"
else
    pip_fallback_install "$MEMCTL_SPEC" "memctl"
fi

# Verify
if command -v memctl >/dev/null 2>&1; then
    ok "memctl on PATH: $(command -v memctl)"
elif [ -x "$HOME/.local/bin/memctl" ]; then
    warn "memctl installed at ~/.local/bin/memctl but not on PATH"
else
    warn "memctl installed but not on PATH — check ~/.local/bin"
fi

# ===========================================================================
# STEP 4: Install CloakMCP
# ===========================================================================

step 4 "Install CloakMCP"

if $USE_PIPX; then
    pipx_install "$CLOAKMCP_SPEC" "cloakmcp"
else
    pip_fallback_install "$CLOAKMCP_SPEC" "cloakmcp"
fi

# Verify
if command -v cloak >/dev/null 2>&1; then
    ok "cloak on PATH: $(command -v cloak)"
elif [ -x "$HOME/.local/bin/cloak" ]; then
    warn "cloak installed at ~/.local/bin/cloak but not on PATH"
else
    warn "cloak installed but not on PATH — check ~/.local/bin"
fi

# ===========================================================================
# STEP 5: Install adservio-toolbox (from GitHub release, not PyPI)
# ===========================================================================

step 5 "Install adservio-toolbox"

# Determine version and source for the toolbox
_tb_version="${ARG_VERSION:-$TOOLBOX_VERSION}"
_tb_tarball="adservio-toolbox-${_tb_version}.tar.gz"
_tb_url="https://github.com/${GITHUB_REPO}/releases/download/v${_tb_version}/${_tb_tarball}"

# Resolution order: local file > download from release
if [ -f "$_tb_tarball" ]; then
    _tb_source="./$_tb_tarball"
    info "Using local tarball: $_tb_tarball"
elif [ -f "$(dirname "$0")/../release/$_tb_tarball" ]; then
    _tb_source="$(dirname "$0")/../release/$_tb_tarball"
    info "Using release/ tarball: $_tb_source"
else
    _tb_source="$_tb_url"
    info "Installing from GitHub release: $_tb_url"
fi

if $USE_PIPX; then
    if $ARG_UPGRADE; then
        if pipx_cmd list --short 2>/dev/null | grep -q "^adservio-toolbox "; then
            info "Upgrading adservio-toolbox …"
            run pipx_cmd install --force "$_tb_source"
            ok "adservio-toolbox upgraded"
        else
            run pipx_cmd install "$_tb_source"
            ok "adservio-toolbox installed"
        fi
    else
        if pipx_cmd list --short 2>/dev/null | grep -q "^adservio-toolbox "; then
            ok "adservio-toolbox already installed (use --upgrade to force)"
        else
            run pipx_cmd install "$_tb_source"
            ok "adservio-toolbox installed"
        fi
    fi
else
    info "Installing adservio-toolbox via pip --user (fallback) …"
    run "$PYTHON" -m pip install --user "$_tb_source"
    ok "adservio-toolbox installed (pip --user)"
fi

# Verify
if command -v toolboxctl >/dev/null 2>&1; then
    ok "toolboxctl on PATH: $(command -v toolboxctl)"
elif [ -x "$HOME/.local/bin/toolboxctl" ]; then
    warn "toolboxctl installed at ~/.local/bin/toolboxctl but not on PATH"
else
    warn "toolboxctl installed but not on PATH — check ~/.local/bin"
fi

# ===========================================================================
# STEP 6: Wire Claude Code globally
# ===========================================================================

step 6 "Wire Claude Code globally"

if $ARG_SKIP_GLOBAL; then
    info "Skipped (--skip-global). Run 'toolboxctl install --global' later."
else
    if command -v toolboxctl >/dev/null 2>&1; then
        run toolboxctl install --global
        ok "Global wiring complete"
    else
        warn "toolboxctl not on PATH — cannot wire Claude Code."
        warn "Run: toolboxctl install --global (after fixing PATH)"
    fi
fi

# ===========================================================================
# STEP 7: Doctor
# ===========================================================================

step 7 "Verify installation"

if command -v toolboxctl >/dev/null 2>&1; then
    run toolboxctl doctor
else
    warn "toolboxctl not on PATH — skipping doctor."
    warn "Verify manually after adding ~/.local/bin to PATH and restarting your shell."
fi

# ===========================================================================
# Summary
# ===========================================================================

echo ""
printf '%b\n' "${_B}=== Installation complete ===${_R}"
echo ""

info "Install track: $INSTALL_TRACK ($( $USE_PIPX && echo "pipx" || echo "pip --user" ))"

if $ARG_SKIP_GLOBAL; then
    info "Tools installed. Global Claude Code wiring was skipped."
    info "To wire later: toolboxctl install --global"
else
    info "Tools installed and Claude Code wired globally."
fi

echo ""
info "Next steps:"
info "  1. Open a terminal (or restart your shell for PATH changes)"
info "  2. Navigate to a project: cd /path/to/your-project"
info "  3. Initialize: toolboxctl init"
info "  4. Check health: toolboxctl doctor"
echo ""

if $USE_PIPX; then
    info "Upgrade later: bash install.sh --upgrade"
    info "Uninstall:     bash install.sh --uninstall"
else
    info "Upgrade: pip install --user --upgrade memctl[mcp,docs] cloakmcp adservio-toolbox"
fi
echo ""
