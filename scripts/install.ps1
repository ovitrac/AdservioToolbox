# Adservio Claude Code Toolbox — Bootstrap Installer (Windows)
#
# Installs the toolbox and its dependencies (memctl, CloakMCP) via pipx,
# then optionally wires Claude Code globally (hooks, permissions, CLAUDE.md).
#
# Prerequisites: PowerShell 5.1+, Python 3.10+ (python.org or winget).
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File install.ps1
#   powershell -ExecutionPolicy Bypass -File install.ps1 -Version 0.4.1
#   powershell -ExecutionPolicy Bypass -File install.ps1 -Upgrade
#   powershell -ExecutionPolicy Bypass -File install.ps1 -Uninstall
#
# One-liner (download + run):
#   iwr -useb https://github.com/ovitrac/AdservioToolbox/releases/latest/download/install.ps1 -OutFile install.ps1; .\install.ps1
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
# Constants
# ---------------------------------------------------------------------------

$TOOLBOX_VERSION  = "__TOOLBOX_VERSION__"
$GITHUB_REPO      = "ovitrac/AdservioToolbox"
$MEMCTL_SPEC      = "memctl[mcp,docs]"
$CLOAKMCP_SPEC    = "cloakmcp"
$MIN_PYTHON_MAJOR = 3
$MIN_PYTHON_MINOR = 10
$TotalSteps       = 7

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

function Write-Step($num, $total, $msg) {
    Write-Host "[STEP $num/$total] " -ForegroundColor Cyan -NoNewline
    Write-Host $msg
}

function Write-Ok($msg) {
    Write-Host "[OK]    " -ForegroundColor Green -NoNewline
    Write-Host $msg
}

function Write-Info($msg) {
    Write-Host "[INFO]  " -ForegroundColor Cyan -NoNewline
    Write-Host $msg
}

function Write-Warn($msg) {
    Write-Host "[WARN]  " -ForegroundColor Yellow -NoNewline
    Write-Host $msg
}

function Write-Err($msg) {
    Write-Host "[ERROR] " -ForegroundColor Red -NoNewline
    Write-Host $msg
}

function Invoke-Run {
    param([scriptblock]$Cmd)
    if ($DryRun) {
        Write-Info "[dry-run] $Cmd"
        return $true
    }
    try {
        & $Cmd
        return ($LASTEXITCODE -eq 0 -or $null -eq $LASTEXITCODE)
    } catch {
        return $false
    }
}

function Test-Command($name) {
    $null -ne (Get-Command $name -ErrorAction SilentlyContinue)
}

# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------

if ($Help) {
    @"
Adservio Claude Code Toolbox — Bootstrap Installer (Windows)

Usage:
  powershell -ExecutionPolicy Bypass -File install.ps1 [OPTIONS]

Options:
  -Version VER     Pin all packages to version VER (e.g., 0.4.1)
  -SkipGlobal      Install tools only, do not wire ~/.claude/
  -Upgrade         Upgrade existing installations
  -Uninstall       Remove global wiring and uninstall all packages
  -DryRun          Preview actions without executing
  -Help            Show this help

Install tracks:
  Track A  Python + pip + venv available -> uses pipx (recommended)
  Track B  Python + pip available (no venv) -> uses pip --user (less isolation)

Exit codes:
  0  Success
  1  Error during installation
  2  Missing prerequisite (Python < 3.10, no pip)

Examples:
  .\install.ps1                        # full install + global wiring
  .\install.ps1 -Version 0.4.1        # pinned install
  .\install.ps1 -SkipGlobal           # tools only, no Claude wiring
  .\install.ps1 -Upgrade              # upgrade all tools
  .\install.ps1 -Uninstall            # clean removal
"@ | Write-Host
    exit 0
}

# ---------------------------------------------------------------------------
# Python detection (py launcher, python3, python)
# ---------------------------------------------------------------------------

