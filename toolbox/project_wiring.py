"""Project-level Claude Code wiring — CLAUDE.md block, manifest, state, gitignore.

Manages the project-level wiring for toolboxctl init/deinit:
- CLAUDE.md block injection and removal (marker-based)
- .toolbox/manifest.json (tracked, authoritative init marker)
- .toolbox/state.json (untracked, reversible state for deinit)
- .gitignore idempotent updates

All operations are idempotent and reversible.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from toolbox import __version__
from toolbox.helpers import info, warn

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Project-specific markers (distinct from global to avoid collisions)
_PROJECT_BLOCK_BEGIN = "<!-- ADSERVIO_TOOLBOX PROJECT BEGIN — managed by toolboxctl, do not edit manually -->"
_PROJECT_BLOCK_END = "<!-- ADSERVIO_TOOLBOX PROJECT END -->"

_PROJECT_BLOCK_BASE = """\
## Adservio Toolbox — Project Conventions

- CloakMCP safety rules are defined globally (see `~/.claude/CLAUDE.md`).
  Do not paste raw secrets into prompts.
- This repo may enable eco mode; see `.claude/eco/ECO.md` when present.
- Run `toolboxctl doctor` to verify the installation at any time.
"""

_PROJECT_BLOCK_DEV_ADDENDUM = """\
- Build, test, lint, and format instructions are in `.claude/PROJECT.md`.
"""

_PROJECT_BLOCK_PLAYGROUND_ADDENDUM = """\
- This is a playground project. See `CHALLENGE.md` for interactive tests.
"""

# Template for .claude/PROJECT.md (dev profile only)
_PROJECT_MD_TEMPLATE = """\
# Project — Build, Test, Lint, Format

## Build
```bash
# e.g. pip install -e ".[dev]"
```

## Test
```bash
# e.g. pytest -x --tb=short
```

## Lint
```bash
# e.g. ruff check .
```

