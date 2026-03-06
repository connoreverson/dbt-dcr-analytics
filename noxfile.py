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

    # Refresh target/manifest.json so state:modified compares against the current
    # working tree, not a stale manifest from a previous build.
    session.run("dbt", "parse", external=True)

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
    """Run all CI checks by chaining individual sessions.

    Equivalent to running: nox (default sessions)
    Using session.notify() ensures ci stays in sync with any changes to
    individual sessions rather than duplicating their logic.
    """
    for s in ("deps", "seed", "build", "lint", "score", "check"):
        session.notify(s)


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
