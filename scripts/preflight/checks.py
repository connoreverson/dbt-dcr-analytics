# scripts/preflight/checks.py
"""Preflight check orchestrator -- sequential pipeline with short-circuit on critical failure."""
from __future__ import annotations

import logging
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
        name="Compile",
        passed=False,
        critical=True,
        message="dbt compile failed -- fix SQL syntax first",
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
        name="Build",
        passed=False,
        critical=True,
        message="dbt build failed -- fix model or test errors",
        fix_command=f"dbt build --select {selector}",
    )


def _check_grain(target) -> CheckResult:
    """Step 3: Is the PK unique and tested?"""
    from scripts.grain.key_discovery import run_key_discovery

    candidates = run_key_discovery(target, output_mode="silent")
    if candidates and candidates[0]["uniqueness_ratio"] >= 0.99:
        return CheckResult(name="Grain", passed=True)
    return CheckResult(
        name="Grain",
        passed=True,
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
        name="Join Cardinality",
        passed=True,
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
            name="Layer Lint",
            passed=False,
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
            name="DAG Direction",
            passed=False,
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
        name="Test Coverage",
        passed=True,
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
        return CheckResult(
            name="YAML/SQL Alignment",
            passed=True,
            warnings=["Model not found in manifest -- skipped"],
        )

    yaml_columns = set(node.get("columns", {}).keys())
    if not yaml_columns:
        return CheckResult(
            name="YAML/SQL Alignment",
            passed=True,
            warnings=["No columns defined in YAML"],
        )

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
        return CheckResult(
            name="YAML/SQL Alignment",
            passed=True,
            warnings=[f"Could not query model: {exc}"],
        )

    in_yaml_not_sql = yaml_columns - sql_columns
    in_sql_not_yaml = sql_columns - yaml_columns

    mismatches = []
    if in_yaml_not_sql:
        mismatches.append(f"In YAML but not SQL: {', '.join(sorted(in_yaml_not_sql))}")
    if in_sql_not_yaml:
        mismatches.append(f"In SQL but not YAML: {', '.join(sorted(in_sql_not_yaml))}")

    if mismatches:
        return CheckResult(
            name="YAML/SQL Alignment",
            passed=False,
            message="Column mismatch between YAML and SQL output",
            warnings=mismatches,
        )
    return CheckResult(name="YAML/SQL Alignment", passed=True)


def run_preflight(selector: str, skip_build: bool = False) -> int:
    """Run the full preflight check sequence.

    Returns 0 if all checks pass, 1 if any check fails.
    Short-circuits on critical failures (compile, build).
    """
    from scripts._core.selector import resolve_selector

    print(f"\nPREFLIGHT: {selector}")
    print("=" * (12 + len(selector)))

    results: list[CheckResult] = []

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

    try:
        targets = resolve_selector(selector)
    except Exception as exc:
        print(f"  X Could not resolve selector: {exc}")
        return 1

    for target in targets:
        for check_fn in [_check_grain, _check_joins, _check_layer_lint, _check_dag]:
            r = check_fn(target)
            results.append(r)
            _print_result(r)

    r = _check_test_coverage(selector)
    results.append(r)
    _print_result(r)

    for target in targets:
        r = _check_yaml_sql_alignment(target)
        results.append(r)
        _print_result(r)

    _print_summary(results)
    return 1 if any(not r.passed for r in results) else 0


def _print_result(r: CheckResult) -> None:
    """Print a single check result."""
    if r.passed and not r.warnings:
        print(f"  \u2713 {r.name}")
    elif r.passed and r.warnings:
        print(f"  \u26a0 {r.name}")
        for w in r.warnings[:3]:
            print(f"    \u2192 {w}")
        if r.fix_command:
            print(f"    Fix: {r.fix_command}")
    else:
        print(f"  \u2717 {r.name}: {r.message}")
        if r.fix_command:
            print(f"    Fix: {r.fix_command}")


def _print_summary(results: list[CheckResult]) -> None:
    """Print final summary."""
    passed, failed, warnings = summarize_results(results)
    print(f"\n{chr(0x2500) * 40}")
    print(f"  {passed} passed, {failed} failed, {warnings} with warnings")
    if failed == 0:
        print(f"  \u2713 Ready for PR")
    else:
        print(f"  \u2717 Fix failures before opening PR")
