#!/usr/bin/env bash
# Adservio Claude Code Toolbox — Release Builder
#
# Builds release assets for GitHub Releases:
#   - install.sh (bootstrap script)
#   - install.ps1 (Windows skeleton)
#   - adservio-toolbox-VERSION.tar.gz (sdist)
#   - adservio-toolbox-VERSION.zip (convenience archive)
#   - SHA256SUMS (checksums for all assets)
#   - SHA256SUMS.sig (optional GPG signature)
#
# Usage:
#   bash scripts/build-release.sh                  # build from pyproject.toml version
#   bash scripts/build-release.sh --version 0.2.0  # override version
#   bash scripts/build-release.sh --sign            # also GPG-sign SHA256SUMS
#   bash scripts/build-release.sh --dry-run         # preview actions
#   bash scripts/build-release.sh --clean           # remove release/ directory
#
# Output: release/ directory with all assets ready for upload.
#
# Author: Olivier Vitrac, PhD, HDR | olivier.vitrac@adservio.fr | Adservio
# ---

set -euo pipefail

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
RELEASE_DIR="$REPO_ROOT/release"
PYPROJECT="$REPO_ROOT/pyproject.toml"
PKG_NAME="adservio-toolbox"

# ---------------------------------------------------------------------------
# ANSI helpers (TTY-aware)
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
ARG_SIGN=false
ARG_DRY_RUN=false
ARG_CLEAN=false
TOTAL_STEPS=6

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Adservio Claude Code Toolbox — Release Builder.

Builds release assets (sdist, scripts, checksums) for GitHub Releases.

Options:
  --version VER    Override version (default: read from pyproject.toml)
  --sign           GPG-sign SHA256SUMS (requires gpg)
  --dry-run        Preview actions without building
  --clean          Remove release/ directory and exit
  -h, --help       Show this help

Output:
  release/
    install.sh
    install.ps1
    ${PKG_NAME}-VERSION.tar.gz
    ${PKG_NAME}-VERSION.zip
    SHA256SUMS
    SHA256SUMS.sig  (if --sign)

Examples:
  bash scripts/build-release.sh                   # build from pyproject.toml
  bash scripts/build-release.sh --version 0.2.0   # override version
  bash scripts/build-release.sh --sign             # with GPG signature
  bash scripts/build-release.sh --clean            # remove release/
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
        --sign)     ARG_SIGN=true ;;
        --dry-run)  ARG_DRY_RUN=true ;;
        --clean)    ARG_CLEAN=true ;;
        -h|--help)  usage ;;
        *)          err "Unknown argument: $1"; exit 1 ;;
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
# Clean
# ---------------------------------------------------------------------------

if $ARG_CLEAN; then
    if [ -d "$RELEASE_DIR" ]; then
        rm -rf "$RELEASE_DIR"
        ok "Removed $RELEASE_DIR"
    else
        info "Nothing to clean (release/ does not exist)"
    fi
    exit 0
fi

# ===========================================================================
# BUILD
# ===========================================================================

echo ""
printf '%b\n' "${_B}Adservio Claude Code Toolbox — Release Builder${_R}"
echo ""

# ===========================================================================
# STEP 1: Determine version
# ===========================================================================

step 1 "Determine version"

if [ -n "$ARG_VERSION" ]; then
    VERSION="$ARG_VERSION"
    info "Version override: $VERSION"
else
    if [ ! -f "$PYPROJECT" ]; then
        err "pyproject.toml not found at $PYPROJECT"
        exit 1
    fi
    # Extract version from pyproject.toml (no toml parser needed — simple grep)
    VERSION=$(grep -E '^version\s*=' "$PYPROJECT" | head -1 | sed 's/.*=\s*"\(.*\)"/\1/')
    if [ -z "$VERSION" ]; then
        err "Could not extract version from pyproject.toml"
        exit 1
    fi
fi

ok "Version: $VERSION"

