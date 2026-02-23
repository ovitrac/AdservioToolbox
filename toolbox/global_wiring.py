"""Global Claude Code wiring — hooks, permissions, and CLAUDE.md management.

Manages the user-level ~/.claude/ directory:
- Global CloakMCP hooks in settings.json (secrets-only profile)
- Tool permissions in settings.local.json (Bash, Read, Grep)
- Behavioral rules in CLAUDE.md (delimited block)

All operations are idempotent and reversible.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from toolbox.helpers import error, info, run, warn

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CLAUDE_DIR = Path.home() / ".claude"
SETTINGS_JSON = CLAUDE_DIR / "settings.json"
SETTINGS_LOCAL_JSON = CLAUDE_DIR / "settings.local.json"
CLAUDE_MD = CLAUDE_DIR / "CLAUDE.md"

GLOBAL_PERMISSIONS = [
    "Bash(cloak *)",
    "Bash(memctl *)",
    "Bash(toolboxctl *)",
    "Read",
    "Grep",
]

# Marker used to identify toolbox-managed hook entries
HOOK_SOURCE_TAG = "adservio-toolbox"

# Delimiters for the managed block in ~/.claude/CLAUDE.md
_BLOCK_BEGIN = "<!-- ADSERVIO_TOOLBOX BEGIN — managed by toolboxctl, do not edit manually -->"
_BLOCK_END = "<!-- ADSERVIO_TOOLBOX END -->"

_CLAUDE_MD_BLOCK = """\
## Adservio Toolbox Conventions

- **CloakMCP** is active globally. Secrets are redacted to `TAG-xxxx` placeholders
  at session start and restored at session end.
  Do not attempt to bypass, decode, or reconstruct original secret values.
- When `TAG-xxxx` placeholders appear in files, they are CloakMCP redaction tags.
  Treat them as opaque identifiers. Do not modify or remove them.
- `cloak`, `memctl`, and `toolboxctl` CLI commands are pre-authorized (no confirmation needed).
- For projects with eco mode enabled, use the memctl MCP server tools
  (`memory_recall`, `memory_inspect`) instead of sequential file reads.
  These are MCP tools — do NOT run them as CLI commands.
  CLI equivalent: `memctl search "<query>"` or `memctl show <id>`.
  See `.claude/eco/ECO.md` for the strategy.
- Run `toolboxctl doctor` to verify the toolbox installation at any time.
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_json(path: Path) -> dict:
    """Read a JSON file, returning {} if it doesn't exist or is empty."""
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, ValueError):
        warn(f"Could not parse {path} — treating as empty.")
        return {}


