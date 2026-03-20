# Phase 4: `preflight/` — Analyst Self-Check — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `preflight/` package — a single command analysts run before opening a PR that orchestrates compile, build, grain verification, join cardinality, layer-specific lint, DAG direction, test coverage, and YAML/SQL alignment checks.

**Architecture:** Thin orchestrator (`checks.py`) that delegates to `grain/`, `scaffold/`, and dbt CLI. Sequential pipeline that short-circuits on critical failures (compile/build must pass before analysis checks run). All output goes to terminal with pass/fail markers and fix-it commands.

**Tech Stack:** Python 3.10+, dbt-core (dbtRunner), `grain/` (all linters), `scaffold/test_scaffold` (coverage check)

**Spec:** `docs/superpowers/specs/2026-03-20-scripts-redesign-design.md` (section: "Phase 4: `preflight/`")

**Depends on:** Phase 0 (`_core/`), Phase 1 (`grain/`), Phase 3 (`scaffold/`)

---

### Task 1: Create `preflight/` package structure and CLI

**Files:**
- Create: `scripts/preflight/__init__.py`
- Create: `scripts/preflight/cli.py`
- Test: `tests/scripts/test_preflight_cli.py`

- [ ] **Step 1: Write test for CLI parsing**

```python
# tests/scripts/test_preflight_cli.py
from scripts.preflight.cli import parse_args


def test_parse_basic():
    args = parse_args(["--select", "int_parks"])
    assert args.select == "int_parks"


def test_parse_skip_build():
    args = parse_args(["--select", "int_parks", "--skip-build"])
    assert args.skip_build is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/scripts/test_preflight_cli.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement CLI**

```python
# scripts/preflight/__init__.py
```

```python
# scripts/preflight/cli.py
"""Analyst self-check before PR.

Usage:
    python -m scripts.preflight --select int_grant_applications
    python -m scripts.preflight --select fct_reservations --skip-build
"""
from __future__ import annotations