TAG="v${VERSION}"
SDIST_NAME="${PKG_NAME}-${VERSION}"

# ===========================================================================
# STEP 2: Pre-flight checks
# ===========================================================================

step 2 "Pre-flight checks"

# Check required files exist
for f in scripts/install.sh scripts/install.ps1; do
    if [ ! -f "$REPO_ROOT/$f" ]; then
        err "Required file missing: $f"
        exit 1
    fi
done
ok "install.sh and install.ps1 present"

# Check Python build tools
PYTHON=""
for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
        PYTHON="$candidate"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    err "Python not found — required for building sdist"
    exit 2
fi
ok "Python: $($PYTHON --version 2>&1)"

# Check build module
if ! "$PYTHON" -m build --version >/dev/null 2>&1; then
    warn "python build module not found — attempting to install"
    if ! $ARG_DRY_RUN; then
        "$PYTHON" -m pip install --user build >/dev/null 2>&1 || true
        if ! "$PYTHON" -m build --version >/dev/null 2>&1; then
            err "Could not install 'build' module. Run: pip install build"
            exit 1
        fi
    fi
fi
ok "build module available"

# Check zip
if ! command -v zip >/dev/null 2>&1; then
    warn "zip not found — .zip archive will be skipped"
    HAS_ZIP=false
else
    HAS_ZIP=true
    ok "zip available"
fi

# Check GPG (if signing)
if $ARG_SIGN; then
    if ! command -v gpg >/dev/null 2>&1; then
        err "--sign requires gpg but it is not installed"
        exit 1
    fi
    ok "gpg available"
fi

# ===========================================================================
# STEP 3: Prepare release directory
# ===========================================================================

step 3 "Prepare release directory"

if [ -d "$RELEASE_DIR" ]; then
    warn "release/ already exists — removing"
    run rm -rf "$RELEASE_DIR"
fi
run mkdir -p "$RELEASE_DIR"
ok "Created $RELEASE_DIR"

# ===========================================================================
# STEP 4: Build sdist
# ===========================================================================

step 4 "Build sdist"

if ! $ARG_DRY_RUN; then
    # Build sdist into dist/
    (cd "$REPO_ROOT" && "$PYTHON" -m build --sdist --outdir "$RELEASE_DIR" 2>&1) | while IFS= read -r line; do
        info "$line"
    done

    # Verify the tarball exists
    TARBALL="$RELEASE_DIR/${SDIST_NAME}.tar.gz"
    if [ ! -f "$TARBALL" ]; then
        # setuptools may use underscores in the filename
        SDIST_NAME_US="${PKG_NAME//-/_}-${VERSION}"
        TARBALL="$RELEASE_DIR/${SDIST_NAME_US}.tar.gz"
        if [ ! -f "$TARBALL" ]; then
            err "Expected sdist not found in $RELEASE_DIR"
            ls -la "$RELEASE_DIR" >&2
            exit 1
        fi
        # Rename to use hyphens (consistent with package name)
        mv "$TARBALL" "$RELEASE_DIR/${SDIST_NAME}.tar.gz"
        TARBALL="$RELEASE_DIR/${SDIST_NAME}.tar.gz"
    fi
    ok "sdist: $(basename "$TARBALL") ($(du -h "$TARBALL" | cut -f1))"
else
    info "[dry-run] python -m build --sdist --outdir $RELEASE_DIR"
    ok "sdist: ${SDIST_NAME}.tar.gz (dry-run)"
fi

# ===========================================================================
# STEP 5: Collect release assets
# ===========================================================================

step 5 "Collect release assets"

# Copy install scripts
run cp "$REPO_ROOT/scripts/install.sh" "$RELEASE_DIR/install.sh"
ok "Copied install.sh"

run cp "$REPO_ROOT/scripts/install.ps1" "$RELEASE_DIR/install.ps1"
ok "Copied install.ps1"

