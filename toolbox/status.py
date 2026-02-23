"""Deterministic status report — safe to paste into issues."""

from __future__ import annotations

import platform
import shutil
import sys
from pathlib import Path

from toolbox import __version__
from toolbox.config import CONFIG_FILENAME, find_config, load_config
from toolbox.helpers import info, print_table, run

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _pkg_version(pip_name: str) -> str | None:
    """Return the installed version of a pip package, or None."""
    result = run(
        [sys.executable, "-m", "pip", "show", pip_name],
        check=False,
        quiet=True,
    )
    if result.returncode != 0:
        return None
    for line in result.stdout.splitlines():
        if line.startswith("Version:"):
            return line.split(":", 1)[1].strip()
    return None


def _check_commands(cwd: Path) -> list[str]:
    """Return list of installed slash commands in .claude/commands/."""
    commands_dir = cwd / ".claude" / "commands"
    if not commands_dir.is_dir():
        return []
    return sorted(f.stem for f in commands_dir.iterdir() if f.suffix == ".md")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def cmd_status(args) -> None:
    """Entry point for ``toolboxctl status``."""
    cwd = Path.cwd()
    config_path = find_config(cwd)
    cfg = load_config(config_path)

    memctl_ver = _pkg_version("memctl") or "not installed"
    cloak_ver = _pkg_version("cloakmcp") or "not installed"
    git_ok = "yes" if shutil.which("git") else "no"
    eco_state = "on" if cfg.get("eco", {}).get("enabled_global") else "off"
    commands = _check_commands(cwd)
    commands_str = ", ".join(f"/{c}" for c in commands) if commands else "none"

    rows = [
        ("toolboxctl", __version__),
        ("Python", f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"),
        ("Platform", platform.platform()),
        ("git", git_ok),
        ("memctl", memctl_ver),
        ("CloakMCP", cloak_ver),
        ("Config", str(config_path) if config_path else "not found"),
        ("Eco mode", eco_state),
        ("Commands", commands_str),
    ]

    info("Adservio Toolbox — status")
    print_table(rows, headers=["Component", "Value"])
