#!/usr/bin/env python3
"""Adservio Claude Code Toolbox — Cross-Platform Bootstrap Installer.

Pure Python (stdlib-only) installer that works on Windows, macOS, and Linux
without Git Bash, PowerShell expertise, or external dependencies.

Installs memctl, CloakMCP, and toolboxctl via pipx (Track A), pip --user
(Track B), or optionally via uv when no compliant Python is available
(Track C — fallback only).

Prerequisites: Python 3.10+
Usage:
    python install.py                  # full install + global wiring
    python install.py --skip-global    # install tools only
    python install.py --version 0.4.5  # pin to a specific version
    python install.py --upgrade        # upgrade existing installations
    python install.py --uninstall      # reverse everything
    python install.py --dry-run        # preview actions

Author: Olivier Vitrac, PhD, HDR | olivier.vitrac@adservio.fr | Adservio
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TOOLBOX_VERSION = "__TOOLBOX_VERSION__"
GITHUB_REPO = "ovitrac/AdservioToolbox"
TOOLBOX_SPEC = "adservio-toolbox"
MEMCTL_SPEC = "memctl[mcp,docs]"
CLOAKMCP_SPEC = "cloakmcp"
MIN_PYTHON = (3, 10)
TOTAL_STEPS = 7

IS_WINDOWS = sys.platform == "win32"

# ---------------------------------------------------------------------------
# ANSI helpers (TTY-aware)
# ---------------------------------------------------------------------------

_use_color = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
if IS_WINDOWS:
    # Enable ANSI on Windows 10+ if possible
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        _use_color = False

_B = "\033[1m" if _use_color else ""
_R = "\033[0m" if _use_color else ""
_GREEN = "\033[32m" if _use_color else ""
_YELLOW = "\033[33m" if _use_color else ""
_RED = "\033[31m" if _use_color else ""
_CYAN = "\033[36m" if _use_color else ""


def step(n: int, msg: str) -> None:
    print(f"{_B}{_CYAN}[STEP {n}/{TOTAL_STEPS}]{_R} {msg}")


def ok(msg: str) -> None:
    print(f"{_GREEN}[OK]{_R}    {msg}")


def info(msg: str) -> None:
    print(f"{_CYAN}[INFO]{_R}  {msg}")


def warn(msg: str) -> None:
    print(f"{_YELLOW}[WARN]{_R}  {msg}")


def err(msg: str) -> None:
    print(f"{_RED}[ERROR]{_R} {msg}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Dry-run wrapper
# ---------------------------------------------------------------------------

DRY_RUN = False


def run_cmd(
    cmd: list[str],
    *,
    check: bool = True,
    capture: bool = False,
    quiet: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Execute a command, respecting dry-run mode."""
    if DRY_RUN and not capture:
        info(f"[dry-run] {' '.join(cmd)}")
        return subprocess.CompletedProcess(cmd, 0, "", "")
    kwargs: dict = {"text": True}
    if capture or quiet:
        kwargs["capture_output"] = True
    try:
        return subprocess.run(cmd, check=check, **kwargs)
    except FileNotFoundError:
        if check:
            raise
        return subprocess.CompletedProcess(cmd, 127, "", f"{cmd[0]}: not found")


# ---------------------------------------------------------------------------
# Python detection
# ---------------------------------------------------------------------------


