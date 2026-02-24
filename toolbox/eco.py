"""Eco mode toggle — syncs config file AND memctl sentinel.

State sources (both kept in sync):
  1. ``.adservio-toolbox.toml``  → ``eco.enabled_global`` flag
  2. ``.claude/eco/.disabled``   → memctl sentinel (absent = on, present = off)

Reading: sentinel wins when ``.claude/eco/`` directory exists, config is fallback.
Writing: both are updated so ``toolboxctl eco`` and ``memctl eco`` always agree.
"""

from __future__ import annotations

from pathlib import Path

from toolbox.config import CONFIG_FILENAME, find_config, load_config, write_config
from toolbox.helpers import die, info, warn

# ---------------------------------------------------------------------------
# Sentinel helpers (memctl convention)
# ---------------------------------------------------------------------------

_ECO_DIR = ".claude/eco"
_DISABLED_SENTINEL = ".claude/eco/.disabled"


def _eco_dir(cwd: Path | None = None) -> Path:
    return (cwd or Path.cwd()) / _ECO_DIR


def _sentinel(cwd: Path | None = None) -> Path:
    return (cwd or Path.cwd()) / _DISABLED_SENTINEL


def _read_sentinel(cwd: Path | None = None) -> bool | None:
    """Read eco state from memctl sentinel.

    Returns True (on), False (off), or None (eco not installed).
    """
    eco_dir = _eco_dir(cwd)
    if not eco_dir.is_dir():
        return None
    return not _sentinel(cwd).exists()


def _write_sentinel(enabled: bool, cwd: Path | None = None) -> None:
    """Sync the memctl sentinel file to match *enabled*."""
    eco_dir = _eco_dir(cwd)
    if not eco_dir.is_dir():
        return  # eco not installed — nothing to sync
    sentinel = _sentinel(cwd)
    if enabled:
        sentinel.unlink(missing_ok=True)
    else:
        sentinel.touch()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def cmd_eco(args) -> None:
    """Entry point for ``toolboxctl eco [on|off]``."""
    action: str | None = getattr(args, "action", None)
    config_path = find_config()
    cfg = load_config(config_path)

    # Read state: sentinel wins when eco dir exists, config is fallback
    sentinel_state = _read_sentinel()
    if sentinel_state is not None:
        current = sentinel_state
    else:
        current = cfg.get("eco", {}).get("enabled_global", False)

    # Show current state
    if action is None:
        state = "on" if current else "off"
        info(f"Eco mode is currently: {state}")
        if sentinel_state is not None:
            info(f"Source: {_eco_dir()} (memctl sentinel)")
        if config_path:
            info(f"Config: {config_path}")
        else:
            warn("No config file found. Run 'toolboxctl init' first.")
        return

    # Toggle
    new_state = action == "on"
    if new_state == current:
        info(f"Eco mode is already {'on' if new_state else 'off'}.")
        return

    # Write to config
    if config_path is None:
        die(f"No {CONFIG_FILENAME} found. Run 'toolboxctl init' first.", code=1)

    cfg.setdefault("eco", {})["enabled_global"] = new_state
    write_config(cfg, config_path)

    # Sync sentinel so memctl sees the same state
    _write_sentinel(new_state)

    info(f"Eco mode set to {'on' if new_state else 'off'} in {config_path}")
