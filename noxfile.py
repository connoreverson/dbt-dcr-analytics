"""
Local CI automation for DCR Analytics using nox.

Provides sessions for development testing, linting, and validation.

Usage:
    nox              # Run all sessions
    nox -s build     # Run specific session
    nox --no-venv    # Use existing venv
"""

import nox

# Python version
python = "3.10"

# Sessions to run by default
nox.options.sessions = ["deps", "seed", "build", "lint", "score", "check"]


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
    session.run("dbt-score", "score", external=True)


@nox.session
def check(session):
    """Run custom governance checks."""
    session.env["PYTHONUTF8"] = "1"
    session.run(
        "python",
        "scripts/check_model.py",
        "--select",
        "state:modified",
        "--json",
        "--output",
        "tmp/check_model.json",
        external=True,
    )


@nox.session
def ci(session):
    """Run all CI checks (deps → seed → build → lint → score → check)."""
    session.run("dbt", "deps", external=True)
    session.run("dbt", "seed", external=True)
    session.run("dbt", "build", external=True)
    session.run("sqlfluff", "lint", "models/", "--dialect", "duckdb", external=True)
    session.run("dbt-score", "score", external=True)
    session.env["PYTHONUTF8"] = "1"
    session.run(
        "python",
        "scripts/check_model.py",
        "--select",
        "state:modified",
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