# Create zip archive (convenience for Windows users)
if $HAS_ZIP && ! $ARG_DRY_RUN; then
    (cd "$REPO_ROOT" && zip -r "$RELEASE_DIR/${SDIST_NAME}.zip" \
        toolbox/ \
        scripts/install.sh \
        scripts/install.ps1 \
        pyproject.toml \
        README.md \
        CHANGELOG.md \
        LICENSE \
        docs/ \
        -x "*.pyc" "*/__pycache__/*" "*.egg-info/*" 2>/dev/null) || true
    if [ -f "$RELEASE_DIR/${SDIST_NAME}.zip" ]; then
        ok "zip: ${SDIST_NAME}.zip ($(du -h "$RELEASE_DIR/${SDIST_NAME}.zip" | cut -f1))"
    else
        warn "zip creation failed — skipping"
    fi
elif $HAS_ZIP; then
    info "[dry-run] zip -r $RELEASE_DIR/${SDIST_NAME}.zip ..."
    ok "zip: ${SDIST_NAME}.zip (dry-run)"
else
    info "Skipping zip (zip command not available)"
fi

# ===========================================================================
# STEP 6: Generate checksums
# ===========================================================================

step 6 "Generate checksums"

if ! $ARG_DRY_RUN; then
    (cd "$RELEASE_DIR" && {
        # Generate SHA256 checksums for all release files
        # Use shasum (macOS) or sha256sum (Linux)
        if command -v sha256sum >/dev/null 2>&1; then
            sha256sum -- *.tar.gz *.zip *.sh *.ps1 2>/dev/null > SHA256SUMS
        elif command -v shasum >/dev/null 2>&1; then
            shasum -a 256 -- *.tar.gz *.zip *.sh *.ps1 2>/dev/null > SHA256SUMS
        else
            err "Neither sha256sum nor shasum found"
            exit 1
        fi
    })
    ok "SHA256SUMS generated"

    # Display checksums
    echo ""
    info "Checksums:"
    while IFS= read -r line; do
        info "  $line"
    done < "$RELEASE_DIR/SHA256SUMS"

    # GPG sign if requested
    if $ARG_SIGN; then
        echo ""
        info "Signing SHA256SUMS with GPG …"
        gpg --detach-sign --armor "$RELEASE_DIR/SHA256SUMS"
        mv "$RELEASE_DIR/SHA256SUMS.asc" "$RELEASE_DIR/SHA256SUMS.sig"
        ok "SHA256SUMS.sig created"
    fi
else
    info "[dry-run] sha256sum *.tar.gz *.zip *.sh *.ps1 > SHA256SUMS"
    if $ARG_SIGN; then
        info "[dry-run] gpg --detach-sign --armor SHA256SUMS"
    fi
fi

# ===========================================================================
# Summary
# ===========================================================================

echo ""
printf '%b\n' "${_B}=== Release build complete ===${_R}"
echo ""

info "Version: $VERSION"
info "Tag:     $TAG"
info "Output:  $RELEASE_DIR/"
echo ""

if ! $ARG_DRY_RUN; then
    info "Release assets:"
    (cd "$RELEASE_DIR" && ls -lh) | while IFS= read -r line; do
        info "  $line"
    done
else
    info "Release assets (dry-run):"
    info "  install.sh"
    info "  install.ps1"
    info "  ${SDIST_NAME}.tar.gz"
    info "  ${SDIST_NAME}.zip"
    info "  SHA256SUMS"
    if $ARG_SIGN; then
        info "  SHA256SUMS.sig"
    fi
fi

echo ""
info "Next steps:"
info "  1. Review assets in release/"
info "  2. Tag the release:  git tag -a $TAG -m 'Release $VERSION'"
info "  3. Push the tag:     git push origin $TAG"
info "  4. Upload to GitHub: gh release create $TAG release/* --title '$TAG' --notes-file CHANGELOG.md"
echo ""
info "Or use the GitHub Actions workflow to automate steps 3-4."
echo ""
