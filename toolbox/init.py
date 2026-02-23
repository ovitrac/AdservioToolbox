"""Wire .claude/commands/ and create the default config in the current repo.

Idempotent: existing files are skipped unless --force is passed.
Settings merge: MCP servers are injected into existing .claude/settings.json
without touching permissions, hooks, or other user configuration.
"""

from __future__ import annotations

import importlib.resources
import json
import shutil
from pathlib import Path

from toolbox.config import CONFIG_FILENAME, DEFAULTS, write_config
from toolbox.helpers import info, warn

# ---------------------------------------------------------------------------
# Template resolution
# ---------------------------------------------------------------------------


def _templates_root() -> Path:
    """Return the filesystem path to the shipped templates/ directory."""
    ref = importlib.resources.files("toolbox") / "templates"
    # importlib.resources may return a Traversable; resolve to real path
    return Path(str(ref))


# ---------------------------------------------------------------------------
# File copy helper
# ---------------------------------------------------------------------------


def _copy_file(src: Path, dst: Path, *, force: bool = False) -> bool:
    """Copy *src* to *dst*.  Return True if the file was written."""
    if dst.exists() and not force:
        warn(f"Skipped (exists): {dst}")
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    info(f"Wrote {dst}")
    return True


def _merge_settings(template_path: Path, target_path: Path, *, force: bool = False) -> None:
    """Merge toolbox MCP servers into existing settings.json.

    Only injects ``mcpServers.memctl`` and ``mcpServers.cloakmcp``.
    Never touches permissions, hooks, or other user configuration.
    Existing MCP server entries are overwritten only with --force.
    """
    with open(template_path, encoding="utf-8") as fh:
        template = json.load(fh)

    toolbox_servers = template.get("mcpServers", {})

    if target_path.exists():
        with open(target_path, encoding="utf-8") as fh:
            existing = json.load(fh)
    else:
        existing = {}

    if "mcpServers" not in existing:
        existing["mcpServers"] = {}

    changed = False
    for name, config in toolbox_servers.items():
        if name in existing["mcpServers"] and not force:
            info(f"MCP server '{name}' already registered, skipping.")
        else:
            existing["mcpServers"][name] = config
            changed = True
            info(f"Registered MCP server: {name}")

    if changed:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as fh:
            json.dump(existing, fh, indent=2)
            fh.write("\n")
        info(f"Wrote {target_path}")
    else:
        info(f"No changes to {target_path}")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def cmd_init(args) -> None:
    """Entry point for ``toolboxctl init``."""
    force: bool = getattr(args, "force", False)
    fts: str = getattr(args, "fts", "fr")
    cwd = Path.cwd()
    templates = _templates_root()

    # --- Slash commands ----------------------------------------------------
    commands_src = templates / "commands"
    commands_dst = cwd / ".claude" / "commands"
    if commands_src.is_dir():
        for src_file in sorted(commands_src.iterdir()):
            if src_file.is_file():
                _copy_file(src_file, commands_dst / src_file.name, force=force)

    # --- settings.json (merge MCP servers into existing) -------------------
    settings_src = templates / "settings.json"
    settings_dst = cwd / ".claude" / "settings.json"
    if settings_src.is_file():
        _merge_settings(settings_src, settings_dst, force=force)

    # --- Config file ------------------------------------------------------
    config_dst = cwd / CONFIG_FILENAME
    if config_dst.exists() and not force:
        warn(f"Skipped (exists): {config_dst}")
    else:
        # Build config from defaults, override FTS if requested
        cfg = {section: dict(values) for section, values in DEFAULTS.items()}
        if fts:
            cfg["memctl"]["fts"] = fts
        write_config(cfg, config_dst)
        info(f"Wrote {config_dst}")

    info("Init complete. Slash commands and config are ready.")
