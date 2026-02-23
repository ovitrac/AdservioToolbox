"""Playground: verify installed tools and run smoke tests.

Two modes:
  - Standard (pipx): verifies tools on PATH, runs smoke tests directly.
  - Dev (pyproject.toml in cwd): creates .playground/venv/, installs editable,
    runs smoke tests against the venv.

Creates .playground/playground.log with test results.
"""

from __future__ import annotations

import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from toolbox.helpers import die, error, info, run, warn

PLAYGROUND_DIR = ".playground"
LOG_FILE = f"{PLAYGROUND_DIR}/playground.log"

MEMCTL_SPEC = "memctl[mcp,docs]"
CLOAKMCP_SPEC = "cloakmcp"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _log(lines: list[str], path: Path) -> None:
    """Append lines to the log file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        for line in lines:
            fh.write(line + "\n")


def _check_cmd(cmd: str) -> tuple[bool, str]:
    """Return (found, path_or_msg) for a CLI tool."""
    path = shutil.which(cmd)
    if path:
        return True, path
    return False, "not found"


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

    # Detect mode: dev (pyproject.toml present) vs standard (pipx)
    dev_mode = (cwd / "pyproject.toml").exists()

    log_entries: list[str] = [
        f"# Playground log — {datetime.now(timezone.utc).isoformat()}",
        f"# Mode: {'dev (editable)' if dev_mode else 'standard (PATH)'}",
        "",
    ]

    if dev_mode:
        # Dev mode: create venv, install editable + deps
        venv_path = cwd / PLAYGROUND_DIR / "venv"
        if venv_path.exists():
            info("Playground venv already exists, reusing.")
        else:
            info("Creating playground venv …")
            run([sys.executable, "-m", "venv", str(venv_path)])

        py = str(venv_path / "bin" / "python")
        run([py, "-m", "pip", "install", "--upgrade", "pip"], quiet=True)

        info("Installing toolbox (editable) + deps …")
        r = run([py, "-m", "pip", "install", "-e", str(cwd)], check=False, quiet=True)
        log_entries.append(f"toolbox install: {'OK' if r.returncode == 0 else 'FAIL'}")

        info("Installing memctl …")
        r = run([py, "-m", "pip", "install", MEMCTL_SPEC], check=False, quiet=True)
        log_entries.append(f"memctl install: {'OK' if r.returncode == 0 else 'FAIL'}")

        info("Installing CloakMCP …")
        r = run([py, "-m", "pip", "install", CLOAKMCP_SPEC], check=False, quiet=True)
        log_entries.append(f"CloakMCP install: {'OK' if r.returncode == 0 else 'FAIL'}")

        toolboxctl_bin = str(venv_path / "bin" / "toolboxctl")
        memctl_bin = str(venv_path / "bin" / "memctl")
        cloak_bin = str(venv_path / "bin" / "cloak")
    else:
        # Standard mode: verify tools on PATH
        info("Verifying installed tools …")

        for cmd in ("toolboxctl", "memctl", "cloak"):
            found, path = _check_cmd(cmd)
            if found:
                info(f"  {cmd}: {path}")
                log_entries.append(f"{cmd}: {path}")
            else:
                error(f"  {cmd}: not found — run 'toolboxctl install' first")
                log_entries.append(f"{cmd}: NOT FOUND")

        toolboxctl_bin = shutil.which("toolboxctl") or "toolboxctl"
        memctl_bin = shutil.which("memctl") or "memctl"
        cloak_bin = shutil.which("cloak") or "cloak"

    # Smoke tests
    info("Running smoke tests …")
    tests_passed = 0
    tests_failed = 0

    smoke_tests = [
        ([toolboxctl_bin, "--version"], "toolboxctl --version"),
        ([toolboxctl_bin, "status"], "toolboxctl status"),
        ([memctl_bin, "--version"], "memctl --version"),
        ([cloak_bin, "--version"], "cloak --version"),
    ]

    for cmd, label in smoke_tests:
        r = run(cmd, check=False, quiet=True)
        ok = r.returncode == 0
        status = "PASS" if ok else "FAIL"
        log_entries.append(f"  {status}: {label}")
        if ok:
            tests_passed += 1
            info(f"  PASS: {label}")
        else:
            tests_failed += 1
            error(f"  FAIL: {label}")

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
