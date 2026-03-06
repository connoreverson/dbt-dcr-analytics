"""
Local CI automation for DCR Analytics using nox.

Provides sessions for development testing, linting, and validation.

Usage:
    nox              # Run all sessions
    nox -s build     # Run specific session
    nox --no-venv    # Use existing venv
    nox -s save_state                    # Save baseline from HEAD~1
    DBT_STATE_REF=abc123 nox -s save_state  # Save baseline from a specific commit
"""

import os
import shutil
import nox
from pathlib import Path

# Python version
python = "3.10"

# Sessions to run by default
nox.options.sessions = ["deps", "seed", "build", "lint", "score", "check"]

# Use the project's existing virtualenv instead of creating isolated session venvs.
# All tools (dbt, sqlfluff, dbt-score) are installed there, not in nox-managed envs.
nox.options.default_venv_backend = "none"

_STATE_DIR = Path("tmp/state")
_STATE_MANIFEST = _STATE_DIR / "manifest.json"


@nox.session
def deps(session):
    """Install dbt packages."""
    session.run("dbt", "deps", external=True)


@nox.session
def seed(session):
    """Load seed data."""
    session.run("dbt", "seed", external=True)


@nox.session
def build(session):
    """Build all models and run data tests."""
    session.run("dbt", "build", external=True)


@nox.session
def lint(session):
    """Lint all SQL with sqlfluff."""
    session.run(
        "sqlfluff",
        "lint",
        "models/",
        "--dialect",
        "duckdb",
        external=True,
    )


@nox.session
def score(session):
    """Run dbt-score governance checks."""
    session.env["PYTHONUTF8"] = "1"
    session.run("dbt-score", "lint", external=True)


@nox.session
def save_state(session):
    """Save a comparison manifest from a prior git ref for state:modified selection.

    By default compares against HEAD~1. Override with DBT_STATE_REF env var:
        DBT_STATE_REF=main nox -s save_state
        DBT_STATE_REF=abc1234 nox -s save_state
    """
    session.env["PYTHONUTF8"] = "1"
    ref = os.environ.get("DBT_STATE_REF", "HEAD~1")
    worktree_dir = Path("tmp/_state_worktree")

    # Clean up any stale worktree from a previous interrupted run
    if worktree_dir.exists():
        shutil.rmtree(str(worktree_dir), ignore_errors=True)
    session.run("git", "worktree", "prune", external=True)

    session.run("git", "worktree", "add", str(worktree_dir), ref, external=True)

    try:
        # Copy installed packages so dbt parse works without running dbt deps
        src_pkgs = Path("dbt_packages")
        dst_pkgs = worktree_dir / "dbt_packages"
        if src_pkgs.exists() and not dst_pkgs.exists():
            shutil.copytree(str(src_pkgs), str(dst_pkgs))

        # Match line endings in the worktree to the corresponding file in the current
        # working tree. Windows git autocrlf=true converts LF→CRLF on checkout, but
        # files written directly by tooling (e.g. Claude Code) keep LF, so the project
        # has mixed endings. The worktree always uses CRLF; we mirror the current
        # working tree per-file so dbt produces matching checksums for unchanged content.
        for ext in ("*.sql", "*.yml", "*.yaml"):
            for wt_file in worktree_dir.rglob(ext):
                if "dbt_packages" in wt_file.parts:
                    continue
                rel = wt_file.relative_to(worktree_dir)
                cur_file = Path(".") / rel
                wt_raw = wt_file.read_bytes()
                if cur_file.exists():
                    cur_raw = cur_file.read_bytes()
                    # Match whatever endings the current working tree file uses
                    if b"\r\n" in cur_raw:
                        normalized = wt_raw.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
                    else:
                        normalized = wt_raw.replace(b"\r\n", b"\n")
                else:
                    # File only exists in the baseline (deleted since HEAD~1) — use LF
                    normalized = wt_raw.replace(b"\r\n", b"\n")
                if normalized != wt_raw:
                    wt_file.write_bytes(normalized)

        # dbt parse generates manifest.json without connecting to the database
        _STATE_DIR.mkdir(parents=True, exist_ok=True)
        session.run(
            "dbt", "parse",
            "--project-dir", str(worktree_dir),
            "--profiles-dir", ".",
            external=True,
        )

        shutil.copy(
            str(worktree_dir / "target" / "manifest.json"),
            str(_STATE_MANIFEST),
        )
        print(f"State manifest saved from '{ref}' -> {_STATE_MANIFEST}")

    finally:
        shutil.rmtree(str(worktree_dir), ignore_errors=True)
        session.run("git", "worktree", "prune", external=True)


@nox.session
def check(session):
    """Run custom governance checks on models modified since the saved state baseline.

    Run 'nox -s save_state' first to generate the baseline. Without a baseline,
    falls back to checking all models.
    """
    session.env["PYTHONUTF8"] = "1"

    if _STATE_MANIFEST.exists():
        select = "state:modified"
        extra = ["--state", str(_STATE_DIR)]
    else:
        session.warn(
            f"No state manifest at {_STATE_MANIFEST}. "
            "Run 'nox -s save_state' to generate a baseline. "
            "Falling back to checking all models."
        )
        select = "+"
        extra = []

    session.run(
        "python",
        "scripts/check_model.py",
        "--select", select,
        *extra,
        "--json",
        "--output", "tmp/check_model.json",
        external=True,
    )


@nox.session
def ci(session):
    """Run all CI checks (deps → seed → build → lint → score → check)."""
    session.run("dbt", "deps", external=True)
    session.run("dbt", "seed", external=True)
    session.run("dbt", "build", external=True)
    session.run("sqlfluff", "lint", "models/", "--dialect", "duckdb", external=True)
    session.env["PYTHONUTF8"] = "1"
    session.run("dbt-score", "lint", external=True)
    session.run(
        "python",
        "scripts/check_model.py",
        "--select",
        "state:modified" if _STATE_MANIFEST.exists() else "+",
        *(["--state", str(_STATE_DIR)] if _STATE_MANIFEST.exists() else []),
        "--json",
        "--output",
        "tmp/check_model.json",
        external=True,
    )


@nox.session
def export(session):
    """Export all mart model data to CSV and Parquet."""
    session.run(
        "python",
        "scripts/export_mart_data.py",
        "--format",
        "both",
        external=True,
    )
