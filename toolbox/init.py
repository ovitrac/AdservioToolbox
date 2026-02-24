"""Wire .claude/commands/, permissions, config, CLAUDE.md block, and manifest.

Idempotent: existing files are skipped unless --force is passed.
Settings merge: MCP servers are injected into existing .claude/settings.json
without touching hooks or other user configuration.
Permissions: cloak/memctl/toolboxctl Bash glob permissions are injected into
.claude/settings.local.json (merges with existing hooks and other keys).
CLAUDE.md: project-scoped toolbox block injected via markers (non-destructive).
Manifest: .toolbox/manifest.json tracks init state for deinit/update.

Reversible via ``toolboxctl deinit``.
"""

from __future__ import annotations

import importlib.resources
import json
import shutil
from pathlib import Path

from toolbox.config import CONFIG_FILENAME, DEFAULTS, write_config
from toolbox.helpers import ask_yes_no, info, warn
from toolbox.project_wiring import (
    _ensure_gitignore,
    install_project_claude_md,
    install_project_manifest,
    install_project_md,
    uninstall_project_claude_md,
)

# ---------------------------------------------------------------------------
# Per-project permissions (colon-glob format for Claude Code matching)
# ---------------------------------------------------------------------------

_PROJECT_PERMISSIONS = [
    "Bash(cloak:*)",
    "Bash(memctl:*)",
    "Bash(toolboxctl:*)",
]

# Old format entries to clean up on re-init
_STALE_PROJECT_PERMISSIONS = [
    "Bash(cloak *)",
    "Bash(memctl *)",
    "Bash(toolboxctl *)",
]

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


def _merge_permissions(target_path: Path) -> None:
    """Inject cloak/memctl/toolboxctl Bash permissions into settings.local.json.

    Merges into existing file (preserves hooks, mcpServers, and other keys).
    Replaces stale space-glob entries with colon-glob format.
    """
    if target_path.exists():
        try:
            with open(target_path, encoding="utf-8") as fh:
                existing = json.load(fh)
        except (json.JSONDecodeError, ValueError):
            warn(f"Could not parse {target_path} — treating as empty.")
            existing = {}
    else:
        existing = {}

    allow = existing.setdefault("permissions", {}).setdefault("allow", [])

    changed = False

    # Remove stale space-glob entries
    for stale in _STALE_PROJECT_PERMISSIONS:
        if stale in allow:
            allow.remove(stale)
            changed = True

    # Add current permissions
    added = []
    for perm in _PROJECT_PERMISSIONS:
        if perm not in allow:
            allow.append(perm)
            added.append(perm)

    if added or changed:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as fh:
            json.dump(existing, fh, indent=2)
            fh.write("\n")
        for perm in added:
            info(f"Project permission added: {perm}")
        if changed and not added:
            info("Project permissions upgraded (format fix).")
    else:
        info("Project permissions already configured.")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def cmd_init(args) -> None:
    """Entry point for ``toolboxctl init``."""
    force: bool = getattr(args, "force", False)
    fts: str = getattr(args, "fts", "fr")
    profile: str = getattr(args, "profile", "minimal")
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

    # --- settings.local.json (merge Bash permissions) ---------------------
    settings_local_dst = cwd / ".claude" / "settings.local.json"
    _merge_permissions(settings_local_dst)

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

    # --- CLAUDE.md (inject toolbox block) ---------------------------------
    install_project_claude_md(cwd, force=force, profile=profile)

    # --- .claude/PROJECT.md (dev profile only) ----------------------------
    if profile == "dev":
        install_project_md(cwd, force=force)

    # --- Manifest + state -------------------------------------------------
    install_project_manifest(cwd, profile=profile)

    # --- .gitignore -------------------------------------------------------
    _ensure_gitignore(cwd)

    info("Init complete. Slash commands, config, and CLAUDE.md are ready.")


# ---------------------------------------------------------------------------
# Deinit (reverse init)
# ---------------------------------------------------------------------------

# Toolbox MCP server keys to remove from settings.json
_TOOLBOX_MCP_SERVERS = {"memctl", "cloakmcp"}

# Toolbox slash command files
_TOOLBOX_COMMANDS = [
    "cheat.md", "eco.md", "how.md", "tldr.md", "why.md",
]


