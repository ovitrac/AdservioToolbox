"""Export config as shell environment variables or JSON.

Usage:
    eval "$(toolboxctl env)"        # inject into current shell
    toolboxctl env --json           # machine-readable output
"""

from __future__ import annotations

import json
import shlex
import sys

from toolbox.config import config_to_env, load_config
from toolbox.helpers import info

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def cmd_env(args) -> None:
    """Entry point for ``toolboxctl env``."""
    as_json: bool = getattr(args, "json", False)

    cfg = load_config()
    env_map = config_to_env(cfg)

    if as_json:
        # stdout — machine-readable
        print(json.dumps(env_map, indent=2))
    else:
        # stdout — sourceable shell exports
        for key, value in sorted(env_map.items()):
            print(f"export {key}={shlex.quote(value)}")
        # Only show the hint when stdout is a TTY (not piped into eval)
        if sys.stdout.isatty():
            info("Paste or eval the lines above to inject into your shell.")
