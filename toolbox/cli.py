"""CLI entrypoint for toolboxctl.

All subcommand modules are lazily imported to keep startup fast.
"""

from __future__ import annotations

import argparse
import sys

from toolbox import __version__


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="toolboxctl",
        description="Adservio Claude Code Toolbox — installer, configurator, and developer assets.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"toolboxctl {__version__}",
    )

    sub = parser.add_subparsers(dest="command")
    sub.required = True

    # --- install -----------------------------------------------------------
    p_install = sub.add_parser("install", help="Install memctl + CloakMCP")
    p_install.add_argument(
        "--fts",
        choices=["fr", "en", "raw"],
        default="fr",
        help="FTS tokenizer language (default: fr)",
    )
    p_install.add_argument(
        "--upgrade",
        action="store_true",
        help="Force upgrade of already-installed packages",
    )
    p_install.add_argument(
        "--global",
        dest="do_global",
        action="store_true",
        help="Wire CloakMCP hooks and conventions into ~/.claude/ (global scope)",
    )
    p_install.add_argument(
        "--uninstall",
        action="store_true",
        help="Remove global Claude Code wiring (hooks, permissions, CLAUDE.md block)",
    )

    # --- init --------------------------------------------------------------
    p_init = sub.add_parser("init", help="Wire .claude/ commands and create config")
    p_init.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files",
    )
    p_init.add_argument(
        "--fts",
        choices=["fr", "en", "raw"],
        default="fr",
        help="FTS tokenizer language (default: fr)",
    )

    # --- status ------------------------------------------------------------
    sub.add_parser("status", help="Show deterministic status report")

    # --- doctor ------------------------------------------------------------
    sub.add_parser("doctor", help="Diagnose toolbox installation health")

    # --- eco ---------------------------------------------------------------
    p_eco = sub.add_parser("eco", help="Toggle eco mode")
    p_eco.add_argument(
        "action",
        nargs="?",
        choices=["on", "off"],
        default=None,
        help="Enable or disable eco mode (omit to show current state)",
    )

    # --- env ---------------------------------------------------------------
    p_env = sub.add_parser("env", help="Export config as env vars")
    p_env.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON instead of shell exports",
    )

    # --- playground --------------------------------------------------------
    p_pg = sub.add_parser("playground", help="Create playground venv with smoke tests")
    p_pg.add_argument(
        "--clean",
        action="store_true",
        help="Remove existing playground",
    )

    return parser


def main(argv: list[str] | None = None) -> None:
    """Parse arguments and dispatch to the appropriate subcommand."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    # Lazy imports per subcommand (fast startup)
    if args.command == "install":
        from toolbox.install import cmd_install
        cmd_install(args)
    elif args.command == "init":
        from toolbox.init import cmd_init
        cmd_init(args)
    elif args.command == "status":
        from toolbox.status import cmd_status
        cmd_status(args)
    elif args.command == "doctor":
        from toolbox.doctor import cmd_doctor
        cmd_doctor(args)
    elif args.command == "eco":
        from toolbox.eco import cmd_eco
        cmd_eco(args)
    elif args.command == "env":
        from toolbox.env import cmd_env
        cmd_env(args)
    elif args.command == "playground":
        from toolbox.playground import cmd_playground
        cmd_playground(args)


if __name__ == "__main__":
    main()
