"""Install memctl and CloakMCP into the current Python environment.

All interaction with sub-projects is via subprocess — no Python-level imports.

Supports two modes:
- Default: pip install memctl + CloakMCP + inject global Bash permissions
- ``--global``: additionally wire CloakMCP hooks and CLAUDE.md into ~/.claude/
- ``--uninstall``: reverse global wiring (does not uninstall packages)
"""

from __future__ import annotations

import sys

from toolbox.helpers import die, error, info, run, warn

MEMCTL_SPEC = "memctl[mcp]"
CLOAKMCP_SPEC = "cloakmcp"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _pip(*args: str, check: bool = True) -> bool:
    """Run pip via the current interpreter."""
    cmd = [sys.executable, "-m", "pip", *args]
    result = run(cmd, check=False, quiet=True)
    if result.returncode != 0:
        if check:
            error(f"pip failed: {result.stderr.strip()}")
        return False
    return True


def _is_installed(package: str) -> bool:
    """Check if a package is already installed (pip show)."""
    cmd = [sys.executable, "-m", "pip", "show", package]
    result = run(cmd, check=False, quiet=True, capture=True)
    return result.returncode == 0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def cmd_install(args) -> None:
    """Entry point for ``toolboxctl install``."""
    do_global: bool = getattr(args, "do_global", False)
    do_uninstall: bool = getattr(args, "uninstall", False)
    fts: str = getattr(args, "fts", "fr")
    upgrade: bool = getattr(args, "upgrade", False)

    # --- Uninstall path (global only) ------------------------------------
    if do_uninstall:
        from toolbox.global_wiring import uninstall_global
        uninstall_global()
        return

    pip_extra: list[str] = []
    if upgrade:
        pip_extra.append("--upgrade")

    # --- memctl -----------------------------------------------------------
    if _is_installed("memctl") and not upgrade:
        info("memctl is already installed (use --upgrade to force).")
    else:
        info("Installing memctl …")
        if not _pip("install", *pip_extra, MEMCTL_SPEC):
            die("Failed to install memctl.", code=2)
        info("memctl installed.")

    # --- CloakMCP ---------------------------------------------------------
    if _is_installed("cloakmcp") and not upgrade:
        info("CloakMCP is already installed (use --upgrade to force).")
    else:
        info("Installing CloakMCP …")
        if not _pip("install", *pip_extra, CLOAKMCP_SPEC):
            die("Failed to install CloakMCP.", code=2)
        info("CloakMCP installed.")

    # --- Global permissions (always) --------------------------------------
    from toolbox.global_wiring import install_global_permissions
    install_global_permissions()

    # --- Full global wiring (hooks + CLAUDE.md) ---------------------------
    if do_global:
        from toolbox.global_wiring import install_global_hooks, install_global_claude_md
        install_global_hooks()
        install_global_claude_md()
        info("Global wiring complete. Run 'toolboxctl doctor' to verify.")

    # --- FTS hint ---------------------------------------------------------
    if fts and fts != "fr":
        warn(f"FTS language set to '{fts}' — pass the same value to 'toolboxctl init'.")

    info("Install complete.")
