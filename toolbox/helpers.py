"""Shared utilities for the Adservio Toolbox CLI.

Conventions:
- All user-facing messages go to stderr (info, warn, error, die).
- Only machine-readable data goes to stdout (env exports, JSON).
- ANSI colors are emitted only when stderr is a TTY.
"""

from __future__ import annotations

import subprocess
import sys
from typing import Any, Sequence

# ---------------------------------------------------------------------------
# ANSI helpers
# ---------------------------------------------------------------------------

_USE_COLOR = sys.stderr.isatty()


def _sgr(code: str, text: str) -> str:
    if _USE_COLOR:
        return f"\033[{code}m{text}\033[0m"
    return text


def _bold(text: str) -> str:
    return _sgr("1", text)


def _green(text: str) -> str:
    return _sgr("32", text)


def _yellow(text: str) -> str:
    return _sgr("33", text)


def _red(text: str) -> str:
    return _sgr("31", text)


def _cyan(text: str) -> str:
    return _sgr("36", text)


# ---------------------------------------------------------------------------
# Messaging (all to stderr)
# ---------------------------------------------------------------------------


def info(msg: str) -> None:
    """Print an informational message to stderr."""
    print(f"{_green('•')} {msg}", file=sys.stderr)


def warn(msg: str) -> None:
    """Print a warning message to stderr."""
    print(f"{_yellow('!')} {msg}", file=sys.stderr)


def error(msg: str) -> None:
    """Print an error message to stderr."""
    print(f"{_red('✗')} {msg}", file=sys.stderr)


def die(msg: str, code: int = 1) -> None:
    """Print an error and exit."""
    error(msg)
    sys.exit(code)


# ---------------------------------------------------------------------------
# Subprocess wrapper
# ---------------------------------------------------------------------------


def run(
    cmd: Sequence[str],
    *,
    capture: bool = True,
    check: bool = True,
    quiet: bool = False,
    cwd: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a command via subprocess.

    Parameters
    ----------
    cmd : sequence of str
        Command and arguments.
    capture : bool
        Capture stdout/stderr (default True).
    check : bool
        Raise on non-zero exit (default True).
    quiet : bool
        Suppress the info message about the command being run.
    cwd : str or None
        Working directory for the subprocess (default: inherit).
    """
    if not quiet:
        info(f"run: {' '.join(cmd)}")
    return subprocess.run(
        cmd,
        text=True,
        capture_output=capture,
        check=check,
        cwd=cwd,
    )


# ---------------------------------------------------------------------------
# Table printer
# ---------------------------------------------------------------------------


def print_table(
    rows: Sequence[Sequence[Any]],
    headers: Sequence[str] | None = None,
) -> None:
    """Print a simple aligned table to stderr.

    Parameters
    ----------
    rows : list of tuples/lists
        Each inner sequence is one row.
    headers : list of str, optional
        Column headers (printed bold).
    """
    all_rows: list[list[str]] = []
    if headers:
        all_rows.append([str(h) for h in headers])
    for row in rows:
        all_rows.append([str(c) for c in row])

    if not all_rows:
        return

    ncols = max(len(r) for r in all_rows)
    widths = [0] * ncols
    for r in all_rows:
        for i, c in enumerate(r):
            widths[i] = max(widths[i], len(c))

    def _fmt(row: list[str], bold: bool = False) -> str:
        parts = []
        for i, c in enumerate(row):
            padded = c.ljust(widths[i])
            parts.append(_bold(padded) if bold else padded)
        return "  ".join(parts)

    if headers:
        print(_fmt(all_rows[0], bold=True), file=sys.stderr)
        print("  ".join("─" * w for w in widths), file=sys.stderr)
        data = all_rows[1:]
    else:
        data = all_rows

    for r in data:
        print(_fmt(r), file=sys.stderr)


# ---------------------------------------------------------------------------
# Interactive prompts
# ---------------------------------------------------------------------------


def ask_yes_no(prompt: str, default: bool = False) -> bool:
    """Ask a yes/no question on stderr, return boolean.

    Returns *default* on empty input, EOF, or KeyboardInterrupt.
    """
    suffix = "[Y/n]" if default else "[y/N]"
    try:
        answer = input(f"{_yellow('?')} {prompt} {suffix} ").strip().lower()
        if not answer:
            return default
        return answer in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        print(file=sys.stderr)
        return default
