# Installing Python

## 1. Why Python?

AdservioToolbox orchestrates [CloakMCP](https://pypi.org/project/cloakmcp/) and
[memctl](https://pypi.org/project/memctl/), both implemented as Python packages.
Python is the only runtime prerequisite.

**Why not Node?**  Claude Code itself requires Node (it is part of the
JavaScript ecosystem).  The toolbox does not.  CloakMCP and memctl are Python
libraries, their hooks are Python scripts, and the installer is pure Python
(stdlib only).  Adding a Node dependency would mean requiring *two* runtimes for
no technical benefit.

**Why not a compiled binary?**  The toolbox is a thin orchestration layer — it
installs, configures, and wires components.  Distributing a compiled binary
would add build complexity (cross-compilation, code signing) without reducing
the Python requirement: CloakMCP and memctl still need it.

**What Python provides:**

- Already present on most developer machines (Linux and macOS ship it by
  default; Windows has first-class support via `py` launcher and `winget`).
- Rich standard library: the bootstrap installer (`install.py`) uses only
  stdlib modules — no pip needed for initial execution.
- User-mode installation on all platforms — no admin rights required.

The minimum version is declared in
[`pyproject.toml`](../pyproject.toml) (`requires-python`).  At the time of
writing: **Python 3.10+**.

---

## 2. Quick Check

Verify whether a compliant Python is already available:

```bash
# macOS / Linux
python3 --version

# Windows
py -3 --version
```

If the output shows 3.10 or higher, skip to
[Verifying After Installation](#10-verifying-after-installation).

---

## 3. Minimum Version and Why 3.10

The toolbox requires **Python 3.10+** (declared in `pyproject.toml` as
`requires-python = ">=3.10"`).

Why 3.10 specifically:

- **`match` / `case` statements** (PEP 634) — used in hook dispatch logic.
- **`ParamSpec` and `TypeAlias`** (PEP 612/613) — used by memctl's type
  annotations.
- **Improved error messages** — Python 3.10 introduced significantly better
  tracebacks, which helps users diagnose hook failures.
- **`tomllib`** landed in 3.11, but the toolbox provides a `tomli` fallback
  for 3.10 (declared in `pyproject.toml` dependencies).

Python 3.9 and older are **not supported** — they lack language features that
CloakMCP and memctl depend on.  Python 3.12+ is recommended for best
performance.

---

## 4. Multiple Python Versions Can Coexist

It is normal — and common — for a machine to have **several Python versions
installed simultaneously**.  This is not a conflict; Python is designed for it.

Typical examples:

| Location | Origin | Version |
|----------|--------|---------|
| `/usr/bin/python3` | System package manager | 3.8 (Ubuntu 20.04), 3.10 (22.04), 3.12 (24.04) |
| `/usr/bin/python3.12` | `apt install python3.12` | 3.12 |
| `/opt/homebrew/bin/python3` | Homebrew | 3.12 |
| `~/.local/share/uv/python/` | uv | 3.12 (managed) |
| `C:\Python312\python.exe` | python.org | 3.12 |
| Conda / Anaconda | conda environments | varies per environment |

**Key points:**

- Each Python installation is independent — its own `site-packages`, its own
  `pip`, its own `venv` capability.
- `pipx` creates isolated virtual environments per tool, so the toolbox, memctl,
  and CloakMCP each live in their own venv regardless of how many Pythons exist.
- The toolbox installer picks the **first compliant Python** it finds (see next
  section).  It does not modify or interfere with other installations.
- Conda environments are separate — if you use conda, activate the right
  environment *before* running the installer or `toolboxctl`.

> **Rule of thumb:** having multiple Pythons is fine.  What matters is that the
> one used by `pipx` (or `pip --user`) meets the minimum version.

---

## 5. How to Pick a Specific Python

When multiple Python versions coexist, here is how the toolbox (and `pipx`)
decide which one to use — and how you can override that choice.

### Default resolution order

The installer (`install.py` / `install.sh`) searches in this order:

| Platform | Search order |
|----------|-------------|
| **Linux / macOS** | `python3` → `python` (first match on `PATH` that is ≥ 3.10) |
| **Windows** | `py -3` (py launcher) → `python3` → `python` |

The **first candidate** whose version satisfies `requires-python` wins.

### Forcing a specific Python

If the default pick is wrong (e.g., `python3` points to 3.8 but you have
3.12 installed elsewhere):

**Option A — Set PATH ordering**

```bash
# Prepend the desired Python to PATH for this session
export PATH="/usr/bin/python3.12:$PATH"
python install.py
```

**Option B — Call the installer with a specific interpreter**

```bash
/usr/bin/python3.12 install.py
```

**Option C — Tell pipx which Python to use**

```bash
pipx install --python /usr/bin/python3.12 adservio-toolbox
pipx install --python /usr/bin/python3.12 memctl[mcp,docs]
pipx install --python /usr/bin/python3.12 cloakmcp
```

**Option D — Windows py launcher version selection**

```powershell
py -3.12 install.py
```

The `py` launcher on Windows supports version suffixes: `py -3.12`, `py -3.11`,
etc.  It selects the matching installed version.

### Checking which Python the toolbox actually uses

```bash
toolboxctl doctor
```

The first line of the doctor output shows the Python version and path that the
toolbox is running under.

### Common pitfall: conda vs system Python

If you use conda, `python3` inside an activated environment points to the conda
Python — which may or may not have `venv` and `pip` available.  Two approaches:

1. **Install inside the conda env** (if you want the toolbox in that env):
   `pip install adservio-toolbox` (no pipx needed).
2. **Deactivate conda first** and use the system Python with pipx (recommended):
   `conda deactivate && python install.py`.

---

## 6. Platform Installation Matrix

All instructions below support **user-mode installation** unless explicitly
noted.  Choose the option that matches your environment.

### Windows

| Option | Command / Action | Notes |
|--------|-----------------|-------|
| **A — winget** (recommended) | `winget install Python.Python.3.12` | Ships with Windows 11; available on Windows 10 via App Installer |
| **B — Microsoft Store** | Search "Python 3.12", click Install | Good for corporate environments where winget is allowed |
| **C — python.org** | [Download](https://www.python.org/downloads/windows/) | Check **"Add Python to PATH"** and select **"Install for me only"** |
| **D — Scoop** | `scoop install python` | User-mode by default |
| **E — Chocolatey** | `choco install python --yes` | Requires admin for global install |

After installation, verify:

```powershell
py -3 --version
```

### macOS

| Option | Command / Action | Notes |
|--------|-----------------|-------|
| **A — Homebrew** (recommended) | `brew install python@3.12` | Apple Silicon: ensure `/opt/homebrew/bin` is in `PATH` |
| **B — python.org** | [Download](https://www.python.org/downloads/macos/) | Universal installer, no Homebrew needed |

> **Note on system Python.**  macOS ships `/usr/bin/python3` for internal use.
> It may be too old or lack `venv`.  Always install a user Python via Homebrew
> or python.org rather than relying on the system copy.

### Linux (Debian / Ubuntu)

```bash
sudo apt update && sudo apt install -y python3 python3-venv python3-pip
```

### Linux (Fedora / RHEL)

```bash
sudo dnf install -y python3 python3-pip
```

### Linux (Arch)

```bash
sudo pacman -S python python-pip
```

### Alpine

```bash
sudo apk add python3 py3-pip
```

---

## 7. No Admin Rights?

If you cannot run `sudo` or install system packages:

| Platform | Options |
|----------|---------|
| **Windows** | Microsoft Store, python.org ("Install for me only"), or Scoop (user-mode by default) |
| **macOS** | Homebrew (user install) or python.org |
| **Linux** | [uv fallback](#8-alternative-uv-as-escape-hatch) — provisions Python in user space |

All these install Python under your home directory with no system-wide changes.

---

## 8. Alternative: uv (Escape Hatch)

[uv](https://docs.astral.sh/uv/) is a fast Python package manager that can
**provision Python itself** in user space.  Use it when:

- Python is missing entirely
- The installed Python is too old
- You cannot install packages system-wide (corporate lockdown, no `sudo`)

### Linux / macOS

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv python install 3.12
```

### Windows (PowerShell)

```powershell
irm https://astral.sh/uv/install.ps1 | iex
uv python install 3.12
```

This installs a managed Python runtime under `~/.local/share/uv/` (or
`%LOCALAPPDATA%\uv\` on Windows) without touching the system Python.

After provisioning, the toolbox installer works normally:

```bash
python install.py          # or: uv run python install.py
```

> **Status:** uv is positioned as a *fallback mechanism*, not the primary
> installation path.  The toolbox may adopt uv as a first-class bootstrap route
> in a future version (see `base/installer_upgrade.md` for the parked
> architecture note).

---

## 9. Why Not Docker?

Docker is intentionally **not** the default installation path.

**Functional constraints:**

- Hooks must integrate directly with Claude Code on the **host** system.
- Secret management (CloakMCP) relies on local filesystem access and session
  lifecycle — volume-mapping breaks the pack/unpack boundary.
- Developer workflows require native file editing; Docker introduces latency
  and inotify limitations.

**Operational friction:**

- Volume mapping complexity for `.claude/`, `.cloak/`, and project files.
- Corporate proxy and private registry configuration.
- Additional security review in enterprise environments.
- GPU/runtime constraints if Claude-adjacent ML tools are used.

**The toolbox is designed to be:**

- Lightweight (three `pipx install` commands)
- Local-first (nothing leaves the machine)
- Native to the developer's environment

Containerization may be useful for CI or advanced deployment scenarios, but it
is not required and is not recommended for daily developer use.

---

## 10. Verifying After Installation

Once Python is installed, run the cross-platform installer:

```bash
python install.py
```

Or, if the toolbox is already installed:

```bash
toolboxctl doctor
```

The doctor command verifies:

- Python version (3.10+ required)
- pipx availability
- CloakMCP and memctl installed and on PATH
- Hook wiring status
- Hook platform compatibility (Windows `.py` entrypoints)
- Permissions and CLAUDE.md block

If all checks pass, the environment is ready.

---

## Summary

| Concern | Position |
|---------|----------|
| **Runtime prerequisite** | Python only (no Node, no Docker) |
| **Minimum version** | Declared in `pyproject.toml` (`requires-python`) |
| **Primary install** | System Python + pipx |
| **No-admin fallback** | python.org user install, Scoop, or uv |
| **uv** | Escape hatch today, potential first-class route in the future |
| **Docker** | Not required, not recommended for daily use |
| **User-space** | Fully compatible on all platforms |