function Find-Python {
    # Windows Python launcher (py -3) is the most reliable on Windows
    foreach ($cmd in @("py", "python3", "python")) {
        try {
            $args_ = if ($cmd -eq "py") { @("-3", "-c") } else { @("-c") }
            $ver = & $cmd @args_ "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
            if ($LASTEXITCODE -eq 0 -and $ver) {
                $parts = $ver.Split(".")
                $major = [int]$parts[0]
                $minor = [int]$parts[1]
                if ($major -ge $MIN_PYTHON_MAJOR -and $minor -ge $MIN_PYTHON_MINOR) {
                    return @{
                        Cmd     = $cmd
                        Args    = if ($cmd -eq "py") { @("-3") } else { @() }
                        Version = $ver
                    }
                }
            }
        } catch {
            continue
        }
    }
    return $null
}

function Invoke-Python {
    param([string[]]$Arguments)
    $allArgs = $script:Python.Args + $Arguments
    & $script:Python.Cmd @allArgs
}

# ---------------------------------------------------------------------------
# Capability probes
# ---------------------------------------------------------------------------

function Test-Pip {
    try {
        Invoke-Python @("-m", "pip", "--version") 2>$null | Out-Null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

function Test-Venv {
    try {
        Invoke-Python @("-c", "import venv") 2>$null | Out-Null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

function Test-ExternallyManaged {
    # PEP 668: check for EXTERNALLY-MANAGED marker
    try {
        $stdlib = Invoke-Python @("-c", "import sysconfig; print(sysconfig.get_path('stdlib'))") 2>$null
        if ($stdlib -and (Test-Path (Join-Path $stdlib "EXTERNALLY-MANAGED"))) {
            return $true
        }
    } catch {}
    return $false
}

# ---------------------------------------------------------------------------
# pipx helpers
# ---------------------------------------------------------------------------

function Ensure-Pipx {
    if (Test-Command "pipx") {
        $ver = & pipx --version 2>$null
        Write-Ok "pipx found: $ver"
        return $true
    }

    # PEP 668: skip pip install, suggest system package manager
    if ($script:IsExternallyManaged) {
        Write-Warn "This Python is externally managed (PEP 668)."
        Write-Warn "pip install --user is blocked by the system."
        Write-Host ""
        Write-Info "Install pipx using one of these methods:"
        Write-Host ""
        Write-Host "  winget install pipx                     " -ForegroundColor White -NoNewline
        Write-Host "# Windows Package Manager"
        Write-Host "  scoop install pipx                      " -ForegroundColor White -NoNewline
        Write-Host "# Scoop"
        Write-Host "  choco install pipx                      " -ForegroundColor White -NoNewline
        Write-Host "# Chocolatey"
        Write-Host ""
        Write-Info "Then: pipx ensurepath"
        Write-Info "Then re-run this script."
        Write-Host ""
        return $false
    }

    Write-Info "pipx not found - installing via pip ..."

    if (-not $DryRun) {
        try {
            Invoke-Python @("-m", "pip", "install", "--user", "pipx") 2>$null | Out-Null
            Invoke-Python @("-m", "pipx", "ensurepath") 2>$null | Out-Null
        } catch {}

        # Check if pipx is now available
        if (Test-Command "pipx") {
            Write-Ok "pipx installed"
            return $true
        }

        # Try common install locations
        $pipxPaths = @(
            "$env:APPDATA\Python\Scripts\pipx.exe",
            "$env:LOCALAPPDATA\Programs\Python\Scripts\pipx.exe",
            "$HOME\.local\bin\pipx.exe"
        )
        foreach ($p in $pipxPaths) {
            if (Test-Path $p) {
                Write-Ok "pipx installed at $p"
                Write-Warn "Restart your terminal for PATH changes, then re-run."
                return $false
            }
        }
    } else {
        Write-Info "[dry-run] pip install --user pipx"
        return $true
    }

    # pip install failed
    Write-Warn "Could not install pipx via pip."
    Write-Host ""
    Write-Info "Install pipx manually using one of these methods:"
    Write-Host ""
    Write-Host "  winget install pipx                     " -ForegroundColor White -NoNewline
    Write-Host "# Windows Package Manager (recommended)"
    Write-Host "  scoop install pipx                      " -ForegroundColor White -NoNewline
    Write-Host "# Scoop"
    Write-Host "  choco install pipx                      " -ForegroundColor White -NoNewline
    Write-Host "# Chocolatey"
    Write-Host ""
    Write-Info "Then: pipx ensurepath"
    Write-Info "Then re-run this script."
    Write-Host ""
    return $false
}

function Invoke-PipxInstall {
    param([string]$Spec, [string]$DisplayName)

    if ($Upgrade) {
        $listed = & pipx list --short 2>$null
        if ($listed -match "^$DisplayName ") {
            Write-Info "Upgrading $DisplayName ..."
            Invoke-Run { & pipx upgrade $DisplayName }
            Write-Ok "$DisplayName upgraded"
            return
        }
    }

    $installSpec = $Spec
    if ($Version) { $installSpec = "${Spec}==${Version}" }

    # Already installed?
    $listed = & pipx list --short 2>$null
    if ($listed -match "^$DisplayName ") {
        if (-not $Upgrade) {
            Write-Ok "$DisplayName already installed (use -Upgrade to force)"
            return
        }
    }

    Write-Info "Installing $DisplayName ..."
    Invoke-Run { & pipx install $installSpec }
    Write-Ok "$DisplayName installed"
}

function Invoke-PipFallbackInstall {
    param([string]$Spec, [string]$DisplayName)

    $installSpec = $Spec
    if ($Version) { $installSpec = "${Spec}==${Version}" }

    $args_ = @("-m", "pip", "install", "--user", $installSpec)
    if ($Upgrade) { $args_ += "--upgrade" }

    Write-Info "Installing $DisplayName via pip --user (fallback) ..."
    Invoke-Run { Invoke-Python $args_ }
    Write-Ok "$DisplayName installed (pip --user)"
}

# ===========================================================================
# UNINSTALL PATH
# ===========================================================================

if ($Uninstall) {
    Write-Host ""
    Write-Host "Adservio Claude Code Toolbox - Uninstaller" -ForegroundColor White
    Write-Host ""

    Write-Step 1 2 "Remove global Claude Code wiring"
    if (Test-Command "toolboxctl") {
        Invoke-Run { & toolboxctl install --uninstall }
        Write-Ok "Global wiring removed"
    } else {
        Write-Warn "toolboxctl not found - skipping global wiring removal"
    }

    Write-Step 2 2 "Uninstall packages"
    $usePipx = Test-Command "pipx"
    foreach ($pkg in @("adservio-toolbox", "cloakmcp", "memctl")) {
        if ($usePipx) {
            $listed = & pipx list --short 2>$null
            if ($listed -match "^$pkg ") {
                Write-Info "Removing $pkg (pipx) ..."
                Invoke-Run { & pipx uninstall $pkg }
                Write-Ok "$pkg uninstalled"
                continue
            }
        }
        Write-Info "$pkg not installed - skipping"
    }

    Write-Host ""
    Write-Ok "Uninstall complete."
    exit 0
}

# ===========================================================================
# INSTALL PATH
# ===========================================================================

Write-Host ""
Write-Host "Adservio Claude Code Toolbox - Installer" -ForegroundColor White
Write-Host ""
Write-Info "Prerequisites: Python ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR}+, pipx (installed automatically)"
Write-Host ""

# ===========================================================================
# STEP 1: Check Python + capabilities
# ===========================================================================

Write-Step 1 $TotalSteps "Check Python ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR}+ and capabilities"

$Python = Find-Python

if (-not $Python) {
    Write-Err "Python ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR}+ is required but not found."
    Write-Host ""
    Write-Info "Install Python using one of these methods:"
    Write-Host ""
    Write-Host "  winget install Python.Python.3.12        " -ForegroundColor White -NoNewline
    Write-Host "# Windows Package Manager (recommended)"
    Write-Host "  scoop install python                     " -ForegroundColor White -NoNewline
    Write-Host "# Scoop"
    Write-Host "  choco install python312                  " -ForegroundColor White -NoNewline
    Write-Host "# Chocolatey"
    Write-Host ""
    Write-Info "Or download from https://www.python.org/downloads/"
    Write-Warn "Check 'Add Python to PATH' during installation!"
    Write-Host ""
    exit 2
}

Write-Ok "Python $($Python.Version) ($($Python.Cmd)$(if($Python.Args){' ' + ($Python.Args -join ' ')}))"

# Probe capabilities
$HasPip = Test-Pip
$HasVenv = Test-Venv
$IsExternallyManaged = Test-ExternallyManaged

if (-not $HasPip) {
    Write-Err "Python pip module is required but not available."
    Write-Host ""
    Write-Info "Install pip:"
    Write-Host "  $(if($Python.Cmd -eq 'py'){'py -3'}else{$Python.Cmd}) -m ensurepip --user"
    Write-Host ""
    Write-Info "Or reinstall Python with pip included (check the box during install)."
    Write-Host ""
    exit 2
}
Write-Ok "pip available"

if ($HasVenv) {
    Write-Ok "venv available"
} else {
    Write-Warn "venv not available - pipx may not work."
    Write-Warn "Reinstall Python and ensure the 'py launcher' and 'pip' options are checked."
}

if ($IsExternallyManaged) {
    Write-Warn "PEP 668: This Python is externally managed."
    Write-Info "The installer will try pipx from PATH or suggest system install."
}

# ===========================================================================
# STEP 2: Select install track
# ===========================================================================

Write-Step 2 $TotalSteps "Select install track"

$UsePipx = $false
$InstallTrack = ""

if ($HasVenv -or (Test-Command "pipx")) {
    # Track A: try pipx
    if (Ensure-Pipx) {
        $UsePipx = $true
        $InstallTrack = "A"
        Write-Ok "Track A: pipx (isolated environments)"
    } else {
        if ($IsExternallyManaged) {
            Write-Err "Cannot proceed: pip --user is blocked (PEP 668) and pipx is not available."
            Write-Host ""
            Write-Info "Install pipx first, then re-run this script:"
            Write-Host "  winget install pipx && pipx ensurepath" -ForegroundColor White
            Write-Host ""
            exit 2
        }
        Write-Warn "Falling back to Track B (pip --user)."
        $InstallTrack = "B"
    }
} else {
    if ($IsExternallyManaged) {
        Write-Err "Cannot proceed: pip --user is blocked (PEP 668) and pipx is not available."
        Write-Host ""
        Write-Info "Install pipx first, then re-run this script:"
        Write-Host "  winget install pipx && pipx ensurepath" -ForegroundColor White
        Write-Host ""
        exit 2
    }
    $InstallTrack = "B"
    Write-Info "Track B: pip --user (no venv available for pipx)"
}

if ($InstallTrack -eq "B") {
    Write-Ok "Track B: pip --user"
    Write-Warn "Less isolation than pipx. Consider installing pipx for Track A."
}

# ===========================================================================
# STEP 3: Install memctl
# ===========================================================================

Write-Step 3 $TotalSteps "Install memctl"

if ($UsePipx) {
    Invoke-PipxInstall -Spec $MEMCTL_SPEC -DisplayName "memctl"
} else {
    Invoke-PipFallbackInstall -Spec $MEMCTL_SPEC -DisplayName "memctl"
}

if (Test-Command "memctl") {
    Write-Ok "memctl on PATH: $((Get-Command memctl).Source)"
} else {
    Write-Warn "memctl installed but not on PATH - restart your terminal"
}

# ===========================================================================
# STEP 4: Install CloakMCP
# ===========================================================================

Write-Step 4 $TotalSteps "Install CloakMCP"

if ($UsePipx) {
    Invoke-PipxInstall -Spec $CLOAKMCP_SPEC -DisplayName "cloakmcp"
} else {
    Invoke-PipFallbackInstall -Spec $CLOAKMCP_SPEC -DisplayName "cloakmcp"
}

if (Test-Command "cloak") {
    Write-Ok "cloak on PATH: $((Get-Command cloak).Source)"
} else {
    Write-Warn "cloak installed but not on PATH - restart your terminal"
}

# ===========================================================================
# STEP 5: Install adservio-toolbox (from GitHub release)
# ===========================================================================

Write-Step 5 $TotalSteps "Install adservio-toolbox"

$tbVersion = if ($Version) { $Version } else { $TOOLBOX_VERSION }
$tbTarball = "adservio-toolbox-${tbVersion}.tar.gz"
$tbUrl     = "https://github.com/${GITHUB_REPO}/releases/download/v${tbVersion}/${tbTarball}"

# Resolution order: local file > download from release
$tbSource = $null
if (Test-Path $tbTarball) {
    $tbSource = ".\$tbTarball"
    Write-Info "Using local tarball: $tbTarball"
} elseif (Test-Path (Join-Path (Split-Path $PSScriptRoot) "release\$tbTarball")) {
    $tbSource = Join-Path (Split-Path $PSScriptRoot) "release\$tbTarball"
    Write-Info "Using release/ tarball: $tbSource"
} else {
    $tbSource = $tbUrl
    Write-Info "Installing from GitHub release: $tbUrl"
}

if ($UsePipx) {
    $listed = & pipx list --short 2>$null
    if ($Upgrade -and ($listed -match "^adservio-toolbox ")) {
        Write-Info "Upgrading adservio-toolbox ..."
        Invoke-Run { & pipx install --force $tbSource }
        Write-Ok "adservio-toolbox upgraded"
    } elseif ($listed -match "^adservio-toolbox ") {
        Write-Ok "adservio-toolbox already installed (use -Upgrade to force)"
    } else {
        Write-Info "Installing adservio-toolbox ..."
        Invoke-Run { & pipx install $tbSource }
        Write-Ok "adservio-toolbox installed"
    }
} else {
    Write-Info "Installing adservio-toolbox via pip --user ..."
    $pipArgs = @("-m", "pip", "install", "--user", $tbSource)
    if ($Upgrade) { $pipArgs += "--upgrade" }
    Invoke-Run { Invoke-Python $pipArgs }
    Write-Ok "adservio-toolbox installed (pip --user)"
}

if (Test-Command "toolboxctl") {
    Write-Ok "toolboxctl on PATH: $((Get-Command toolboxctl).Source)"
} else {
    Write-Warn "toolboxctl installed but not on PATH - restart your terminal"
}

# ===========================================================================
# STEP 6: Wire Claude Code globally
# ===========================================================================

Write-Step 6 $TotalSteps "Wire Claude Code globally"

if ($SkipGlobal) {
    Write-Info "Skipped (-SkipGlobal). Run 'toolboxctl install --global' later."
} elseif (Test-Command "toolboxctl") {
    Invoke-Run { & toolboxctl install --global }
    Write-Ok "Global wiring complete"
} else {
    Write-Warn "toolboxctl not on PATH - cannot wire Claude Code."
    Write-Warn "Restart your terminal, then run: toolboxctl install --global"
}

# ===========================================================================
# STEP 7: Doctor
# ===========================================================================

Write-Step 7 $TotalSteps "Verify installation"

if (Test-Command "toolboxctl") {
    if (-not $DryRun) {
        & toolboxctl doctor
    } else {
        Write-Info "[dry-run] toolboxctl doctor"
    }
} else {
    Write-Warn "toolboxctl not on PATH - skipping doctor."
    Write-Warn "Restart your terminal, then run: toolboxctl doctor"
}

# ===========================================================================
# Summary
# ===========================================================================

Write-Host ""
Write-Host "=== Installation complete ===" -ForegroundColor Green
Write-Host ""

$trackLabel = if ($UsePipx) { "pipx" } else { "pip --user" }
Write-Info "Install track: $InstallTrack ($trackLabel)"

if ($SkipGlobal) {
    Write-Info "Tools installed. Global Claude Code wiring was skipped."
    Write-Info "To wire later: toolboxctl install --global"
} else {
    Write-Info "Tools installed and Claude Code wired globally."
}

Write-Host ""
Write-Info "Next steps:"
Write-Info "  1. Restart your terminal (for PATH changes)"
Write-Info "  2. Navigate to a project: cd C:\path\to\your-project"
Write-Info "  3. Initialize: toolboxctl init"
Write-Info "  4. Check health: toolboxctl doctor"
Write-Host ""

if ($UsePipx) {
    Write-Info "Upgrade later:  .\install.ps1 -Upgrade"
    Write-Info "Uninstall:      .\install.ps1 -Uninstall"
} else {
    Write-Info "Upgrade: pip install --user --upgrade memctl[mcp,docs] cloakmcp adservio-toolbox"
}
Write-Host ""
