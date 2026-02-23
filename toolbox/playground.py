"""Playground: create an isolated venv, install from origin, run smoke tests.

Creates .playground/ in the current directory with:
  .playground/venv/          — isolated Python virtual environment
  .playground/playground.log — test results log
"""

from __future__ import annotations

import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from toolbox.helpers import die, error, info, run, warn

PLAYGROUND_DIR = ".playground"
VENV_DIR = f"{PLAYGROUND_DIR}/venv"
LOG_FILE = f"{PLAYGROUND_DIR}/playground.log"

MEMCTL_SPEC = "memctl[mcp]"
CLOAKMCP_SPEC = "cloakmcp"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _venv_python() -> str:
    """Return path to the venv Python binary."""
    return str(Path(VENV_DIR) / "bin" / "python")


def _log(lines: list[str], path: Path) -> None:
    """Append lines to the log file."""
    with open(path, "a", encoding="utf-8") as fh:
        for line in lines:
            fh.write(line + "\n")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def cmd_playground(args) -> None:
    """Entry point for ``toolboxctl playground``."""
    clean: bool = getattr(args, "clean", False)
    cwd = Path.cwd()
    pg = cwd / PLAYGROUND_DIR
    log_path = cwd / LOG_FILE

    # Clean mode
    if clean:
        if pg.exists():
            shutil.rmtree(pg)
            info(f"Removed {pg}")
        else:
            warn(f"{pg} does not exist.")
        return

    # Create venv
    venv_path = cwd / VENV_DIR
    if venv_path.exists():
        info("Playground venv already exists, reusing.")
    else:
        info("Creating playground venv …")
        run([sys.executable, "-m", "venv", str(venv_path)])

    py = _venv_python()
    log_entries: list[str] = [
        f"# Playground log — {datetime.now(timezone.utc).isoformat()}",
        f"# Python: {py}",
        "",
    ]

    # Upgrade pip
    run([py, "-m", "pip", "install", "--upgrade", "pip"], quiet=True)

    # Install memctl
    info("Installing memctl into playground …")
    r = run([py, "-m", "pip", "install", MEMCTL_SPEC], check=False, quiet=True)
    log_entries.append(f"memctl install: {'OK' if r.returncode == 0 else 'FAIL'}")

    # Install CloakMCP
    info("Installing CloakMCP into playground …")
    r = run([py, "-m", "pip", "install", CLOAKMCP_SPEC], check=False, quiet=True)
    log_entries.append(f"CloakMCP install: {'OK' if r.returncode == 0 else 'FAIL'}")

    # Install toolbox (editable, from current directory)
    info("Installing toolbox (editable) into playground …")
    r = run([py, "-m", "pip", "install", "-e", str(cwd)], check=False, quiet=True)
    log_entries.append(f"toolbox install: {'OK' if r.returncode == 0 else 'FAIL'}")

    # Smoke tests
    info("Running smoke tests …")
    tests_passed = 0
    tests_failed = 0

    smoke_tests = [
        ([py, "-m", "pip", "show", "memctl"], "memctl is installed"),
        ([py, "-m", "pip", "show", "cloakmcp"], "CloakMCP is installed"),
        ([str(venv_path / "bin" / "toolboxctl"), "--version"], "toolboxctl --version"),
        ([str(venv_path / "bin" / "toolboxctl"), "status"], "toolboxctl status"),
    ]

    for cmd, label in smoke_tests:
        r = run(cmd, check=False, quiet=True)
        ok = r.returncode == 0
        status = "PASS" if ok else "FAIL"
        log_entries.append(f"  {status}: {label}")
        if ok:
            tests_passed += 1
        else:
            tests_failed += 1
            error(f"FAIL: {label}")

    # Summary
    log_entries.append("")
    log_entries.append(f"Passed: {tests_passed}/{tests_passed + tests_failed}")

    _log(log_entries, log_path)
    info(f"Log written to {log_path}")

    if tests_failed:
        error(f"{tests_failed} smoke test(s) failed.")
        sys.exit(1)
    else:
        info(f"All {tests_passed} smoke tests passed.")