## Format
```bash
# e.g. black . && isort .
```
"""


def _build_project_block(cwd: Path, *, profile: str = "minimal") -> str:
    """Assemble project CLAUDE.md block content based on profile.

    - Base block always present (references GLOBAL, no CloakMCP restatement).
    - Dev addendum when profile == "dev" (points to .claude/PROJECT.md).
    - Playground addendum when profile == "playground".
    - No memctl MCP instructions in any profile.
    """
    parts = [_PROJECT_BLOCK_BASE]
    if profile == "dev":
        parts.append(_PROJECT_BLOCK_DEV_ADDENDUM)
    elif profile == "playground":
        parts.append(_PROJECT_BLOCK_PLAYGROUND_ADDENDUM)
    return "".join(parts)

TOOLBOX_DIR = ".toolbox"
MANIFEST_FILE = "manifest.json"
STATE_FILE = "state.json"

# Entries to add to .gitignore
_GITIGNORE_ENTRIES = [
    ".claude/settings.local.json",
    ".toolbox/state.json",
]


# ---------------------------------------------------------------------------
# JSON helpers
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


# ---------------------------------------------------------------------------
# State tracking (.toolbox/state.json — untracked)
# ---------------------------------------------------------------------------


def _load_state(cwd: Path) -> dict:
    """Load .toolbox/state.json or return empty state."""
    return _read_json(cwd / TOOLBOX_DIR / STATE_FILE)


def _save_state(cwd: Path, state: dict) -> None:
    """Write .toolbox/state.json."""
    _write_json(cwd / TOOLBOX_DIR / STATE_FILE, state)


def _record_created(state: dict, path: str) -> None:
    """Record a file as created by init."""
    created = state.setdefault("created_files", [])
    if path not in created:
        created.append(path)


def _record_modified(state: dict, path: str, action: str, existed_before: bool) -> None:
    """Record a file as modified by init."""
    modified = state.setdefault("modified_files", {})
    modified[path] = {"action": action, "existed_before": existed_before}


# ---------------------------------------------------------------------------
# Manifest (.toolbox/manifest.json — tracked)
# ---------------------------------------------------------------------------


def install_project_manifest(cwd: Path, *, profile: str = "minimal") -> None:
    """Create or update .toolbox/manifest.json."""
    manifest_path = cwd / TOOLBOX_DIR / MANIFEST_FILE
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    if manifest_path.exists():
        manifest = _read_json(manifest_path)
        manifest["toolbox_version"] = __version__
        manifest["updated_timestamp"] = now
        manifest["profile"] = profile
        info("Updated .toolbox/manifest.json")
    else:
        manifest = {
            "schema_version": 1,
            "toolbox_version": __version__,
            "init_timestamp": now,
            "updated_timestamp": now,
            "features": [
                "claude_md_block",
                "slash_commands",
                "mcp_servers",
                "permissions",
                "config",
            ],
            "profile": profile,
        }
        info("Created .toolbox/manifest.json")

    _write_json(manifest_path, manifest)


# ---------------------------------------------------------------------------
# CLAUDE.md block injection / removal
# ---------------------------------------------------------------------------


def install_project_claude_md(cwd: Path, *, force: bool = False,
                              profile: str = "minimal") -> bool:
    """Write or update the toolbox block in project CLAUDE.md.

    - Creates the file if missing.
    - Appends the block if the file exists but has no project markers.
    - Updates the block in-place if markers already exist.
    - Block content depends on the profile (minimal/dev/playground).

    Returns True if changes were made.
    """
    claude_md = cwd / "CLAUDE.md"
    block_content = _build_project_block(cwd, profile=profile)
    full_block = f"{_PROJECT_BLOCK_BEGIN}\n{block_content}{_PROJECT_BLOCK_END}\n"

    # Track state for deinit
    state = _load_state(cwd)

    if not claude_md.exists():
        claude_md.write_text(full_block, encoding="utf-8")
        _record_created(state, "CLAUDE.md")
        _save_state(cwd, state)
        info("Created CLAUDE.md with toolbox block.")
        return True

    content = claude_md.read_text(encoding="utf-8")

    if _PROJECT_BLOCK_BEGIN in content and _PROJECT_BLOCK_END in content:
        # Replace existing block
        before = content[: content.index(_PROJECT_BLOCK_BEGIN)]
        after = content[content.index(_PROJECT_BLOCK_END) + len(_PROJECT_BLOCK_END) :]
        after = after.lstrip("\n")
        new_content = before + full_block + after
        if new_content == content:
            info("CLAUDE.md toolbox block already up to date.")
            return False
        claude_md.write_text(new_content, encoding="utf-8")
        _record_modified(state, "CLAUDE.md", "replaced_block", True)
        _save_state(cwd, state)
        info("Updated toolbox block in CLAUDE.md.")
        return True

    # Append block
    separator = "\n" if content and not content.endswith("\n") else ""
    separator += "\n" if content else ""
    claude_md.write_text(content + separator + full_block, encoding="utf-8")
    _record_modified(state, "CLAUDE.md", "appended_block", True)
    _save_state(cwd, state)
    info("Appended toolbox block to CLAUDE.md.")
    return True


def uninstall_project_claude_md(cwd: Path) -> bool:
    """Remove the toolbox block from project CLAUDE.md.

    If the file was created by init and is now empty, deletes it.
    Returns True if changes were made.
    """
    claude_md = cwd / "CLAUDE.md"
    if not claude_md.exists():
        return False

    content = claude_md.read_text(encoding="utf-8")

    if _PROJECT_BLOCK_BEGIN not in content:
        return False

    if _PROJECT_BLOCK_END not in content:
        warn("Found BEGIN marker but no END marker in CLAUDE.md — skipping.")
        return False

    before = content[: content.index(_PROJECT_BLOCK_BEGIN)]
    after = content[content.index(_PROJECT_BLOCK_END) + len(_PROJECT_BLOCK_END) :]

    # Clean up extra blank lines around the removed block
    new_content = before.rstrip("\n") + after.lstrip("\n")
    if new_content and not new_content.endswith("\n"):
        new_content += "\n"

    # Check if file was created by init and is now empty
    state = _load_state(cwd)
    created_files = state.get("created_files", [])

    if not new_content.strip():
        if "CLAUDE.md" in created_files:
            claude_md.unlink()
            info("Removed CLAUDE.md (was created by init).")
            return True
        new_content = ""

    claude_md.write_text(new_content, encoding="utf-8")
    info("Removed toolbox block from CLAUDE.md.")
    return True


# ---------------------------------------------------------------------------
# .claude/PROJECT.md (dev profile)
# ---------------------------------------------------------------------------


def install_project_md(cwd: Path, *, force: bool = False) -> bool:
    """Create .claude/PROJECT.md for build/test/lint/format. Dev profile only.

    Returns True if the file was written.
    """
    project_md = cwd / ".claude" / "PROJECT.md"
    if project_md.exists() and not force:
        info("Skipped (exists): .claude/PROJECT.md")
        return False
    project_md.parent.mkdir(parents=True, exist_ok=True)
    project_md.write_text(_PROJECT_MD_TEMPLATE, encoding="utf-8")
    info("Created .claude/PROJECT.md (build/test/lint/format template).")
    return True


# ---------------------------------------------------------------------------
# .gitignore management
# ---------------------------------------------------------------------------


def _ensure_gitignore(cwd: Path) -> bool:
    """Idempotently add toolbox entries to project .gitignore.

    Returns True if changes were made.
    """
    gitignore = cwd / ".gitignore"

    if gitignore.exists():
        content = gitignore.read_text(encoding="utf-8")
    else:
        content = ""

    lines = content.splitlines()
    added = []
    for entry in _GITIGNORE_ENTRIES:
        if entry not in lines:
            added.append(entry)

    if not added:
        return False

    # Append with header
    parts = []
    if content and not content.endswith("\n"):
        parts.append("\n")
    if not any("toolbox" in line.lower() for line in lines):
        parts.append("\n# Adservio Toolbox (untracked)\n")
    for entry in added:
        parts.append(f"{entry}\n")

    gitignore.write_text(content + "".join(parts), encoding="utf-8")
    info(f".gitignore updated: added {', '.join(added)}")
    return True


# ---------------------------------------------------------------------------
# Inspection (used by doctor / status)
# ---------------------------------------------------------------------------


def check_project_wiring(cwd: Path) -> dict:
    """Return project wiring state for the given directory."""
    result = {
        "manifest_present": False,
        "toolbox_version": None,
        "claude_md_block": False,
        "features": [],
        "profile": None,
        "eco_active": False,
        "has_project_md": False,
    }

    manifest_path = cwd / TOOLBOX_DIR / MANIFEST_FILE
    if manifest_path.exists():
        manifest = _read_json(manifest_path)
        result["manifest_present"] = True
        result["toolbox_version"] = manifest.get("toolbox_version")
        result["features"] = manifest.get("features", [])
        result["profile"] = manifest.get("profile")

    claude_md = cwd / "CLAUDE.md"
    if claude_md.exists():
        content = claude_md.read_text(encoding="utf-8")
        result["claude_md_block"] = (
            _PROJECT_BLOCK_BEGIN in content and _PROJECT_BLOCK_END in content
        )

    # Eco mode: active when .claude/eco/ECO.md exists and .disabled is absent
    eco_md = cwd / ".claude" / "eco" / "ECO.md"
    eco_disabled = cwd / ".claude" / "eco" / ".disabled"
    result["eco_active"] = eco_md.exists() and not eco_disabled.exists()

    # .claude/PROJECT.md (dev profile artifact)
    result["has_project_md"] = (cwd / ".claude" / "PROJECT.md").exists()

    return result
