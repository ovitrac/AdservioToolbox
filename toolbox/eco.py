"""Eco mode toggle — syncs config, sentinel, CLAUDE.md block, and eco-nudge hook.

State sources (all kept in sync):
  1. ``.adservio-toolbox.toml``  → ``eco.enabled_global`` flag
  2. ``.claude/eco/.disabled``   → memctl sentinel (absent = on, present = off)

Side effects on toggle:
  - F-T1: inject/remove eco behavioral block in project CLAUDE.md
  - F-T2: register/unregister eco-nudge PreToolUse hook in ~/.claude/settings.json

Reading: sentinel wins when ``.claude/eco/`` directory exists, config is fallback.
Writing: all four surfaces updated so toolboxctl/memctl/Claude always agree.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from toolbox._platform import resolve_hook_command
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
# F-T1: CLAUDE.md eco block injection / removal
# ---------------------------------------------------------------------------

_ECO_BLOCK_BEGIN = "<!-- ADSERVIO_TOOLBOX ECO BEGIN -->"
_ECO_BLOCK_END = "<!-- ADSERVIO_TOOLBOX ECO END -->"

_ECO_BLOCK_CONTENT = """\
- Eco mode active. For exploration: memory_inspect (structure), then /recall or memory_recall (FTS5 search, use identifiers).
- Native Grep/Glob after recall misses. Native Read/Edit for modifications.
- Binary files (.docx/.pdf/.pptx) indexed — use memory_recall.
- Structure answers as: Retrieved (cite sources) then Analysis.
"""


def _inject_eco_claude_md(cwd: Path | None = None) -> bool:
    """Inject eco behavioral block into project CLAUDE.md.

    Returns True if changes were made.
    """
    root = cwd or Path.cwd()
    claude_md = root / "CLAUDE.md"
    full_block = f"{_ECO_BLOCK_BEGIN}\n{_ECO_BLOCK_CONTENT}{_ECO_BLOCK_END}\n"

    if not claude_md.exists():
        # No CLAUDE.md — skip (toolboxctl init creates it)
        warn("No CLAUDE.md found — eco block not injected. Run 'toolboxctl init' first.")
        return False

    content = claude_md.read_text(encoding="utf-8")

    if _ECO_BLOCK_BEGIN in content and _ECO_BLOCK_END in content:
        # Already present — replace in case content changed
        before = content[: content.index(_ECO_BLOCK_BEGIN)]
        after = content[content.index(_ECO_BLOCK_END) + len(_ECO_BLOCK_END):]
        after = after.lstrip("\n")
        new_content = before + full_block + after
        if new_content == content:
            return False
        claude_md.write_text(new_content, encoding="utf-8")
        info("Updated eco block in CLAUDE.md.")
        return True

    # Append
    separator = "\n" if content and not content.endswith("\n") else ""
    separator += "\n" if content else ""
    claude_md.write_text(content + separator + full_block, encoding="utf-8")
    info("Injected eco block into CLAUDE.md.")
    return True


def _remove_eco_claude_md(cwd: Path | None = None) -> bool:
    """Remove eco behavioral block from project CLAUDE.md.

    Returns True if changes were made.
    """
    root = cwd or Path.cwd()
    claude_md = root / "CLAUDE.md"

    if not claude_md.exists():
        return False

    content = claude_md.read_text(encoding="utf-8")

    if _ECO_BLOCK_BEGIN not in content:
        return False

    if _ECO_BLOCK_END not in content:
        warn("Found ECO BEGIN marker but no END marker in CLAUDE.md — skipping.")
        return False

    before = content[: content.index(_ECO_BLOCK_BEGIN)]
    after = content[content.index(_ECO_BLOCK_END) + len(_ECO_BLOCK_END):]

    # Clean up trailing blank lines
    new_content = before.rstrip("\n") + "\n" + after.lstrip("\n")
    if not new_content.strip():
        new_content = ""

    claude_md.write_text(new_content, encoding="utf-8")
    info("Removed eco block from CLAUDE.md.")
    return True


# ---------------------------------------------------------------------------
# F-T2: eco-nudge PreToolUse hook wiring (global)
# ---------------------------------------------------------------------------

_HOOK_SOURCE_TAG = "adservio-toolbox-eco"
_GLOBAL_SETTINGS = Path.home() / ".claude" / "settings.json"


def _find_eco_nudge_script() -> str | None:
    """Locate eco-nudge hook from the memctl package (pipx or system install).

    On Windows, prefers the .py entrypoint if available; on POSIX returns the
    .sh script.  Uses :func:`resolve_hook_command` for OS-aware selection.
    """
    memctl_bin = shutil.which("memctl")
    if not memctl_bin:
        return None

    import subprocess
    result = subprocess.run(
        [memctl_bin, "scripts-path"],
        capture_output=True, text=True, timeout=10,
    )
    if result.returncode != 0:
        return None

    scripts_dir = Path(result.stdout.strip())
    nudge_sh = scripts_dir.parent / "templates" / "hooks" / "eco-nudge.sh"
    if nudge_sh.exists():
        return resolve_hook_command(str(nudge_sh.resolve()))
    return None


def _install_eco_nudge_hook() -> bool:
    """Register eco-nudge.sh as a global PreToolUse hook.

    Returns True if changes were made.
    """
    nudge_path = _find_eco_nudge_script()
    if not nudge_path:
        warn("eco-nudge.sh not found in memctl. Upgrade memctl: pipx upgrade memctl")
        return False

    if not _GLOBAL_SETTINGS.exists():
        warn(f"{_GLOBAL_SETTINGS} not found — cannot register eco-nudge hook.")
        return False

    try:
        with open(_GLOBAL_SETTINGS, encoding="utf-8") as fh:
            settings = json.load(fh)
    except (json.JSONDecodeError, ValueError):
        warn(f"Could not parse {_GLOBAL_SETTINGS} — skipping eco-nudge hook.")
        return False

    hooks = settings.setdefault("hooks", {})
    pre_tool = hooks.setdefault("PreToolUse", [])

    # Check if already registered (by source tag)
    for entry in pre_tool:
        if isinstance(entry, dict) and entry.get("_source") == _HOOK_SOURCE_TAG:
            # Update path in case memctl was reinstalled
            hook_list = entry.get("hooks", [])
            if hook_list and hook_list[0].get("command") == nudge_path:
                return False
            # Path changed — update
            entry["hooks"] = [{"type": "command", "command": nudge_path, "timeout": 10000}]
            with open(_GLOBAL_SETTINGS, "w", encoding="utf-8") as fh:
                json.dump(settings, fh, indent=2, ensure_ascii=False)
                fh.write("\n")
            info("Updated eco-nudge hook path in global settings.")
            return True

    # Not yet registered — append
    entry = {
        "hooks": [{"type": "command", "command": nudge_path, "timeout": 10000}],
        "_source": _HOOK_SOURCE_TAG,
        "matcher": "Grep|Glob",
    }
    pre_tool.append(entry)

    with open(_GLOBAL_SETTINGS, "w", encoding="utf-8") as fh:
        json.dump(settings, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    info(f"Registered eco-nudge hook (PreToolUse Grep|Glob) in {_GLOBAL_SETTINGS}")
    return True


def _uninstall_eco_nudge_hook() -> bool:
    """Remove eco-nudge hook from global settings.

    Returns True if changes were made.
    """
    if not _GLOBAL_SETTINGS.exists():
        return False

    try:
        with open(_GLOBAL_SETTINGS, encoding="utf-8") as fh:
            settings = json.load(fh)
    except (json.JSONDecodeError, ValueError):
        return False

    hooks = settings.get("hooks", {})
    pre_tool = hooks.get("PreToolUse", [])
    if not pre_tool:
        return False

    filtered = [e for e in pre_tool if not (
        isinstance(e, dict) and e.get("_source") == _HOOK_SOURCE_TAG
    )]

    if len(filtered) == len(pre_tool):
        return False

    hooks["PreToolUse"] = filtered
    if not filtered:
        del hooks["PreToolUse"]

    with open(_GLOBAL_SETTINGS, "w", encoding="utf-8") as fh:
        json.dump(settings, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    info("Removed eco-nudge hook from global settings.")
    return True


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

    # F-T1: inject/remove eco block in CLAUDE.md
    if new_state:
        _inject_eco_claude_md()
    else:
        _remove_eco_claude_md()

    # F-T2: register/unregister eco-nudge PreToolUse hook (global)
    if new_state:
        _install_eco_nudge_hook()
    else:
        _uninstall_eco_nudge_hook()

    info(f"Eco mode set to {'on' if new_state else 'off'} in {config_path}")
