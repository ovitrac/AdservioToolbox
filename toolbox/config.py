"""Configuration loader with TOML reader, env var bridge, and precedence chain.

Precedence (highest → lowest):
    CLI flags  >  env vars  >  .adservio-toolbox.toml  >  compiled defaults

The module never imports memctl or CloakMCP.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# TOML reader (stdlib 3.11+ / tomli fallback for 3.10)
# ---------------------------------------------------------------------------

try:
    import tomllib  # type: ignore[import-not-found]
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[import-untyped,no-redef]

# ---------------------------------------------------------------------------
# Compiled defaults
# ---------------------------------------------------------------------------

CONFIG_FILENAME = ".adservio-toolbox.toml"

DEFAULTS: dict[str, dict[str, Any]] = {
    "eco": {
        "enabled_global": False,
    },
    "memctl": {
        "db": ".memory/memory.db",
        "fts": "fr",
        "budget": 2200,
        "tier": "stm",
    },
    "cloak": {
        "policy": ".cloak/policy.yaml",
        "mode": "enforce",
        "fail_closed": False,
    },
}

# TOML key → env var mapping (explicit, no magic)
ENV_MAP: dict[tuple[str, str], str] = {
    ("eco", "enabled_global"): "ADSERVIO_ECO",
    ("memctl", "db"): "MEMCTL_DB",
    ("memctl", "fts"): "MEMCTL_FTS",
    ("memctl", "budget"): "MEMCTL_BUDGET",
    ("memctl", "tier"): "MEMCTL_TIER",
    ("cloak", "policy"): "CLOAK_POLICY",
    ("cloak", "mode"): "CLOAK_MODE",
    ("cloak", "fail_closed"): "CLOAK_FAIL_CLOSED",
}


# ---------------------------------------------------------------------------
# Config discovery
# ---------------------------------------------------------------------------


def find_config(start: Path | None = None) -> Path | None:
    """Walk up from *start* (default: cwd) looking for CONFIG_FILENAME."""
    current = (start or Path.cwd()).resolve()
    for directory in [current, *current.parents]:
        candidate = directory / CONFIG_FILENAME
        if candidate.is_file():
            return candidate
    return None


# ---------------------------------------------------------------------------
# TOML loading
# ---------------------------------------------------------------------------


def load_toml(path: Path) -> dict[str, Any]:
    """Parse a TOML file and return a dict."""
    with open(path, "rb") as fh:
        return tomllib.load(fh)


# ---------------------------------------------------------------------------
# Merged config (defaults ← file ← env vars)
# ---------------------------------------------------------------------------


def load_config(path: Path | None = None) -> dict[str, dict[str, Any]]:
    """Return the fully-resolved configuration dict.

    Merge order: compiled defaults ← TOML file ← env vars.
    """
    # Start with defaults (deep copy)
    cfg: dict[str, dict[str, Any]] = {
        section: dict(values) for section, values in DEFAULTS.items()
    }

    # Layer: TOML file
    config_path = path or find_config()
    if config_path and config_path.is_file():
        file_data = load_toml(config_path)
        for section, values in file_data.items():
            if isinstance(values, dict) and section in cfg:
                cfg[section].update(values)

    # Layer: env vars (highest precedence)
    for (section, key), env_var in ENV_MAP.items():
        env_val = os.environ.get(env_var)
        if env_val is not None:
            # Coerce to the type of the default value
            default_val = DEFAULTS.get(section, {}).get(key)
            cfg.setdefault(section, {})[key] = _coerce(env_val, default_val)

    return cfg


def _coerce(value: str, reference: Any) -> Any:
    """Coerce a string env value to the type of the reference default."""
    if isinstance(reference, bool):
        return value.lower() in ("1", "true", "yes", "on")
    if isinstance(reference, int):
        try:
            return int(value)
        except ValueError:
            return value
    return value


# ---------------------------------------------------------------------------
# Config → env var export
# ---------------------------------------------------------------------------


def config_to_env(cfg: dict[str, dict[str, Any]]) -> dict[str, str]:
    """Convert a resolved config dict to a flat {ENV_VAR: value} mapping."""
    result: dict[str, str] = {}
    for (section, key), env_var in ENV_MAP.items():
        val = cfg.get(section, {}).get(key)
        if val is not None:
            if isinstance(val, bool):
                result[env_var] = "1" if val else "0"
            else:
                result[env_var] = str(val)
    return result


# ---------------------------------------------------------------------------
# TOML writer (minimal, avoids tomli-w dependency)
# ---------------------------------------------------------------------------


def _toml_value(v: Any) -> str:
    """Serialize a single value to TOML syntax."""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, str):
        return f'"{v}"'
    return str(v)


def write_config(cfg: dict[str, dict[str, Any]], path: Path) -> None:
    """Write *cfg* as a TOML file at *path*.

    Uses a minimal hand-rolled serializer (flat tables, no nested tables).
    """
    lines: list[str] = [
        "# Adservio Claude Code Toolbox — configuration",
        "# Precedence: CLI flags > env vars > this file > compiled defaults",
        "",
    ]
    for section, values in cfg.items():
        lines.append(f"[{section}]")
        for k, v in values.items():
            lines.append(f"{k} = {_toml_value(v)}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
