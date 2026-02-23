"""Diagnostic command — checks the full toolbox installation health.

Verifies: Python, pipx, Claude Code, memctl, CloakMCP, PATH resolution,
global hooks, permissions, and CLAUDE.md block.

Exit codes: 0 = all green, 1 = warnings, 2 = critical missing.
"""

from __future__ import annotations

import platform
import shutil
import sys
from pathlib import Path

from toolbox import __version__
from toolbox.helpers import _green, _red, _yellow, info, print_table, run, warn

# ---------------------------------------------------------------------------
# Check helpers
# ---------------------------------------------------------------------------

_OK = "ok"
_WARN = "warn"
_FAIL = "fail"


def _check_mark(status: str) -> str:
    """Return a colored status marker."""
    if status == _OK:
        return _green("\u2713")
    if status == _WARN:
        return _yellow("~")
    return _red("\u2717")


def _cmd_version(cmd: str) -> str | None:
    """Get version from a CLI tool, or None if not found."""
    path = shutil.which(cmd)
    if not path:
        return None
    # Try --version first
    result = run([cmd, "--version"], check=False, quiet=True)
    if result.returncode == 0 and result.stdout.strip():
        # Take first line, strip common prefixes
        line = result.stdout.strip().splitlines()[0]
        for prefix in [f"{cmd} ", "v"]:
            if line.lower().startswith(prefix):
                line = line[len(prefix):]
        return line.strip()
    # Fallback: just report "found"
    return "found"


def _pip_version(pip_name: str) -> str | None:
    """Return the installed version of a pip package, or None."""
    result = run(
        [sys.executable, "-m", "pip", "show", pip_name],
        check=False, quiet=True,
    )
    if result.returncode != 0:
        return None
    for line in result.stdout.splitlines():
        if line.startswith("Version:"):
            return line.split(":", 1)[1].strip()
    return None


def _pipx_available() -> str | None:
    """Return pipx version if available, else None."""
    pipx = shutil.which("pipx")
    if not pipx:
        return None
    result = run(["pipx", "--version"], check=False, quiet=True)
    if result.returncode == 0:
        return result.stdout.strip()
    return "found"


def _detect_install_method(cmd: str) -> str:
    """Detect how a tool was installed (pipx, pip, or unknown)."""
    path = shutil.which(cmd)
    if not path:
        return "not found"
    path_str = str(Path(path).resolve())
    if "pipx" in path_str or ".local/pipx" in path_str:
        return "pipx"
    if "site-packages" in path_str or ".venv" in path_str:
        return "pip/venv"
    return "system"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def cmd_doctor(args) -> None:
    """Entry point for ``toolboxctl doctor``."""
    # Lazy import to avoid circular dependency
    from toolbox.global_wiring import (
        check_global_claude_md,
        check_global_hooks,
        check_global_permissions,
    )

    checks: list[tuple[str, str, str, str]] = []  # (name, value, status, note)
    has_warn = False
    has_fail = False

    # --- Python -----------------------------------------------------------
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    py_ok = sys.version_info >= (3, 10)
    checks.append((
        "Python",
        py_ver,
        _OK if py_ok else _FAIL,
        "" if py_ok else "3.10+ required",
    ))

    # --- pipx -------------------------------------------------------------
    pipx_ver = _pipx_available()
    if pipx_ver:
        checks.append(("pipx", pipx_ver, _OK, ""))
    else:
        checks.append(("pipx", "not found", _WARN, "recommended for isolated installs"))
        has_warn = True

    # --- Claude Code ------------------------------------------------------
    claude_ver = _cmd_version("claude")
    if claude_ver:
        checks.append(("Claude Code", claude_ver, _OK, ""))
    else:
        checks.append(("Claude Code", "not found", _WARN, "npm i -g @anthropic-ai/claude-code"))
        has_warn = True

    # --- memctl -----------------------------------------------------------
    memctl_ver = _cmd_version("memctl")
    if memctl_ver:
        method = _detect_install_method("memctl")
        checks.append(("memctl", memctl_ver, _OK, f"({method})"))
    else:
        checks.append(("memctl", "not installed", _FAIL, "toolboxctl install"))
        has_fail = True

    # --- CloakMCP ---------------------------------------------------------
    cloak_ver = _cmd_version("cloak")
    if cloak_ver:
        method = _detect_install_method("cloak")
        checks.append(("CloakMCP", cloak_ver, _OK, f"({method})"))
    else:
        checks.append(("CloakMCP", "not installed", _FAIL, "toolboxctl install"))
        has_fail = True

    # --- toolboxctl -------------------------------------------------------
    method = _detect_install_method("toolboxctl")
    checks.append(("toolboxctl", __version__, _OK, f"({method})"))

    # --- PATH resolution --------------------------------------------------
    path_cmds = ["cloak", "memctl"]
    missing_path = [c for c in path_cmds if not shutil.which(c)]
    if not missing_path:
        checks.append(("PATH", ", ".join(path_cmds), _OK, "all on PATH"))
    else:
        checks.append((
            "PATH",
            ", ".join(missing_path) + " missing",
            _WARN if memctl_ver or cloak_ver else _FAIL,
            "check pipx ensurepath",
        ))
        has_warn = True

    # --- Global hooks -----------------------------------------------------
    hooks_state = check_global_hooks()
    if hooks_state["installed"]:
        events = ", ".join(hooks_state["events"])
        checks.append((
            "Global hooks",
            f"{hooks_state['hook_count']} hooks",
            _OK,
            events,
        ))
    else:
        checks.append((
            "Global hooks",
            "not configured",
            _WARN,
            "toolboxctl install --global",
        ))
        has_warn = True

    # --- Permissions ------------------------------------------------------
    perms_state = check_global_permissions()
    if perms_state["installed"]:
        checks.append((
            "Permissions",
            ", ".join(p.split("(")[1].rstrip(")") for p in perms_state["permissions"]),
            _OK,
            "",
        ))
    else:
        checks.append((
            "Permissions",
            "incomplete",
            _WARN,
            "toolboxctl install",
        ))
        has_warn = True

    # --- CLAUDE.md block --------------------------------------------------
    md_state = check_global_claude_md()
    if md_state["installed"]:
        checks.append(("CLAUDE.md", "~/.claude/", _OK, "toolbox block present"))
    elif md_state["file_exists"]:
        checks.append((
            "CLAUDE.md",
            "~/.claude/",
            _WARN,
            "no toolbox block — toolboxctl install --global",
        ))
        has_warn = True
    else:
        checks.append((
            "CLAUDE.md",
            "not found",
            _WARN,
            "toolboxctl install --global",
        ))
        has_warn = True

    # --- Platform (informational) -----------------------------------------
    checks.append(("Platform", platform.platform(), _OK, ""))

    # --- Print results ----------------------------------------------------
    info("Adservio Toolbox — Doctor\n")

    rows = []
    for name, value, status, note in checks:
        mark = _check_mark(status)
        display = f"{value}  {note}".strip() if note else value
        rows.append((name, display, mark))

    print_table(rows, headers=["Component", "Value", ""])

    # --- Summary ----------------------------------------------------------
    if has_fail:
        print(file=sys.stderr)
        warn("Some critical components are missing. Run 'toolboxctl install' first.")
        sys.exit(2)
    elif has_warn:
        print(file=sys.stderr)
        info("Some optional components are not configured. See suggestions above.")
        sys.exit(1)
    else:
        print(file=sys.stderr)
        info("All checks passed.")
        sys.exit(0)
