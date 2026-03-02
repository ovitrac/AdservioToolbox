"""Adservio Claude Code Toolbox — installer, configurator, and developer assets."""

from importlib.metadata import version as _pkg_version

try:
    __version__ = _pkg_version("adservio-toolbox")
except Exception:
    __version__ = "0.5.4"  # fallback for editable installs without metadata
