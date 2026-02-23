"""Eco mode toggle — read/write the eco.enabled_global flag in config."""

from __future__ import annotations

from pathlib import Path

from toolbox.config import CONFIG_FILENAME, find_config, load_config, write_config
from toolbox.helpers import die, info, warn

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def cmd_eco(args) -> None:
    """Entry point for ``toolboxctl eco [on|off]``."""
    action: str | None = getattr(args, "action", None)
    config_path = find_config()
    cfg = load_config(config_path)

    current = cfg.get("eco", {}).get("enabled_global", False)

    # Show current state
    if action is None:
        state = "on" if current else "off"
        info(f"Eco mode is currently: {state}")
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
    info(f"Eco mode set to {'on' if new_state else 'off'} in {config_path}")