import argparse
import logging
import sys


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preflight check: compile, build, grain, lint, tests, YAML alignment.",
    )
    parser.add_argument(
        "--select", "-s", required=True, metavar="SELECTOR",
        help="dbt model selector",
    )
    parser.add_argument(
        "--skip-build", action="store_true",
        help="Skip compile + build steps (use when model already builds)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

    from scripts.preflight.checks import run_preflight
    return run_preflight(args.select, skip_build=args.skip_build)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/scripts/test_preflight_cli.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/preflight/ tests/scripts/test_preflight_cli.py
git commit -m "feat(preflight): create package structure and CLI"
```

---

### Task 2: Implement `checks.py` — Preflight orchestrator

**Files:**
- Create: `scripts/preflight/checks.py`
- Test: `tests/scripts/test_preflight_checks.py`

- [ ] **Step 1: Write test for check orchestration helpers**

```python
# tests/scripts/test_preflight_checks.py
from scripts.preflight.checks import CheckResult, summarize_results


def test_check_result_pass():
    r = CheckResult(name="Compile", passed=True)
    assert r.passed
    assert r.critical is False


def test_check_result_critical_failure():
    r = CheckResult(name="Build", passed=False, critical=True, message="SQL error")
    assert not r.passed
    assert r.critical


def test_summarize_all_pass():
    results = [
        CheckResult(name="Compile", passed=True),
        CheckResult(name="Build", passed=True),
        CheckResult(name="Grain", passed=True),
    ]
    passed, failed, warnings = summarize_results(results)
    assert passed == 3
    assert failed == 0


def test_summarize_with_failures():
    results = [
        CheckResult(name="Compile", passed=True),
        CheckResult(name="Build", passed=False, critical=True),
        CheckResult(name="Grain", passed=True, warnings=["No PK test"]),
    ]
    passed, failed, warnings = summarize_results(results)
    assert passed == 2
    assert failed == 1
    assert warnings == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/scripts/test_preflight_checks.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement `checks.py`**

```python
# scripts/preflight/checks.py
"""Preflight check orchestrator — sequential pipeline with short-circuit on critical failure."""
from __future__ import annotations

import logging
import sys
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class CheckResult:
    """Result of a single preflight check."""
    name: str
    passed: bool
    critical: bool = False
    message: str = ""
    warnings: list[str] = field(default_factory=list)
    fix_command: str = ""


def summarize_results(results: list[CheckResult]) -> tuple[int, int, int]:
    """Count passed, failed, and warning results."""
    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)
    warnings = sum(1 for r in results if r.warnings)
    return passed, failed, warnings


def _check_compile(selector: str) -> CheckResult:
    """Step 1: Does the model compile?"""
    from dbt.cli.main import dbtRunner
    runner = dbtRunner()
    result = runner.invoke(["compile", "--select", selector])
    if result.success:
        return CheckResult(name="Compile", passed=True)
    return CheckResult(
        name="Compile", passed=False, critical=True,
        message="dbt compile failed — fix SQL syntax first",
        fix_command=f"dbt compile --select {selector}",
    )


def _check_build(selector: str) -> CheckResult:
    """Step 2: Does the model build and pass tests?"""
    from dbt.cli.main import dbtRunner
    runner = dbtRunner()
    result = runner.invoke(["build", "--select", selector])
    if result.success:
        return CheckResult(name="Build", passed=True)
    return CheckResult(
        name="Build", passed=False, critical=True,
        message="dbt build failed — fix model or test errors",
        fix_command=f"dbt build --select {selector}",
    )


def _check_grain(target) -> CheckResult:
    """Step 3: Is the PK unique and tested?"""
    from scripts.grain.key_discovery import run_key_discovery
    candidates = run_key_discovery(target, output_mode="silent")
    if candidates and candidates[0]["uniqueness_ratio"] >= 0.99:
        return CheckResult(name="Grain", passed=True)
    return CheckResult(
        name="Grain", passed=True,
        warnings=["No candidate key with >99% uniqueness found"],
        fix_command=f"python -m scripts.grain --select {target.table} --checks grain",
    )


def _check_joins(target) -> CheckResult:
    """Step 4: Any fan-outs?"""
    from scripts.grain.join_analysis import run_join_analysis
    joins = run_join_analysis(target, output_mode="silent")
    fan_outs = [j for j in joins if j.get("fan_out")]
    if not fan_outs:
        return CheckResult(name="Join Cardinality", passed=True)
    return CheckResult(
        name="Join Cardinality", passed=True,
        warnings=[f"Fan-out detected on {len(fan_outs)} join(s)"],
        fix_command=f"python -m scripts.grain --select {target.table} --checks joins",
    )


def _check_layer_lint(target) -> CheckResult:
    """Step 5: Layer-specific lint."""
    from scripts._core.selector import _determine_layer
    layer = _determine_layer(target.table)

    findings = []
    if layer in ("staging", "base"):
        from scripts.grain.staging_lint import run_staging_lint
        findings = run_staging_lint(target, output_mode="silent")
    elif layer == "integration":
        from scripts.grain.integration_lint import run_integration_lint
        findings = run_integration_lint(target, output_mode="silent")
    elif layer == "marts":
        from scripts.grain.mart_lint import run_mart_lint
        findings = run_mart_lint(target, output_mode="silent")

    errors = [f for f in findings if f.get("severity") == "error"]
    warns = [f["message"] for f in findings if f.get("severity") == "warning"]

    if errors:
        return CheckResult(
            name="Layer Lint", passed=False,
            message=f"{len(errors)} error(s) found",
            warnings=warns,
            fix_command=f"python -m scripts.grain --select {target.table} --checks lint",
        )
    return CheckResult(name="Layer Lint", passed=True, warnings=warns)


def _check_dag(target) -> CheckResult:
    """Step 6: DAG direction violations."""
    from scripts.grain.dag_lint import run_dag_lint
    findings = run_dag_lint(target, output_mode="silent")
    errors = [f for f in findings if f.get("severity") == "error"]
    warns = [f["message"] for f in findings]

    if errors:
        return CheckResult(
            name="DAG Direction", passed=False,
            message=f"{len(errors)} direction violation(s)",
            fix_command=f"python -m scripts.grain --select {target.table} --checks lint",
        )
    return CheckResult(name="DAG Direction", passed=True, warnings=warns)


def _check_test_coverage(selector: str) -> CheckResult:
    """Step 7: How many suggested tests are missing?"""
    from scripts.scaffold.test_scaffold import run_test_scaffold
    missing = run_test_scaffold(selector, count_only=True)
    if missing == 0:
        return CheckResult(name="Test Coverage", passed=True)
    return CheckResult(
        name="Test Coverage", passed=True,
        warnings=[f"{missing} suggested test(s) missing"],
        fix_command=f"python -m scripts.scaffold tests --select {selector}",
    )


def _check_yaml_sql_alignment(target) -> CheckResult:
    """Step 8: Do YAML columns match SQL output columns?"""
    from scripts._core.selector import load_manifest

    manifest = load_manifest()
    node_key = f"model.dcr_analytics.{target.table}"
    node = manifest.get("nodes", {}).get(node_key)

    if node is None:
        return CheckResult(name="YAML/SQL Alignment", passed=True,
                           warnings=["Model not found in manifest — skipped"])

    yaml_columns = set(node.get("columns", {}).keys())
    if not yaml_columns:
        return CheckResult(name="YAML/SQL Alignment", passed=True,
                           warnings=["No columns defined in YAML"])

    # Query actual output columns from the materialized model
    try:
        if target.connector_type == "duckdb":
            from scripts._core.connectors.duckdb import DuckDBConnector
            connector = DuckDBConnector(target)
        else:
            from scripts._core.connectors.bigquery import BigQueryConnector
            connector = BigQueryConnector(target)

        schema = connector.get_schema()
        sql_columns = {col.name for col in schema}

        if hasattr(connector, "close"):
            connector.close()
    except Exception as exc:
        return CheckResult(name="YAML/SQL Alignment", passed=True,
                           warnings=[f"Could not query model: {exc}"])

    in_yaml_not_sql = yaml_columns - sql_columns
    in_sql_not_yaml = sql_columns - yaml_columns

    mismatches = []
    if in_yaml_not_sql:
        mismatches.append(f"In YAML but not SQL: {', '.join(sorted(in_yaml_not_sql))}")
    if in_sql_not_yaml:
        mismatches.append(f"In SQL but not YAML: {', '.join(sorted(in_sql_not_yaml))}")

    if mismatches:
        return CheckResult(
            name="YAML/SQL Alignment", passed=False,
            message="Column mismatch between YAML and SQL output",
            warnings=mismatches,
        )
    return CheckResult(name="YAML/SQL Alignment", passed=True)


def run_preflight(selector: str, skip_build: bool = False) -> int:
    """Run the full preflight check sequence."""
    from scripts._core.selector import resolve_selector

    print(f"\nPREFLIGHT: {selector}")
    print("=" * (12 + len(selector)))

    results: list[CheckResult] = []

    # Steps 1-2: Compile and Build (short-circuit on failure)
    if not skip_build:
        r = _check_compile(selector)
        results.append(r)
        _print_result(r)
        if not r.passed:
            _print_summary(results)
            return 1

        r = _check_build(selector)
        results.append(r)
        _print_result(r)
        if not r.passed:
            _print_summary(results)
            return 1

    # Resolve targets for analysis checks
    try:
        targets = resolve_selector(selector)
    except Exception as exc:
        print(f"  ✗ Could not resolve selector: {exc}")
        return 1

    for target in targets:
        # Steps 3-6: Analysis checks
        for check_fn in [_check_grain, _check_joins, _check_layer_lint, _check_dag]:
            r = check_fn(target)
            results.append(r)
            _print_result(r)

    # Step 7: Test coverage
    r = _check_test_coverage(selector)
    results.append(r)
    _print_result(r)

    # Step 8: YAML/SQL alignment
    for target in targets:
        r = _check_yaml_sql_alignment(target)
        results.append(r)
        _print_result(r)

    _print_summary(results)

    # Return 1 if any check failed (not warnings)
    return 1 if any(not r.passed for r in results) else 0


def _print_result(r: CheckResult) -> None:
    """Print a single check result."""
    if r.passed and not r.warnings:
        print(f"  ✓ {r.name}")
    elif r.passed and r.warnings:
        print(f"  ⚠ {r.name}")
        for w in r.warnings[:3]:
            print(f"    → {w}")
        if r.fix_command:
            print(f"    Fix: {r.fix_command}")
    else:
        print(f"  ✗ {r.name}: {r.message}")
        if r.fix_command:
            print(f"    Fix: {r.fix_command}")


def _print_summary(results: list[CheckResult]) -> None:
    """Print final summary."""
    passed, failed, warnings = summarize_results(results)
    print(f"\n{'─' * 40}")
    print(f"  {passed} passed, {failed} failed, {warnings} with warnings")
    if failed == 0:
        print("  ✓ Ready for PR")
    else:
        print("  ✗ Fix failures before opening PR")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/scripts/test_preflight_checks.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/preflight/checks.py tests/scripts/test_preflight_checks.py
git commit -m "feat(preflight): implement 8-step check orchestrator with short-circuit"
```

---

### Task 3: Add VS Code task for preflight

**Files:**
- Create or modify: `.vscode/tasks.json`

- [ ] **Step 1: Check if `.vscode/tasks.json` exists**

Run: `ls .vscode/tasks.json 2>/dev/null || echo "not found"`

- [ ] **Step 2: Create or update `.vscode/tasks.json`**

If the file doesn't exist, create it. If it does, add the preflight task.

```jsonc
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "Preflight: Current Model",
            "type": "shell",
            "command": "source .venv/Scripts/activate && PYTHONUTF8=1 python -m scripts.preflight --select ${input:modelName}",
            "group": "test",
            "presentation": {
                "reveal": "always",
                "panel": "new"
            }
        },
        {
            "label": "Profile: Source Table",
            "type": "shell",
            "command": "source .venv/Scripts/activate && PYTHONUTF8=1 python -m scripts.profiler.cli --select ${input:modelName}",
            "group": "test"
        },
        {
            "label": "New Model: Guided Intake",
            "type": "shell",
            "command": "source .venv/Scripts/activate && PYTHONUTF8=1 python -m scripts.llm_context new-model",
            "group": "none"
        },
        {
            "label": "Grain Check: Current Model",
            "type": "shell",
            "command": "source .venv/Scripts/activate && PYTHONUTF8=1 python -m scripts.grain --select ${input:modelName}",
            "group": "test"
        }
    ],
    "inputs": [
        {
            "id": "modelName",
            "type": "promptString",
            "description": "dbt model or source selector"
        }
    ]
}
```

- [ ] **Step 3: Commit**

```bash
git add .vscode/tasks.json
git commit -m "feat: add VS Code tasks for preflight, profiler, intake, and grain"
```