def _write_json(path: Path, data: dict) -> None:
    """Write a JSON file with consistent formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")


def _cloak_scripts_path() -> Path | None:
    """Return the CloakMCP scripts directory, or None if unavailable."""
    cloak = shutil.which("cloak")
    if not cloak:
        return None
    result = run(["cloak", "scripts-path"], check=False, quiet=True)
    if result.returncode != 0:
        return None
    scripts = Path(result.stdout.strip())
    if scripts.is_dir():
        return scripts
    return None


# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------


def install_global_permissions() -> bool:
    """Inject cloak/memctl/toolboxctl Bash permissions into settings.local.json.

    Returns True if changes were made.
    """
    settings = _read_json(SETTINGS_LOCAL_JSON)
    allow = settings.setdefault("permissions", {}).setdefault("allow", [])

    added = []
    for perm in GLOBAL_PERMISSIONS:
        if perm not in allow:
            allow.append(perm)
            added.append(perm)

    if added:
        _write_json(SETTINGS_LOCAL_JSON, settings)
        for perm in added:
            info(f"Global permission added: {perm}")
        return True

    info("Global permissions already configured.")
    return False


def uninstall_global_permissions() -> bool:
    """Remove toolbox-managed permissions from ~/.claude/settings.local.json.

    Returns True if changes were made.
    """
    if not SETTINGS_LOCAL_JSON.exists():
        return False

    settings = _read_json(SETTINGS_LOCAL_JSON)
    allow = settings.get("permissions", {}).get("allow", [])
    if not allow:
        return False

    original_len = len(allow)
    filtered = [p for p in allow if p not in GLOBAL_PERMISSIONS]

    if len(filtered) == original_len:
        return False

    settings["permissions"]["allow"] = filtered
    _write_json(SETTINGS_LOCAL_JSON, settings)
    for perm in GLOBAL_PERMISSIONS:
        if perm not in filtered:
            info(f"Global permission removed: {perm}")
    return True


# ---------------------------------------------------------------------------
# Global CloakMCP hooks
# ---------------------------------------------------------------------------


def _build_hook_entry(command: str, timeout: int | None = None,
                      matcher: str | None = None) -> dict:
    """Build a single hook group entry with the toolbox source marker."""
    hook = {"type": "command", "command": command}
    if timeout:
        hook["timeout"] = timeout
    group: dict = {"hooks": [hook], "_source": HOOK_SOURCE_TAG}
    if matcher:
        group["matcher"] = matcher
    return group


def install_global_hooks() -> bool:
    """Install CloakMCP secrets-only hooks into ~/.claude/settings.json.

    Uses absolute paths to hook scripts from the CloakMCP package.
    Merges into existing hooks (does not replace).
    Returns True if changes were made.
    """
    scripts = _cloak_scripts_path()
    if scripts is None:
        error("CloakMCP not found — cannot install global hooks.")
        error("Install CloakMCP first: pipx install cloakmcp")
        return False

    hooks_dir = scripts / "hooks"
    if not hooks_dir.is_dir():
        # Fallback: scripts may be flat (older CloakMCP)
        hooks_dir = scripts

    # Resolve absolute paths to hook scripts
    def _hook(name: str) -> str:
        for candidate in [hooks_dir / name, scripts / name]:
            if candidate.exists():
                return str(candidate)
        # Not found — use relative (will work if cloak is on PATH)
        return f".claude/hooks/{name}"

    # secrets-only profile: 5 hooks
    toolbox_hooks = {
        "SessionStart": [
            _build_hook_entry(_hook("cloak-session-start.sh"), timeout=60000,
                              matcher="startup"),
        ],
        "SessionEnd": [
            _build_hook_entry(_hook("cloak-session-end.sh"), timeout=60000),
        ],
        "UserPromptSubmit": [
            _build_hook_entry(_hook("cloak-prompt-guard.sh"), timeout=10000),
        ],
        "PreToolUse": [
            _build_hook_entry(_hook("cloak-guard-write.sh"), timeout=10000,
                              matcher="Write|Edit"),
        ],
        "PostToolUse": [
            _build_hook_entry(_hook("cloak-audit-logger.sh"), timeout=5000,
                              matcher="Write|Edit|Bash"),
        ],
    }

    settings = _read_json(SETTINGS_JSON)
    existing_hooks = settings.setdefault("hooks", {})

    changed = False
    for event, entries in toolbox_hooks.items():
        event_list = existing_hooks.setdefault(event, [])

        # Check if our hooks are already present (by _source tag)
        existing_sources = {
            e.get("_source") for e in event_list if isinstance(e, dict)
        }
        if HOOK_SOURCE_TAG in existing_sources:
            continue

        event_list.extend(entries)
        changed = True

    if changed:
        _write_json(SETTINGS_JSON, settings)
        info("Global CloakMCP hooks installed (secrets-only profile).")
        return True

    info("Global CloakMCP hooks already configured.")
    return False


def uninstall_global_hooks() -> bool:
    """Remove toolbox-managed hooks from ~/.claude/settings.json.

    Removes only entries with ``"_source": "adservio-toolbox"``.
    Returns True if changes were made.
    """
    if not SETTINGS_JSON.exists():
        return False

    settings = _read_json(SETTINGS_JSON)
    hooks = settings.get("hooks")
    if not hooks:
        return False

    changed = False
    for event in list(hooks.keys()):
        event_list = hooks[event]
        filtered = [
            e for e in event_list
            if not (isinstance(e, dict) and e.get("_source") == HOOK_SOURCE_TAG)
        ]
        if len(filtered) != len(event_list):
            changed = True
            if filtered:
                hooks[event] = filtered
            else:
                del hooks[event]

    if not hooks:
        del settings["hooks"]

    if changed:
        _write_json(SETTINGS_JSON, settings)
        info("Global CloakMCP hooks removed.")
        return True

    return False


# ---------------------------------------------------------------------------
# ~/.claude/CLAUDE.md block
# ---------------------------------------------------------------------------


def install_global_claude_md() -> bool:
    """Write or update the toolbox block in ~/.claude/CLAUDE.md.

    - Creates the file if missing.
    - Appends the block if the file exists but has no markers.
    - Updates the block in-place if markers already exist.

    Returns True if changes were made.
    """
    full_block = f"{_BLOCK_BEGIN}\n{_CLAUDE_MD_BLOCK}{_BLOCK_END}\n"

    if not CLAUDE_MD.exists():
        CLAUDE_MD.parent.mkdir(parents=True, exist_ok=True)
        CLAUDE_MD.write_text(full_block, encoding="utf-8")
        info(f"Created {CLAUDE_MD} with toolbox conventions.")
        return True

    content = CLAUDE_MD.read_text(encoding="utf-8")

    if _BLOCK_BEGIN in content and _BLOCK_END in content:
        # Replace existing block
        before = content[: content.index(_BLOCK_BEGIN)]
        after = content[content.index(_BLOCK_END) + len(_BLOCK_END) :]
        # Strip trailing newline from after to avoid double newlines
        after = after.lstrip("\n")
        new_content = before + full_block + after
        if new_content == content:
            info("CLAUDE.md toolbox block already up to date.")
            return False
        CLAUDE_MD.write_text(new_content, encoding="utf-8")
        info("Updated toolbox block in CLAUDE.md.")
        return True

    # Append block
    separator = "\n" if content and not content.endswith("\n") else ""
    separator += "\n" if content else ""
    CLAUDE_MD.write_text(content + separator + full_block, encoding="utf-8")
    info(f"Appended toolbox block to {CLAUDE_MD}.")
    return True


def uninstall_global_claude_md() -> bool:
    """Remove the toolbox block from ~/.claude/CLAUDE.md.

    Returns True if changes were made.
    """
    if not CLAUDE_MD.exists():
        return False

    content = CLAUDE_MD.read_text(encoding="utf-8")

    if _BLOCK_BEGIN not in content:
        return False

    if _BLOCK_END not in content:
        warn(f"Found BEGIN marker but no END marker in {CLAUDE_MD} — skipping.")
        return False

    before = content[: content.index(_BLOCK_BEGIN)]
    after = content[content.index(_BLOCK_END) + len(_BLOCK_END) :]

    # Clean up extra blank lines around the removed block
    new_content = before.rstrip("\n") + after.lstrip("\n")
    if new_content and not new_content.endswith("\n"):
        new_content += "\n"
    if not new_content.strip():
        # File would be empty — remove it only if we created it
        # (safer to leave an empty file than delete user's CLAUDE.md)
        new_content = ""

    CLAUDE_MD.write_text(new_content, encoding="utf-8")
    info("Removed toolbox block from CLAUDE.md.")
    return True


# ---------------------------------------------------------------------------
# Composite operations
# ---------------------------------------------------------------------------


def install_global(args=None) -> None:
    """Full global wiring: permissions + hooks + CLAUDE.md."""
    info("Installing global Claude Code wiring …")
    install_global_permissions()
    install_global_hooks()
    install_global_claude_md()
    info("Global install complete. Run 'toolboxctl doctor' to verify.")


def uninstall_global(args=None) -> None:
    """Reverse all global wiring."""
    info("Removing global Claude Code wiring …")
    removed = False
    removed |= uninstall_global_hooks()
    removed |= uninstall_global_permissions()
    removed |= uninstall_global_claude_md()
    if removed:
        info("Global uninstall complete.")
    else:
        info("Nothing to remove — global wiring was not installed.")


# ---------------------------------------------------------------------------
# Inspection helpers (used by doctor)
# ---------------------------------------------------------------------------


def check_global_hooks() -> dict:
    """Return a dict describing the state of global hooks."""
    result = {"installed": False, "hook_count": 0, "events": []}
    if not SETTINGS_JSON.exists():
        return result

    settings = _read_json(SETTINGS_JSON)
    hooks = settings.get("hooks", {})

    count = 0
    events = []
    for event, entries in hooks.items():
        for e in entries:
            if isinstance(e, dict) and e.get("_source") == HOOK_SOURCE_TAG:
                count += 1
                events.append(event)

    result["installed"] = count > 0
    result["hook_count"] = count
    result["events"] = sorted(set(events))
    return result


def check_global_permissions() -> dict:
    """Return a dict describing the state of global permissions."""
    result = {"installed": False, "permissions": []}
    if not SETTINGS_LOCAL_JSON.exists():
        return result

    settings = _read_json(SETTINGS_LOCAL_JSON)
    allow = settings.get("permissions", {}).get("allow", [])

    found = [p for p in GLOBAL_PERMISSIONS if p in allow]
    result["installed"] = len(found) == len(GLOBAL_PERMISSIONS)
    result["permissions"] = found
    return result


def check_global_claude_md() -> dict:
    """Return a dict describing the state of the CLAUDE.md block."""
    result = {"installed": False, "file_exists": False}
    if not CLAUDE_MD.exists():
        return result

    result["file_exists"] = True
    content = CLAUDE_MD.read_text(encoding="utf-8")
    result["installed"] = _BLOCK_BEGIN in content and _BLOCK_END in content
    return result
