"""Platform detection helpers for hook wiring.

On Windows (without Git Bash), .sh hooks cannot execute.  CloakMCP and memctl
ship Python entrypoints (.py) alongside their Bash hooks.  This module selects
the correct variant based on ``sys.platform``.

Resolution order on Windows:
  1. ``.py`` entrypoint  → ``python <path>.py``
  2. ``.cmd`` wrapper    → ``<path>.cmd``
  3. ``.sh`` fallback    → original path (Git Bash may be present)

On POSIX the ``.sh`` path is returned unchanged.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

IS_WINDOWS = sys.platform == "win32"


def _python_cmd() -> str:
    """Return the Python interpreter command appropriate for the platform."""
    if IS_WINDOWS:
        # Prefer py launcher, fall back to python
        if shutil.which("py"):
            return "py -3"
        return "python"
    return "python3"


def resolve_hook_command(sh_path: str) -> str:
    """Return the OS-appropriate hook command for a given ``.sh`` hook path.

    On Windows: prefers ``.py`` entrypoint, then ``.cmd``, then ``.sh``
    (Git Bash fallback).  On POSIX: returns the ``.sh`` path unchanged.
    """
    if not IS_WINDOWS:
        return sh_path

    base = sh_path.removesuffix(".sh") if sh_path.endswith(".sh") else sh_path

    py_path = base + ".py"
    if Path(py_path).exists():
        return f"{_python_cmd()} {py_path}"

    cmd_path = base + ".cmd"
    if Path(cmd_path).exists():
        return cmd_path

    # Fallback: Git Bash may be installed
    return sh_path
