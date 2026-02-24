"""Guided secret recovery and memory health advisory.

Wraps ``cloak recover``, ``cloak restore``, and ``cloak verify`` in a
diagnostic-first workflow: diagnose → report → confirm → recover → verify.

Memory advisory (``--with-memory``, ``--memory-only``) adds read-only health
checks via ``memctl doctor/status/stats/consolidate --dry-run``.  No mutations.

Exit codes:
    0 — clean (no recovery needed) or recovered + verified
    1 — target directory missing (rescue) / memory issues found (--memory-only)
    2 — cloak not on PATH (rescue) / memctl not on PATH (--memory-only)
    3 — remediation attempted but verification failed

All interaction with CloakMCP and memctl is via subprocess — no Python-level
imports.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from toolbox.helpers import (
    _bold,
    _cyan,
    _green,
    _red,
    _yellow,
    ask_yes_no,
    die,
    error,
    info,
    print_table,
    run,
    warn,
)

# ---------------------------------------------------------------------------
# Detection helpers
# ---------------------------------------------------------------------------


def _check_cloak() -> bool:
    """Return True if ``cloak`` is on PATH."""
    return shutil.which("cloak") is not None


def _cloak_status(directory: str) -> dict | None:
    """Run ``cloak status --dir DIR --json`` and return parsed dict, or None."""
    result = run(
        ["cloak", "status", "--dir", directory, "--json"],
        check=False,
        quiet=True,
    )
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except (json.JSONDecodeError, ValueError):
        return None


def _has_stale_session(directory: str) -> bool:
    """Check for a ``.cloak-session-state`` file indicating an unfinished session."""
    return (Path(directory) / ".cloak-session-state").is_file()


def _scan_tags(directory: str) -> tuple[int, list[str]]:
    """Run ``cloak verify --dir DIR`` and return (tag_count, files_with_tags).

    Returns (0, []) if verify reports clean or the command fails.
    """
    result = run(
        ["cloak", "verify", "--dir", directory],
        check=False,
        quiet=True,
    )
    if result.returncode == 0:
        return 0, []
    # Parse verify output — lines typically list affected files
    files: list[str] = []
    count = 0
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        # Lines containing TAG- indicate residual tags
        if "TAG-" in stripped:
            count += 1
            # Extract filename if present (first token before ':')
            if ":" in stripped:
                fname = stripped.split(":")[0].strip()
                if fname and fname not in files:
                    files.append(fname)
    return max(count, len(files)), files


def _list_backups(directory: str) -> list[str]:
    """List available CloakMCP backups for *directory*.

    Tries ``cloak restore --list --dir DIR``.  Returns list of backup IDs.
    """
    result = run(
        ["cloak", "restore", "--list", "--dir", directory],
        check=False,
        quiet=True,
    )
    if result.returncode != 0:
        return []
    ids: list[str] = []
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and not stripped.startswith("-"):
            # Take first whitespace-delimited token as the ID
            token = stripped.split()[0]
            if token:
                ids.append(token)
    return ids


# ---------------------------------------------------------------------------
# Memory detection helpers
# ---------------------------------------------------------------------------


def _check_memctl() -> bool:
    """Return True if ``memctl`` is on PATH."""
    return shutil.which("memctl") is not None


def _memctl_version() -> tuple[int, ...] | None:
    """Parse ``memctl --version`` into a version tuple, or None on failure."""
    result = run(["memctl", "--version"], check=False, quiet=True)
    if result.returncode != 0:
        return None
    # Expect output like "memctl 0.18.0" or just "0.18.0"
    m = re.search(r"(\d+(?:\.\d+)+)", result.stdout.strip())
    if not m:
        return None
    return tuple(int(p) for p in m.group(1).split("."))


def _memctl_doctor(directory: str) -> dict | None:
    """Run ``memctl doctor --json`` in *directory* and return parsed dict."""
    result = run(
        ["memctl", "doctor", "--json"],
        check=False, quiet=True, cwd=directory,
    )
    if result.returncode not in (0, 1):  # doctor exits 1 on warnings
        return None
    try:
        return json.loads(result.stdout)
    except (json.JSONDecodeError, ValueError):
        return None


def _memctl_status(directory: str) -> dict | None:
    """Run ``memctl status --json`` in *directory* and return parsed dict."""
    result = run(
        ["memctl", "status", "--json"],
        check=False, quiet=True, cwd=directory,
    )
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except (json.JSONDecodeError, ValueError):
        return None


def _memctl_stats(directory: str) -> dict | None:
    """Run ``memctl stats --json`` in *directory* and return parsed dict."""
    result = run(
        ["memctl", "stats", "--json"],
        check=False, quiet=True, cwd=directory,
    )
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except (json.JSONDecodeError, ValueError):
        return None


def _memctl_consolidate_dry(directory: str) -> dict | None:
    """Run ``memctl consolidate --dry-run --json`` in *directory*."""
    result = run(
        ["memctl", "consolidate", "--dry-run", "--json"],
        check=False, quiet=True, cwd=directory,
    )
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except (json.JSONDecodeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# MemoryAdvisory dataclass
# ---------------------------------------------------------------------------


@dataclass
class MemoryAdvisory:
    """Read-only memory health diagnostic."""

    memctl_ok: bool = False
    memctl_version: str = ""
    doctor_available: bool = False
    doctor_checks: list[dict] = field(default_factory=list)
    doctor_status: str = ""
    db_path: str = ""
    db_exists: bool = False
    eco_mode: str = ""
    total_items: int = 0
    tiers: dict[str, int] = field(default_factory=dict)
    fts5_available: bool = False
    fts_tokenizer_mismatch: bool = False
    consolidation_clusters: int = 0
    consolidation_merges: int = 0
    advice: list[str] = field(default_factory=list)

    @property
    def has_issues(self) -> bool:
        return bool(self.advice)


def _diagnose_memory(directory: str) -> MemoryAdvisory:
    """Build a read-only memory health advisory for *directory*."""
    adv = MemoryAdvisory()

    # 1. Check memctl on PATH
    if not _check_memctl():
        adv.advice.append("memctl not found on PATH. Install: pipx install memctl[mcp,docs]")
        return adv
    adv.memctl_ok = True

    # 2. Parse version
    ver = _memctl_version()
    if ver:
        adv.memctl_version = ".".join(str(p) for p in ver)
        adv.doctor_available = ver >= (0, 18, 0)

    # 3. Doctor (v0.18.0+)
    if adv.doctor_available:
        doc = _memctl_doctor(directory)
        if doc:
            adv.doctor_status = doc.get("status", "")
            adv.doctor_checks = doc.get("checks", [])
            # Extract structured fields from doctor checks
            for chk in adv.doctor_checks:
                name = chk.get("name", "")
                detail = chk.get("detail", "")
                status = chk.get("status", "")
                if name == "db_exists":
                    adv.db_exists = status == "pass"
                    adv.db_path = detail
                elif name == "fts5_support":
                    adv.fts5_available = status == "pass"
                elif name == "eco_config":
                    adv.eco_mode = detail

    # 4. Status
    st = _memctl_status(directory)
    if st:
        if not adv.db_path:
            adv.db_path = st.get("db_path", st.get("db", ""))
        if not adv.doctor_available:
            adv.db_exists = st.get("db_exists", False)
            adv.eco_mode = st.get("eco_mode", st.get("eco", ""))
        adv.total_items = st.get("total_items", st.get("total", 0))
        adv.tiers = st.get("tiers", {})
        adv.fts_tokenizer_mismatch = st.get("fts_tokenizer_mismatch", False)

    # 5. Stats (confirms FTS5 if doctor unavailable)
    if adv.db_exists or (st and not adv.doctor_available):
        stats = _memctl_stats(directory)
        if stats and not adv.doctor_available:
            adv.fts5_available = stats.get("fts5_available", stats.get("fts5", False))

    # 6. Consolidation dry-run
    if adv.db_exists:
        cons = _memctl_consolidate_dry(directory)
        if cons:
            adv.consolidation_clusters = cons.get("clusters", 0)
            adv.consolidation_merges = cons.get("merges", cons.get("potential_merges", 0))

    # Advice generation
    if not adv.db_exists and adv.db_path:
        adv.advice.append(f"Memory database not found at {adv.db_path}. Run: memctl init")
    elif not adv.db_exists and not adv.db_path:
        adv.advice.append("Memory database not found. Run: memctl init")
    if adv.total_items == 0 and adv.db_exists:
        adv.advice.append("Memory is empty. Run: memctl push or /scan")
    if adv.eco_mode in ("not installed", ""):
        adv.advice.append("Eco mode is not installed. Run: toolboxctl eco on")
    if adv.fts_tokenizer_mismatch:
        adv.advice.append("FTS tokenizer mismatch detected. Run: memctl reindex --dry-run")
    if adv.consolidation_clusters > 0:
        adv.advice.append(
            f"Consolidation suggested ({adv.consolidation_clusters} clusters, "
            f"{adv.consolidation_merges} potential merges). Run: memctl consolidate --dry-run"
        )
    if not adv.fts5_available and adv.db_exists:
        adv.advice.append("FTS5 not available — search/recall will be degraded")
    # Doctor-specific advice
    if adv.doctor_available:
        for chk in adv.doctor_checks:
            if chk.get("status") == "fail":
                msg = chk.get("message", chk.get("name", "unknown check"))
                adv.advice.append(f"memctl doctor: {msg}")
                if chk.get("name") == "integrity_check":
                    adv.advice.append("Database integrity check failed — consider backup + reset")

    return adv


def _advisory_to_dict(adv: MemoryAdvisory) -> dict:
    """Serialize a MemoryAdvisory to a JSON-safe dict."""
    return {
        "memctl_ok": adv.memctl_ok,
        "memctl_version": adv.memctl_version,
        "doctor_available": adv.doctor_available,
        "doctor_status": adv.doctor_status,
        "doctor_checks": adv.doctor_checks,
        "db_path": adv.db_path,
        "db_exists": adv.db_exists,
        "eco_mode": adv.eco_mode,
        "total_items": adv.total_items,
        "tiers": adv.tiers,
        "fts5_available": adv.fts5_available,
        "fts_tokenizer_mismatch": adv.fts_tokenizer_mismatch,
        "consolidation_clusters": adv.consolidation_clusters,
        "consolidation_merges": adv.consolidation_merges,
        "advice": adv.advice,
    }


def _print_memory_advisory(adv: MemoryAdvisory, *, quiet: bool = False) -> None:
    """Print a formatted memory health advisory to stderr."""
    if quiet:
        return

    print(file=sys.stderr)
    info(f"[Advisory] Memory health (non-destructive)\n")

    if not adv.memctl_ok:
        print(f"  {'memctl':<22s}  {_red('not found')}", file=sys.stderr)
        if adv.advice:
            print(file=sys.stderr)
            info("Recommended:")
            for a in adv.advice:
                print(f"    {a}", file=sys.stderr)
        print(file=sys.stderr)
        return

    # Version
    print(f"  {'memctl':<22s}  {adv.memctl_version or 'unknown'}", file=sys.stderr)

    # Doctor summary
    if adv.doctor_available and adv.doctor_checks:
        pass_count = sum(1 for c in adv.doctor_checks if c.get("status") == "pass")
        total = len(adv.doctor_checks)
        non_pass = total - pass_count
        if non_pass == 0:
            doc_str = _green(f"{pass_count}/{total} pass")
        else:
            parts = [f"{pass_count} pass"]
            warn_count = sum(1 for c in adv.doctor_checks if c.get("status") == "warn")
            fail_count = sum(1 for c in adv.doctor_checks if c.get("status") == "fail")
            if warn_count:
                parts.append(f"{warn_count} warn")
            if fail_count:
                parts.append(f"{fail_count} fail")
            doc_str = _yellow(", ".join(parts))
        print(f"  {'doctor':<22s}  {doc_str}", file=sys.stderr)
    elif not adv.doctor_available:
        print(f"  {'doctor':<22s}  {_yellow('not available (upgrade to 0.18.0+)')}", file=sys.stderr)

    # DB
    print(f"  {'DB path':<22s}  {adv.db_path or 'n/a'}", file=sys.stderr)
    db_val = _green("yes") if adv.db_exists else _red("no")
    print(f"  {'DB exists':<22s}  {db_val}", file=sys.stderr)

    # Eco
    eco_val = adv.eco_mode if adv.eco_mode else "unknown"
    print(f"  {'Eco mode':<22s}  {eco_val}", file=sys.stderr)

    # Items
    if adv.db_exists:
        tier_parts = ", ".join(f"{k}: {v}" for k, v in adv.tiers.items()) if adv.tiers else ""
        items_str = str(adv.total_items)
        if tier_parts:
            items_str += f" ({tier_parts})"
        print(f"  {'Items':<22s}  {items_str}", file=sys.stderr)

    # FTS5
    fts_val = _green("available") if adv.fts5_available else _yellow("not available")
    print(f"  {'FTS5':<22s}  {fts_val}", file=sys.stderr)

    # Tokenizer match
    if adv.db_exists:
        tok_val = _green("yes") if not adv.fts_tokenizer_mismatch else _yellow("mismatch")
        print(f"  {'Tokenizer match':<22s}  {tok_val}", file=sys.stderr)

    # Consolidation
    if adv.db_exists:
        if adv.consolidation_clusters > 0:
            cons_str = f"{adv.consolidation_clusters} clusters, {adv.consolidation_merges} potential merges"
        else:
            cons_str = _green("clean")
        print(f"  {'Consolidation':<22s}  {cons_str}", file=sys.stderr)

    # Advice
    if adv.advice:
        print(file=sys.stderr)
        info("Recommended:")
        for a in adv.advice:
            print(f"    {a}", file=sys.stderr)

    print(file=sys.stderr)


# ---------------------------------------------------------------------------
# Situation dataclass
# ---------------------------------------------------------------------------


@dataclass
class Situation:
    """Aggregated diagnostic state for a project directory."""

    cloak_ok: bool = False
    session_stale: bool = False
    vault_exists: bool = False
    vault_entries: int = 0
    residual_tags: int = 0
    files_with_tags: list[str] = field(default_factory=list)
    backup_count: int = 0

    @property
    def needs_recovery(self) -> bool:
        return self.session_stale or self.residual_tags > 0

    @property
    def severity(self) -> str:
        """Return ``"clean"``, ``"stale"``, ``"tags"``, or ``"critical"``."""
        if not self.needs_recovery:
            return "clean"
        if self.session_stale and self.residual_tags > 0:
            return "critical"
        if self.residual_tags > 0:
            return "tags"
        return "stale"


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

_SEVERITY_LABEL = {
    "clean": _green("clean"),
    "stale": _yellow("stale session"),
    "tags": _yellow("residual tags"),
    "critical": _red("critical — stale session + residual tags"),
}


def _print_report(sit: Situation, directory: str, *, quiet: bool = False) -> None:
    """Print a formatted diagnostic table to stderr."""
    if quiet:
        return
    rows = [
        ("cloak on PATH", _green("yes") if sit.cloak_ok else _red("no")),
        ("Session stale", _yellow("yes") if sit.session_stale else _green("no")),
        ("Vault exists", _green("yes") if sit.vault_exists else "no"),
        ("Vault entries", str(sit.vault_entries)),
        ("Residual TAG-xxxx", str(sit.residual_tags)),
        ("Backups available", str(sit.backup_count)),
        ("Severity", _SEVERITY_LABEL.get(sit.severity, sit.severity)),
    ]

    print(file=sys.stderr)
    info(f"Rescue diagnostic — {_bold(directory)}\n")
    for label, value in rows:
        print(f"  {label:<20s}  {value}", file=sys.stderr)

    if sit.files_with_tags:
        print(file=sys.stderr)
        info("Files with residual tags:")
        for f in sit.files_with_tags[:20]:
            print(f"    {f}", file=sys.stderr)
        if len(sit.files_with_tags) > 20:
            print(f"    … and {len(sit.files_with_tags) - 20} more", file=sys.stderr)
    print(file=sys.stderr)


# ---------------------------------------------------------------------------
# Main command
# ---------------------------------------------------------------------------


def cmd_rescue(args) -> None:
    """Entry point for ``toolboxctl rescue``."""
    directory: str = getattr(args, "dir", ".")
    from_backup = getattr(args, "from_backup", None)
    dry_run: bool = getattr(args, "dry_run", False)
    force: bool = getattr(args, "force", False)
    memory_only: bool = getattr(args, "memory_only", False)
    with_memory: bool = getattr(args, "with_memory", False) or memory_only
    json_mode: bool = getattr(args, "json", False)

    target = Path(directory).resolve()
    if not target.is_dir():
        die(f"Target directory does not exist: {target}")
    directory = str(target)

    # --memory-only: skip cloak, run memory advisory only -------------------
    if memory_only:
        adv = _diagnose_memory(directory)
        if json_mode:
            print(json.dumps({"memory": _advisory_to_dict(adv)}, indent=2))
        else:
            _print_memory_advisory(adv)
        sys.exit(2 if not adv.memctl_ok else (1 if adv.has_issues else 0))
        return

    # Phase 1 — Pre-flight --------------------------------------------------
    if not _check_cloak():
        die("cloak not found on PATH. Install CloakMCP: pipx install cloakmcp", code=2)

    # Phase 2 — Diagnose -----------------------------------------------------
    sit = Situation(cloak_ok=True)

    status = _cloak_status(directory)
    if status:
        sit.session_stale = status.get("session_active", False)
        sit.vault_exists = status.get("vault_exists", False)
        sit.vault_entries = status.get("vault_entries", 0)
    else:
        # Fallback: file-based checks
        sit.session_stale = _has_stale_session(directory)
        vault_path = target / ".cloak" / "vault"
        sit.vault_exists = vault_path.is_dir() and any(vault_path.iterdir()) if vault_path.is_dir() else False
        sit.vault_entries = len(list(vault_path.iterdir())) if sit.vault_exists else 0

    tag_count, tag_files = _scan_tags(directory)
    sit.residual_tags = tag_count
    sit.files_with_tags = tag_files

    backups = _list_backups(directory)
    sit.backup_count = len(backups)

    # Phase 3 — Report -------------------------------------------------------
    _print_report(sit, directory, quiet=json_mode)

    # Phase 4 — --from-backup "list" mode ------------------------------------
    if from_backup == "list":
        if not json_mode:
            if not backups:
                info("No backups found.")
            else:
                info(f"Available backups ({len(backups)}):")
                for bid in backups:
                    print(f"    {bid}", file=sys.stderr)
                print(file=sys.stderr)
                info("Restore with: toolboxctl rescue --from-backup <BACKUP_ID>")
        return

    # Phase 5 — Check if recovery needed -------------------------------------
    if not sit.needs_recovery and from_backup is None:
        if not json_mode:
            info("No recovery needed — project is clean.")

        # Memory advisory (combined mode) even when cloak is clean
        mem_dict: dict | None = None
        if with_memory:
            adv = _diagnose_memory(directory)
            if json_mode:
                mem_dict = _advisory_to_dict(adv)
            else:
                _print_memory_advisory(adv)

        if json_mode:
            combined: dict = {
                "rescue": {
                    "directory": directory,
                    "severity": sit.severity,
                    "session_stale": sit.session_stale,
                    "vault_exists": sit.vault_exists,
                    "vault_entries": sit.vault_entries,
                    "residual_tags": sit.residual_tags,
                    "files_with_tags": sit.files_with_tags,
                    "backup_count": sit.backup_count,
                    "actions": [],
                    "verify": "pass",
                    "outcome": "clean",
                },
            }
            if mem_dict is not None:
                combined["memory"] = mem_dict
            print(json.dumps(combined, indent=2))
        return

    # Phase 6 — Confirm (unless --force or --dry-run) ------------------------
    if not dry_run and not force and not json_mode:
        action = "Proceed with recovery?"
        if not ask_yes_no(action):
            info("Aborted.")
            return

    # Phase 7 — Execute recovery ---------------------------------------------
    ok = True
    actions: list[str] = []

    if from_backup is not None and from_backup != "list":
        # Backup-based recovery
        cmd = ["cloak", "restore", "--from-backup", "--backup-id", from_backup,
               "--force", "--dir", directory]
        actions.append(f"restore-from-backup:{from_backup}")
        if dry_run:
            if not json_mode:
                info(f"[dry-run] would run: {' '.join(cmd)}")
        else:
            result = run(cmd, check=False, quiet=False)
            if result.returncode != 0:
                error(f"Backup restore failed (exit {result.returncode})")
                if result.stderr:
                    error(result.stderr.strip())
                ok = False

    else:
        # Standard recovery
        if sit.session_stale:
            cmd = ["cloak", "recover", "--dir", directory]
            actions.append("recover-stale-session")
            if dry_run:
                if not json_mode:
                    info(f"[dry-run] would run: {' '.join(cmd)}")
            else:
                result = run(cmd, check=False, quiet=False)
                if result.returncode != 0:
                    error(f"Session recovery failed (exit {result.returncode})")
                    if result.stderr:
                        error(result.stderr.strip())
                    ok = False

        if sit.residual_tags > 0 and sit.vault_exists:
            cmd = ["cloak", "restore", "--dir", directory]
            actions.append("restore-residual-tags")
            if dry_run:
                if not json_mode:
                    info(f"[dry-run] would run: {' '.join(cmd)}")
            else:
                result = run(cmd, check=False, quiet=False)
                if result.returncode != 0:
                    error(f"Tag restoration failed (exit {result.returncode})")
                    if result.stderr:
                        error(result.stderr.strip())
                    ok = False

    # Phase 8 — Verify -------------------------------------------------------
    verified = True
    if not dry_run:
        verify_cmd = ["cloak", "verify", "--dir", directory]
        result = run(verify_cmd, check=False, quiet=False)
        if result.returncode != 0:
            if not json_mode:
                warn("Verification found remaining issues:")
                if result.stdout:
                    for line in result.stdout.strip().splitlines()[:10]:
                        print(f"    {line}", file=sys.stderr)
            verified = False
            ok = False

    # Phase 8b — Incident report artifact ------------------------------------
    if not dry_run and actions:
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "directory": directory,
            "situation": {
                "severity": sit.severity,
                "session_stale": sit.session_stale,
                "vault_exists": sit.vault_exists,
                "vault_entries": sit.vault_entries,
                "residual_tags": sit.residual_tags,
                "files_with_tags": sit.files_with_tags,
                "backup_count": sit.backup_count,
            },
            "actions": actions,
            "verify": "pass" if verified else "fail",
            "outcome": "recovered" if ok else "failed",
        }
        report_path = Path(directory) / ".cloak-rescue-report.json"
        try:
            report_path.write_text(
                json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            if not json_mode:
                info(f"Incident report written to {report_path}")
        except OSError as exc:
            warn(f"Could not write incident report: {exc}")

    # Phase 9 — Summary ------------------------------------------------------
    if not json_mode:
        print(file=sys.stderr)
        if dry_run:
            info("Dry run complete — no changes were made.")
        elif ok:
            info(_green("Recovery complete — project is clean."))
        else:
            warn("Issues remain — manual inspection may be needed.")
            info("Try: cloak status --dir . && cloak verify --dir .")

    # Memory advisory (combined mode) ----------------------------------------
    mem_dict = None
    if with_memory:
        adv = _diagnose_memory(directory)
        if json_mode:
            mem_dict = _advisory_to_dict(adv)
        else:
            _print_memory_advisory(adv)

    # JSON combined output ---------------------------------------------------
    if json_mode:
        combined = {
            "rescue": {
                "directory": directory,
                "severity": sit.severity,
                "session_stale": sit.session_stale,
                "vault_exists": sit.vault_exists,
                "vault_entries": sit.vault_entries,
                "residual_tags": sit.residual_tags,
                "files_with_tags": sit.files_with_tags,
                "backup_count": sit.backup_count,
                "actions": actions,
                "verify": "pass" if verified else "fail",
                "outcome": ("clean" if not sit.needs_recovery
                            else ("recovered" if ok else "failed")),
            },
        }
        if mem_dict is not None:
            combined["memory"] = mem_dict
        print(json.dumps(combined, indent=2))

    # Exit code contract: 0=clean, 1=dir missing, 2=cloak missing,
    # 3=remediation attempted but verification failed
    if not dry_run and not ok:
        sys.exit(3 if not verified else 1)