def _teardown(cwd: Path) -> None:
    """Remove toolbox wiring from the project. Preserves .memory/, hooks, user content."""
    removed = []

    # 1. Remove slash command files
    commands_dir = cwd / ".claude" / "commands"
    for cmd_file in _TOOLBOX_COMMANDS:
        target = commands_dir / cmd_file
        if target.exists():
            target.unlink()
            removed.append(f".claude/commands/{cmd_file}")
    # Remove empty commands dir
    if commands_dir.exists() and not any(commands_dir.iterdir()):
        commands_dir.rmdir()
        info("Removed empty .claude/commands/")

    # 2. Remove toolbox MCP servers from settings.json
    settings_json = cwd / ".claude" / "settings.json"
    if settings_json.exists():
        try:
            with open(settings_json, encoding="utf-8") as fh:
                settings = json.load(fh)
        except (json.JSONDecodeError, ValueError):
            settings = {}

        mcp = settings.get("mcpServers", {})
        for key in _TOOLBOX_MCP_SERVERS:
            if key in mcp:
                del mcp[key]
                removed.append(f".claude/settings.json (mcpServers.{key})")

        # If only mcpServers remains and it's empty, clean up
        if not mcp and "mcpServers" in settings:
            del settings["mcpServers"]

        if settings:
            with open(settings_json, "w", encoding="utf-8") as fh:
                json.dump(settings, fh, indent=2)
                fh.write("\n")
        else:
            settings_json.unlink()
            removed.append(".claude/settings.json (empty, deleted)")

    # 3. Remove toolbox permissions from settings.local.json
    settings_local = cwd / ".claude" / "settings.local.json"
    if settings_local.exists():
        try:
            with open(settings_local, encoding="utf-8") as fh:
                local = json.load(fh)
        except (json.JSONDecodeError, ValueError):
            local = {}

        allow = local.get("permissions", {}).get("allow", [])
        toolbox_perms = set(_PROJECT_PERMISSIONS) | set(_STALE_PROJECT_PERMISSIONS)
        filtered = [p for p in allow if p not in toolbox_perms]
        if len(filtered) != len(allow):
            local["permissions"]["allow"] = filtered
            removed.append(".claude/settings.local.json (toolbox permissions)")

            # Clean up empty permissions
            if not filtered:
                del local["permissions"]["allow"]
            if not local.get("permissions"):
                del local["permissions"]

            if local:
                with open(settings_local, "w", encoding="utf-8") as fh:
                    json.dump(local, fh, indent=2)
                    fh.write("\n")
            else:
                settings_local.unlink()
                removed.append(".claude/settings.local.json (empty, deleted)")

    # 4. Remove .claude/PROJECT.md (dev profile artifact)
    project_md = cwd / ".claude" / "PROJECT.md"
    if project_md.exists():
        project_md.unlink()
        removed.append(".claude/PROJECT.md")

    # 5. Remove config file
    config_file = cwd / CONFIG_FILENAME
    if config_file.exists():
        config_file.unlink()
        removed.append(CONFIG_FILENAME)

    # 6. Remove toolbox block from CLAUDE.md
    if uninstall_project_claude_md(cwd):
        removed.append("CLAUDE.md (toolbox block)")

    # 7. Remove manifest and state
    toolbox_dir = cwd / ".toolbox"
    manifest = toolbox_dir / "manifest.json"
    state = toolbox_dir / "state.json"
    if manifest.exists():
        manifest.unlink()
        removed.append(".toolbox/manifest.json")
    if state.exists():
        state.unlink()
        removed.append(".toolbox/state.json")
    if toolbox_dir.exists() and not any(toolbox_dir.iterdir()):
        toolbox_dir.rmdir()
        removed.append(".toolbox/ (empty, deleted)")

    # Summary
    if removed:
        info(f"Removed {len(removed)} item(s):")
        for item in removed:
            info(f"  - {item}")
    else:
        info("Nothing to remove.")

    info("Preserved: .memory/, .claude/hooks/, .claude/eco/, user CLAUDE.md content.")


def cmd_deinit(args) -> None:
    """Entry point for ``toolboxctl deinit``."""
    force: bool = getattr(args, "force", False)
    cwd = Path.cwd()

    if not force:
        if not ask_yes_no("Remove toolbox wiring from this project?"):
            info("Aborted.")
            return

    _teardown(cwd)
    info("Deinit complete.")