def find_python() -> tuple[str, str] | None:
    """Find a compliant Python interpreter.

    Returns (python_cmd, version_string) or None.
    """
    candidates = []
    if IS_WINDOWS:
        # py launcher first (standard Windows Python discovery)
        candidates.extend(["py", "python3", "python"])
    else:
        candidates.extend(["python3", "python"])

    for candidate in candidates:
        path = shutil.which(candidate)
        if not path:
            continue
        cmd = [candidate]
        if candidate == "py":
            cmd.append("-3")
        try:
            result = subprocess.run(
                [*cmd, "-c",
                 "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode != 0:
                continue
            ver = result.stdout.strip()
            major, minor = (int(x) for x in ver.split("."))
            if (major, minor) >= MIN_PYTHON:
                return (" ".join(cmd), ver)
        except Exception:
            continue
    return None


# ---------------------------------------------------------------------------
# Capability probes
# ---------------------------------------------------------------------------


def probe_pip(python_cmd: str) -> bool:
    """Check if pip module is available."""
    args = python_cmd.split() + ["-m", "pip", "--version"]
    result = run_cmd(args, check=False, capture=True)
    return result.returncode == 0


def probe_venv(python_cmd: str) -> bool:
    """Check if venv module is available."""
    args = python_cmd.split() + ["-c", "import venv"]
    result = run_cmd(args, check=False, capture=True)
    return result.returncode == 0


def probe_pep668(python_cmd: str) -> bool:
    """Detect PEP 668 externally-managed Python."""
    args = python_cmd.split() + [
        "-c",
        "import sysconfig; from pathlib import Path; "
        "print(Path(sysconfig.get_path('stdlib'), 'EXTERNALLY-MANAGED').exists())",
    ]
    result = run_cmd(args, check=False, capture=True)
    return result.stdout.strip() == "True"


def find_pipx() -> str | None:
    """Find pipx on PATH. Returns the command string or None."""
    if shutil.which("pipx"):
        return "pipx"
    # Check common user install location
    local_pipx = Path.home() / ".local" / "bin" / "pipx"
    if local_pipx.exists():
        return str(local_pipx)
    if IS_WINDOWS:
        # Windows: check Scripts directory
        for scripts_dir in [
            Path.home() / "AppData" / "Roaming" / "Python" / "Scripts",
            Path.home() / ".local" / "bin",
        ]:
            candidate = scripts_dir / "pipx.exe"
            if candidate.exists():
                return str(candidate)
    return None


def find_uv() -> str | None:
    """Find uv on PATH."""
    path = shutil.which("uv")
    return path if path else None


def probe_pipx_health(pipx_cmd: str = "pipx") -> bool:
    """Verify pipx is functional, not just present on PATH.

    Guards against stale shims, broken venvs, or removed Python interpreters.
    """
    result = run_cmd([pipx_cmd, "--version"], check=False, capture=True)
    return result.returncode == 0


# ---------------------------------------------------------------------------
# Install hints (platform-specific guidance)
# ---------------------------------------------------------------------------


def detect_platform() -> str:
    """Detect platform for actionable error messages."""
    if IS_WINDOWS:
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    try:
        with open("/etc/os-release") as f:
            content = f.read()
        for line in content.splitlines():
            if line.startswith("ID="):
                distro_id = line.split("=", 1)[1].strip().strip('"')
                if distro_id in ("ubuntu", "debian", "linuxmint", "pop"):
                    return "debian"
                if distro_id in ("rhel", "centos", "fedora", "rocky", "alma"):
                    return "rhel"
                if distro_id == "alpine":
                    return "alpine"
                if distro_id in ("arch", "manjaro"):
                    return "arch"
                if distro_id.startswith("opensuse") or distro_id == "sles":
                    return "suse"
    except FileNotFoundError:
        pass
    return "unknown"


def print_python_hint() -> None:
    plat = detect_platform()
    err(f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ is required but not found.")
    print()
    hints = {
        "debian": "sudo apt-get update && sudo apt-get install -y python3 python3-venv python3-pip",
        "rhel": "sudo dnf install -y python3 python3-pip",
        "alpine": "apk add python3 py3-pip",
        "arch": "sudo pacman -S python python-pip",
        "suse": "sudo zypper install -y python3 python3-pip python3-venv",
        "macos": "brew install python@3.12",
        "windows": "Download from https://www.python.org/downloads/\n"
                   "  Or: winget install Python.Python.3.12",
    }
    info(f"  {hints.get(plat, 'Download from https://www.python.org/downloads/')}")
    print()
    info("Detailed guide: https://github.com/ovitrac/AdservioToolbox/blob/main/docs/INSTALLING_PYTHON.md")
    print()


def print_pipx_hint() -> None:
    """Print OS-specific instructions for installing pipx."""
    plat = detect_platform()
    print()
    info("pipx is required to install tools in isolated environments.")
    info("Install pipx from your system package manager:")
    print()
    hints = {
        "debian": "sudo apt install -y pipx && pipx ensurepath",
        "rhel": "sudo dnf install -y pipx && pipx ensurepath",
        "arch": "sudo pacman -S python-pipx && pipx ensurepath",
        "suse": "sudo zypper install -y python3-pipx && pipx ensurepath",
        "macos": "brew install pipx && pipx ensurepath",
        "windows": "pip install --user pipx && pipx ensurepath",
    }
    info(f"  {hints.get(plat, 'See https://pipx.pypa.io/stable/installation/')}")
    print()
    info("Then re-run this script.")
    print()


# ---------------------------------------------------------------------------
# pipx helpers
# ---------------------------------------------------------------------------


def ensure_pipx(python_cmd: str, is_pep668: bool) -> str | None:
    """Ensure pipx is available and functional. Returns pipx command or None.

    Called only when the initial pipx health check failed.
    Attempts to bootstrap pipx via pip when possible.
    """
    existing = find_pipx()
    if existing and probe_pipx_health(existing):
        ok(f"pipx functional: {existing}")
        return existing

    if existing:
        warn(f"pipx found at {existing} but not functional — attempting reinstall")

    # PEP 668: defense-in-depth (caller should have caught this already)
    if is_pep668:
        print_pipx_hint()
        return None

    info("Bootstrapping pipx via pip ...")
    args = python_cmd.split() + ["-m", "pip", "install", "--user", "pipx"]
    result = run_cmd(args, check=False)
    if result.returncode != 0:
        warn("Could not bootstrap pipx via pip.")
        return None

    # Try ensurepath
    run_cmd(["pipx", "ensurepath"], check=False, quiet=True)

    # Re-check with functional probe
    found = find_pipx()
    if found and probe_pipx_health(found):
        ok(f"pipx installed: {found}")
        return found

    if found:
        warn(f"pipx installed at {found} but health check failed")
    return None


def pipx_install(
    pipx_cmd: str,
    spec: str,
    display_name: str,
    *,
    version: str = "",
    upgrade: bool = False,
    source: str = "",
) -> None:
    """Install a package via pipx."""
    # Check if already installed
    result = run_cmd(
        [pipx_cmd, "list", "--short"], check=False, capture=True,
    )
    installed = any(
        line.startswith(f"{display_name} ")
        for line in result.stdout.splitlines()
    )

    if upgrade and installed:
        info(f"Upgrading {display_name} ...")
        run_cmd([pipx_cmd, "upgrade", display_name])
        ok(f"{display_name} upgraded")
        return

    if installed and not upgrade:
        ok(f"{display_name} already installed (use --upgrade to force)")
        return

    install_target = source if source else spec
    if version and not source:
        install_target = f"{spec}=={version}"

    info(f"Installing {display_name} ...")
    cmd = [pipx_cmd, "install"]
    if source and installed:
        cmd.append("--force")
    cmd.append(install_target)
    run_cmd(cmd)
    ok(f"{display_name} installed")


def pip_install(
    python_cmd: str,
    spec: str,
    display_name: str,
    *,
    version: str = "",
    upgrade: bool = False,
    source: str = "",
) -> None:
    """Install a package via pip --user (Track B fallback)."""
    install_target = source if source else spec
    if version and not source:
        install_target = f"{spec}=={version}"

    cmd = python_cmd.split() + ["-m", "pip", "install", "--user"]
    if upgrade:
        cmd.append("--upgrade")
    cmd.append(install_target)

    info(f"Installing {display_name} via pip --user (fallback) ...")
    run_cmd(cmd)
    ok(f"{display_name} installed (pip --user)")


# ---------------------------------------------------------------------------
# Verify command on PATH
# ---------------------------------------------------------------------------


def verify_on_path(name: str, exe_name: str | None = None) -> None:
    """Check if a command is available on PATH after install."""
    exe = exe_name or name
    if shutil.which(exe):
        ok(f"{name} on PATH: {shutil.which(exe)}")
        return
    # Check common locations
    local_bin = Path.home() / ".local" / "bin" / exe
    if IS_WINDOWS:
        local_bin = Path.home() / ".local" / "bin" / f"{exe}.exe"
    if local_bin.exists():
        warn(f"{name} installed at {local_bin} but not on PATH")
    else:
        warn(f"{name} installed but not on PATH — check ~/.local/bin")


# ---------------------------------------------------------------------------
# Toolbox tarball resolution
# ---------------------------------------------------------------------------


def resolve_toolbox_source(version: str) -> str:
    """Resolve the toolbox installation source (local tarball or GitHub URL)."""
    tarball = f"adservio-toolbox-{version}.tar.gz"

    # Check current directory
    if Path(tarball).exists():
        info(f"Using local tarball: {tarball}")
        return f"./{tarball}"

    # Check release/ directory relative to this script
    script_dir = Path(__file__).resolve().parent
    release_tarball = script_dir.parent / "release" / tarball
    if release_tarball.exists():
        info(f"Using release/ tarball: {release_tarball}")
        return str(release_tarball)

    # Download from GitHub
    url = f"https://github.com/{GITHUB_REPO}/releases/download/v{version}/{tarball}"
    info(f"Installing from GitHub release: {url}")
    return url


# ===========================================================================
# UNINSTALL
# ===========================================================================


def do_uninstall(python_cmd: str) -> None:
    """Remove global wiring and uninstall all packages."""
    step(1, "Remove global Claude Code wiring")

    if shutil.which("toolboxctl"):
        run_cmd(["toolboxctl", "install", "--uninstall"])
        ok("Global wiring removed")
    else:
        warn("toolboxctl not found — skipping global wiring removal")

    step(2, "Uninstall packages")

    pipx_cmd = find_pipx()

    for pkg in ["adservio-toolbox", "cloakmcp", "memctl"]:
        if pipx_cmd:
            result = run_cmd([pipx_cmd, "list", "--short"], check=False, capture=True)
            if any(line.startswith(f"{pkg} ") for line in result.stdout.splitlines()):
                info(f"Removing {pkg} (pipx) ...")
                run_cmd([pipx_cmd, "uninstall", pkg])
                ok(f"{pkg} uninstalled")
                continue

        # Try pip
        args = python_cmd.split() + ["-m", "pip", "show", pkg]
        result = run_cmd(args, check=False, capture=True)
        if result.returncode == 0:
            info(f"Removing {pkg} (pip) ...")
            run_cmd(python_cmd.split() + ["-m", "pip", "uninstall", "-y", pkg])
            ok(f"{pkg} uninstalled")
        else:
            info(f"{pkg} not installed — skipping")

    print()
    ok("Uninstall complete.")


# ===========================================================================
# INSTALL
# ===========================================================================


def do_install(args: argparse.Namespace) -> None:
    """Main install flow."""
    print()
    print(f"{_B}Adservio Claude Code Toolbox — Installer{_R}")
    print()
    info(f"Prerequisites: Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+")
    print()

    # ── Step 1: Find Python and package tools ───────────────────────────
    step(1, f"Check Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ and package tools")

    python_info = find_python()
    if not python_info:
        print_python_hint()
        sys.exit(2)

    python_cmd, python_ver = python_info
    ok(f"Python {python_ver} ({python_cmd})")

    # --- 1b: Check pipx health first (pipx-first policy) ---
    # If pipx is already present and functional, pip is not needed at all.
    # Modern distros often ship pipx from the system package manager without pip.
    pipx_ready = False
    existing_pipx = find_pipx()
    if existing_pipx and probe_pipx_health(existing_pipx):
        pipx_ready = True
        ok(f"pipx functional ({existing_pipx})")

    # --- 1c: Probe pip/venv/PEP668 only if pipx is not ready ---
    has_pip = False
    has_venv = False
    is_pep668 = False

    if not pipx_ready:
        has_pip = probe_pip(python_cmd)
        has_venv = probe_venv(python_cmd)
        is_pep668 = probe_pep668(python_cmd)

        if has_pip:
            ok("pip available (for pipx bootstrap)")
        if has_venv:
            ok("venv available")
        else:
            warn("venv not available — pipx bootstrap may need it")

        # No pipx AND no pip → only path is OS package manager
        if not has_pip:
            err("Neither pipx nor pip is available.")
            err("pipx is required to install tools in isolated environments.")
            print_pipx_hint()
            sys.exit(2)

        # pip available but PEP 668 blocks pip install --user → can't bootstrap
        if is_pep668:
            err("pip is available but this Python is externally managed (PEP 668).")
            err("Cannot bootstrap pipx via pip — the system blocks pip install --user.")
            print_pipx_hint()
            sys.exit(2)

    # ── Step 2: Select install track ─────────────────────────────────────
    step(2, "Select install track")

    pipx_cmd_str: str | None = None
    install_track = ""

    if pipx_ready:
        # pipx already verified in Step 1 — use it directly (no pip needed)
        pipx_cmd_str = existing_pipx
        install_track = "A"
        ok("Track A: pipx (pre-installed, isolated environments)")
    else:
        pipx_cmd_str = ensure_pipx(python_cmd, is_pep668)
        if pipx_cmd_str:
            install_track = "A"
            ok("Track A: pipx (bootstrapped via pip)")
        else:
            install_track = "B"

    if install_track == "B":
        ok("Track B: pip --user")
        warn("Less isolation than pipx. Consider installing pipx from your package manager.")

    use_pipx = install_track == "A" and pipx_cmd_str is not None

    # ── Step 3: Install memctl ───────────────────────────────────────────
    step(3, "Install memctl")

    if use_pipx:
        pipx_install(
            pipx_cmd_str, MEMCTL_SPEC, "memctl",  # type: ignore[arg-type]
            version=args.version, upgrade=args.upgrade,
        )
    else:
        pip_install(
            python_cmd, MEMCTL_SPEC, "memctl",
            version=args.version, upgrade=args.upgrade,
        )
    verify_on_path("memctl")

    # ── Step 4: Install CloakMCP ─────────────────────────────────────────
    step(4, "Install CloakMCP")

    if use_pipx:
        pipx_install(
            pipx_cmd_str, CLOAKMCP_SPEC, "cloakmcp",  # type: ignore[arg-type]
            version=args.version, upgrade=args.upgrade,
        )
    else:
        pip_install(
            python_cmd, CLOAKMCP_SPEC, "cloakmcp",
            version=args.version, upgrade=args.upgrade,
        )
    verify_on_path("CloakMCP", "cloak")

    # ── Step 5: Install adservio-toolbox ─────────────────────────────────
    step(5, "Install adservio-toolbox")

    tb_version = args.version or TOOLBOX_VERSION
    tb_source = resolve_toolbox_source(tb_version)

    if use_pipx:
        pipx_install(
            pipx_cmd_str, TOOLBOX_SPEC, "adservio-toolbox",  # type: ignore[arg-type]
            version=args.version, upgrade=args.upgrade, source=tb_source,
        )
    else:
        pip_install(
            python_cmd, TOOLBOX_SPEC, "adservio-toolbox",
            version=args.version, upgrade=args.upgrade, source=tb_source,
        )
    verify_on_path("toolboxctl")

    # ── Step 6: Wire Claude Code globally ────────────────────────────────
    step(6, "Wire Claude Code globally")

    if args.skip_global:
        info("Skipped (--skip-global). Run 'toolboxctl install --global' later.")
    elif shutil.which("toolboxctl"):
        run_cmd(["toolboxctl", "install", "--global"])
        ok("Global wiring complete")
    else:
        warn("toolboxctl not on PATH — cannot wire Claude Code.")
        warn("Run: toolboxctl install --global (after fixing PATH)")

    # ── Step 7: Doctor ───────────────────────────────────────────────────
    step(7, "Verify installation")

    if shutil.which("toolboxctl"):
        run_cmd(["toolboxctl", "doctor"])
    else:
        warn("toolboxctl not on PATH — skipping doctor.")
        warn("Verify after adding ~/.local/bin to PATH and restarting your shell.")

    # ── Summary ──────────────────────────────────────────────────────────
    print()
    print(f"{_B}=== Installation complete ==={_R}")
    print()

    track_desc = "pipx" if use_pipx else "pip --user"
    info(f"Install track: {install_track} ({track_desc})")

    if args.skip_global:
        info("Tools installed. Global Claude Code wiring was skipped.")
        info("To wire later: toolboxctl install --global")
    else:
        info("Tools installed and Claude Code wired globally.")

    print()
    info("Next steps:")
    info("  1. Open a terminal (or restart your shell for PATH changes)")
    info("  2. Navigate to a project: cd /path/to/your-project")
    info("  3. Initialize: toolboxctl init")
    info("  4. Check health: toolboxctl doctor")
    print()

    if use_pipx:
        info("Upgrade later: python install.py --upgrade")
        info("Uninstall:     python install.py --uninstall")
    else:
        info("Upgrade: pip install --user --upgrade memctl[mcp,docs] cloakmcp adservio-toolbox")
    print()


# ===========================================================================
# CLI
# ===========================================================================


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Adservio Claude Code Toolbox — Cross-Platform Bootstrap Installer",
    )
    parser.add_argument(
        "--version", default="", metavar="VER",
        help="Pin all packages to version VER (e.g., 0.4.5)",
    )
    parser.add_argument(
        "--skip-global", action="store_true",
        help="Install tools only, do not wire ~/.claude/",
    )
    parser.add_argument(
        "--upgrade", action="store_true",
        help="Upgrade existing installations",
    )
    parser.add_argument(
        "--uninstall", action="store_true",
        help="Remove global wiring and uninstall all packages",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview actions without executing",
    )

    args = parser.parse_args()

    global DRY_RUN
    DRY_RUN = args.dry_run

    if args.uninstall:
        python_info = find_python()
        python_cmd = python_info[0] if python_info else "python3"
        do_uninstall(python_cmd)
        sys.exit(0)

    do_install(args)


if __name__ == "__main__":
    main()
