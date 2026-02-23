# Adservio Claude Code Toolbox — Bootstrap Installer (Windows)
#
# SKELETON — Not fully supported in v0.2.0.
# Provides manual instructions for Windows users.
# Full support planned for v0.3.0.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File install.ps1
#   iwr -useb https://github.com/Adservio-Dev/AdservioToolbox/releases/download/vX.Y.Z/install.ps1 | iex
#
# Author: Olivier Vitrac, PhD, HDR | olivier.vitrac@adservio.fr | Adservio
# ---

param(
    [string]$Version = "",
    [switch]$SkipGlobal,
    [switch]$Upgrade,
    [switch]$Uninstall,
    [switch]$DryRun,
    [switch]$Help
)

$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

function Write-Step($num, $total, $msg) {
    Write-Host "[STEP $num/$total] $msg" -ForegroundColor Cyan
}

function Write-Ok($msg) {
    Write-Host "[OK]    $msg" -ForegroundColor Green
}

function Write-Info($msg) {
    Write-Host "[INFO]  $msg" -ForegroundColor Cyan
}

function Write-Warn($msg) {
    Write-Host "[WARN]  $msg" -ForegroundColor Yellow
}

function Write-Err($msg) {
    Write-Host "[ERROR] $msg" -ForegroundColor Red
}

# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------

if ($Help) {
    Write-Host @"
Adservio Claude Code Toolbox — Bootstrap Installer (Windows)

STATUS: Skeleton — not fully supported in v0.2.0.
        Full support planned for v0.3.0.

Usage:
  powershell -ExecutionPolicy Bypass -File install.ps1 [OPTIONS]

Options:
  -Version VER     Pin all packages to version VER (e.g., 0.2.0)
  -SkipGlobal      Install tools only, do not wire ~/.claude/
  -Upgrade         Upgrade existing installations
  -Uninstall       Remove global wiring and uninstall all packages
  -DryRun          Preview actions without executing
  -Help            Show this help

Manual installation (recommended for now):
  1. Install Python 3.10+ from https://www.python.org/downloads/
  2. pip install --user pipx
  3. pipx ensurepath
  4. Restart your terminal
  5. pipx install memctl[mcp]
  6. pipx install cloakmcp
  7. pipx install adservio-toolbox
  8. toolboxctl install --global
  9. toolboxctl doctor
"@
    exit 0
}

# ---------------------------------------------------------------------------
# Pre-flight
# ---------------------------------------------------------------------------

$TotalSteps = 7

Write-Host ""
Write-Host "Adservio Claude Code Toolbox — Installer (Windows)" -ForegroundColor White -BackgroundColor DarkBlue
Write-Host ""
Write-Warn "Windows support is in preview (v0.2.0). Some features may require manual steps."
Write-Host ""

# ---------------------------------------------------------------------------
# STEP 1: Check Python
# ---------------------------------------------------------------------------

Write-Step 1 $TotalSteps "Check Python 3.10+"

$python = $null
foreach ($cmd in @("python3", "python", "py")) {
    try {
        $ver = & $cmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
        if ($ver) {
            $parts = $ver.Split(".")
            if ([int]$parts[0] -ge 3 -and [int]$parts[1] -ge 10) {
                $python = $cmd
                Write-Ok "Python $ver ($cmd)"
                break
            }
        }
    } catch {
        continue
    }
}

if (-not $python) {
    Write-Err "Python 3.10+ is required. Download from https://www.python.org/downloads/"
    exit 2
}

# ---------------------------------------------------------------------------
# STEP 2: Check pipx
# ---------------------------------------------------------------------------

Write-Step 2 $TotalSteps "Check / install pipx"

$hasPipx = $false
try {
    $pipxVer = & pipx --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Ok "pipx $pipxVer"
        $hasPipx = $true
    }
} catch {}

if (-not $hasPipx) {
    Write-Info "pipx not found — installing …"
    if (-not $DryRun) {
        & $python -m pip install --user pipx 2>$null
        & $python -m pipx ensurepath 2>$null
    } else {
        Write-Info "[dry-run] $python -m pip install --user pipx"
    }
    Write-Warn "Restart your terminal after pipx installation for PATH changes."
    Write-Warn "Then re-run this script."

    if (-not $DryRun) {
        Write-Host ""
        Write-Info "Or install manually:"
        Write-Info "  pipx install memctl[mcp]"
        Write-Info "  pipx install cloakmcp"
        Write-Info "  pipx install adservio-toolbox"
        Write-Info "  toolboxctl install --global"
        Write-Info "  toolboxctl doctor"
        exit 1
    }
}

# ---------------------------------------------------------------------------
# STEPS 3-5: Install packages
# ---------------------------------------------------------------------------

$packages = @(
    @{ Spec = "memctl[mcp]";       Name = "memctl";            Step = 3 },
    @{ Spec = "cloakmcp";          Name = "cloakmcp";          Step = 4 },
    @{ Spec = "adservio-toolbox";  Name = "adservio-toolbox";  Step = 5 }
)

foreach ($pkg in $packages) {
    Write-Step $pkg.Step $TotalSteps "Install $($pkg.Name)"

    $spec = $pkg.Spec
    if ($Version) { $spec = "$spec==$Version" }

    if ($Uninstall) {
        Write-Info "Removing $($pkg.Name) …"
        if (-not $DryRun) {
            & pipx uninstall $pkg.Name 2>$null
        } else {
            Write-Info "[dry-run] pipx uninstall $($pkg.Name)"
        }
        continue
    }

    if ($Upgrade) {
        Write-Info "Upgrading $($pkg.Name) …"
        if (-not $DryRun) {
            & pipx upgrade $pkg.Name 2>$null
        } else {
            Write-Info "[dry-run] pipx upgrade $($pkg.Name)"
        }
    } else {
        Write-Info "Installing $($pkg.Name) …"
        if (-not $DryRun) {
            & pipx install $spec 2>$null
        } else {
            Write-Info "[dry-run] pipx install $spec"
        }
    }
    Write-Ok "$($pkg.Name) done"
}

# ---------------------------------------------------------------------------
# STEP 6: Global wiring
# ---------------------------------------------------------------------------

Write-Step 6 $TotalSteps "Wire Claude Code globally"

if ($Uninstall) {
    Write-Info "Removing global wiring …"
    if (-not $DryRun) {
        & toolboxctl install --uninstall 2>$null
    } else {
        Write-Info "[dry-run] toolboxctl install --uninstall"
    }
} elseif ($SkipGlobal) {
    Write-Info "Skipped (--SkipGlobal). Run 'toolboxctl install --global' later."
} else {
    if (-not $DryRun) {
        & toolboxctl install --global 2>$null
    } else {
        Write-Info "[dry-run] toolboxctl install --global"
    }
}

# ---------------------------------------------------------------------------
# STEP 7: Doctor
# ---------------------------------------------------------------------------

Write-Step 7 $TotalSteps "Verify installation"

if (-not $Uninstall) {
    if (-not $DryRun) {
        & toolboxctl doctor 2>$null
    } else {
        Write-Info "[dry-run] toolboxctl doctor"
    }
}

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

Write-Host ""
if ($Uninstall) {
    Write-Ok "Uninstall complete."
} else {
    Write-Ok "Installation complete."
    Write-Host ""
    Write-Info "Next steps:"
    Write-Info "  1. Restart your terminal (for PATH changes)"
    Write-Info "  2. cd to a project directory"
    Write-Info "  3. toolboxctl init"
    Write-Info "  4. toolboxctl doctor"
}
Write-Host ""
