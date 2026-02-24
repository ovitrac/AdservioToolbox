"""Auto-updater — upgrade memctl, CloakMCP, and toolbox via pipx/pip.

Detects install method per tool, runs the appropriate upgrade command,
and optionally re-runs project template updates.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from toolbox.doctor import _cmd_version, _detect_install_method
from toolbox.helpers import error, info, run, warn

# ---------------------------------------------------------------------------
# Package registry
# ---------------------------------------------------------------------------

_PACKAGES = [
    {"name": "memctl", "pip_name": "memctl", "cmd": "memctl"},
    {"name": "cloakmcp", "pip_name": "cloakmcp", "cmd": "cloak"},
    {"name": "adservio-toolbox", "pip_name": "adservio-toolbox", "cmd": "toolboxctl"},
]


# ---------------------------------------------------------------------------
# PyPI version check
# ---------------------------------------------------------------------------


def _pypi_latest(pip_name: str) -> str | None:
    """Query PyPI for the latest version of a package.

    Uses ``pip index versions`` (pip 21.2+). Returns None if unavailable.
    """
    result = run(
        [sys.executable, "-m", "pip", "index", "versions", pip_name],
        check=False,
        quiet=True,
    )
    if result.returncode != 0:
        return None
    # Output format: "memctl (0.17.0)\n  Available versions: ..."
    first_line = result.stdout.strip().splitlines()[0] if result.stdout else ""
    if "(" in first_line and ")" in first_line:
        return first_line.split("(")[1].split(")")[0].strip()
    return None


# ---------------------------------------------------------------------------
# Upgrade logic
# ---------------------------------------------------------------------------


def _upgrade_package(pkg: dict, *, quiet: bool = False) -> dict:
    """Upgrade a single package. Returns a result dict."""
    name = pkg["name"]
    cmd = pkg["cmd"]
    pip_name = pkg["pip_name"]

    old_ver = _cmd_version(cmd)
    method = _detect_install_method(cmd)

    result = {
        "package": name,
        "old_version": old_ver,
        "new_version": old_ver,
        "method": method,
        "action": "skip",
        "error": None,
    }

    if method == "not found":
        result["action"] = "not_installed"
        if not quiet:
            warn(f"{name}: not installed, skipping.")
        return result

    if method == "pipx":
        upgrade = run(["pipx", "upgrade", pip_name], check=False, quiet=quiet)
        if upgrade.returncode != 0:
            result["action"] = "error"
            result["error"] = upgrade.stderr.strip() if upgrade.stderr else "upgrade failed"
            if not quiet:
                error(f"{name}: pipx upgrade failed.")
        else:
            result["action"] = "upgraded"
    elif method in ("pip/venv", "system"):
        upgrade = run(
            [sys.executable, "-m", "pip", "install", "--upgrade", pip_name],
            check=False,
            quiet=quiet,
        )
        if upgrade.returncode != 0:
            result["action"] = "error"
            result["error"] = upgrade.stderr.strip() if upgrade.stderr else "upgrade failed"
            if not quiet:
                error(f"{name}: pip upgrade failed.")
        else:
            result["action"] = "upgraded"

    # Re-check version after upgrade
    new_ver = _cmd_version(cmd)
    result["new_version"] = new_ver

    return result


# ---------------------------------------------------------------------------
# Check mode (--check)
# ---------------------------------------------------------------------------


def _check_packages(*, quiet: bool = False, as_json: bool = False) -> list[dict]:
    """Show installed vs latest versions without upgrading."""
    results = []
    for pkg in _PACKAGES:
        installed = _cmd_version(pkg["cmd"])
        method = _detect_install_method(pkg["cmd"])
        latest = _pypi_latest(pkg["pip_name"])

        entry = {
            "package": pkg["name"],
            "installed": installed,
            "latest": latest,
            "method": method,
            "up_to_date": (installed == latest) if (installed and latest) else None,
        }
        results.append(entry)

        if not quiet and not as_json:
            status = ""
            if installed is None:
                status = "not installed"
            elif latest is None:
                status = f"{installed} (PyPI check unavailable)"
            elif installed == latest:
                status = f"{installed} (up to date)"
            else:
                status = f"{installed} -> {latest} (update available)"
            info(f"{pkg['name']}: {status} [{method}]")

    return results


# ---------------------------------------------------------------------------
# Block refresh helpers
# ---------------------------------------------------------------------------


def _refresh_global_block() -> None:
    """Refresh the global CLAUDE.md block.

    Handles legacy (pre-doctrine) markers: removes the old block first,
    then installs the new one.  This is the intended migration path.
    """
    from toolbox.global_wiring import (
        check_legacy_global_markers,
        install_global_claude_md,
        uninstall_global_claude_md,
    )

    info("Refreshing global CLAUDE.md block ...")

    legacy = check_legacy_global_markers()
    if legacy["has_legacy"] and not legacy["has_new"]:
        info("Migrating legacy markers to doctrine format ...")
        uninstall_global_claude_md()  # removes legacy block

    install_global_claude_md()


# ---------------------------------------------------------------------------
# Project template refresh
# ---------------------------------------------------------------------------


def _read_json(path: Path) -> dict:
    """Read a JSON file, returning {} on error."""
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, ValueError):
        return {}


def _refresh_project_templates(cwd: Path) -> None:
    """Re-run project template updates if manifest exists."""
    from toolbox.project_wiring import (
        MANIFEST_FILE,
        TOOLBOX_DIR,
        install_project_claude_md,
        install_project_manifest,
    )

    manifest_path = cwd / TOOLBOX_DIR / MANIFEST_FILE
    if not manifest_path.exists():
        return

    manifest = _read_json(manifest_path)
    profile = manifest.get("profile", "minimal")

    info("Refreshing project templates ...")
    install_project_claude_md(cwd, force=True, profile=profile)
    install_project_manifest(cwd, profile=profile)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def cmd_update(args) -> None:
    """Entry point for ``toolboxctl update``."""
    check_only: bool = getattr(args, "check", False)
    quiet: bool = getattr(args, "quiet", False)
    as_json: bool = getattr(args, "json", False)
    scope_global: bool = getattr(args, "scope_global", False)
    scope_project: bool = getattr(args, "scope_project", False)

    # --- Scoped block refresh (no package upgrade) ------------------------
    if scope_global or scope_project:
        if scope_global:
            _refresh_global_block()
        if scope_project:
            _refresh_project_templates(Path.cwd())
        return

    if check_only:
        results = _check_packages(quiet=quiet, as_json=as_json)
        if as_json:
            print(json.dumps(results, indent=2))
        return

    if not quiet:
        info("Upgrading toolbox components ...")

    results = []
    for pkg in _PACKAGES:
        result = _upgrade_package(pkg, quiet=quiet)
        results.append(result)

    if as_json:
        print(json.dumps(results, indent=2))
        return

    if not quiet:
        # Print summary
        print(file=sys.stderr)
        for r in results:
            if r["action"] == "not_installed":
                continue
            old = r["old_version"] or "?"
            new = r["new_version"] or "?"
            if old == new:
                info(f"{r['package']}: {old} (already latest) [{r['method']}]")
            else:
                info(f"{r['package']}: {old} -> {new} [{r['method']}]")

    # Refresh project templates if in a toolbox-initialized project
    _refresh_project_templates(Path.cwd())
