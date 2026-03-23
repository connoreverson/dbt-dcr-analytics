"""Grain verification, join cardinality, and layer-specific lint.

Usage:
    python -m scripts.grain --select fct_reservations
    python -m scripts.grain --select int_parks --output markdown
    python -m scripts.grain --select stg_vistareserve__reservations --checks staging
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

OUTPUT_DIR = Path("tmp/grain")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Grain verification, join cardinality, and layer-specific lint.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--select", "-s", required=True, metavar="SELECTOR",
        help="dbt model selector (e.g. fct_reservations, int_parks)",
    )
    parser.add_argument(
        "--output", "-o", default="terminal", metavar="MODE",
        help="Output mode: terminal, markdown, llm (default: terminal)",
    )
    parser.add_argument(
        "--checks", default="all", metavar="CHECKS",
        help="Comma-separated checks: grain, joins, lint, all (default: all)",
    )
    return parser.parse_args(argv)


def _write_markdown(model_name: str, sections: list[tuple[str, str]]) -> Path:
    """Write collected results to a markdown file. Returns the file path."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{model_name}.md"
    lines = [f"# Grain Analysis: {model_name}\n"]
    for heading, content in sections:
        lines.append(f"\n## {heading}\n")
        lines.append(content)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def _format_key_discovery(candidates: list[dict]) -> str:
    if not candidates:
        return "_No candidate keys found._\n"
    rows = ["| Columns | Uniqueness | Status |", "| --- | --- | --- |"]
    for c in candidates[:10]:
        cols = ", ".join(c["columns"])
        ratio = f"{c['uniqueness_ratio']:.1%}"
        status = "[ok]" if c["uniqueness_ratio"] >= 0.99 else "[ ~]" if c["uniqueness_ratio"] >= 0.9 else "[ x]"
        rows.append(f"| {cols} | {ratio} | {status} |")
    return "\n".join(rows) + "\n"


def _format_join_analysis(joins: list[dict]) -> str:
    if not joins:
        return "_No joins found in compiled SQL._\n"
    rows = ["| # | Type | Right Table | ON Condition |", "| --- | --- | --- | --- |"]
    for i, j in enumerate(joins, 1):
        on = j["on_condition"].replace("|", "\\|") if j["on_condition"] else ""
        rows.append(f"| {i} | {j['join_type']} | {j['right_table']} | {on} |")
    return "\n".join(rows) + "\n"


def _format_findings(findings: list[dict]) -> str:
    if not findings:
        return "_No issues detected._\n"
    lines = []
    for f in findings:
        icon = "**[x]**" if f["severity"] == "error" else "*[!]*"
        lines.append(f"- {icon} {f['message']}")
        lines.append(f"  - {f['detail']}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

    if args.output != "terminal":
        abs_dir = OUTPUT_DIR.resolve()
        print(f"Output directory: {abs_dir}")

    from scripts._core.selector import resolve_selector, determine_layer

    try:
        targets = resolve_selector(args.select)
    except Exception as exc:
        print(f"Error resolving selector: {exc}", file=sys.stderr)
        return 1

    checks = set(args.checks.split(",")) if args.checks != "all" else {"grain", "joins", "lint"}
    exit_code = 0

    for target in targets:
        if target.prefix == "source":
            continue
        layer = determine_layer(target.table)
        sections: list[tuple[str, str]] = []

        if "grain" in checks:
            from scripts.grain.key_discovery import run_key_discovery
            candidates = run_key_discovery(target, args.output)
            if args.output != "terminal":
                sections.append(("Key Discovery", _format_key_discovery(candidates)))

        if "joins" in checks:
            from scripts.grain.join_analysis import run_join_analysis
            joins = run_join_analysis(target, args.output)
            if args.output != "terminal":
                sections.append(("Join Analysis", _format_join_analysis(joins)))

        if "lint" in checks:
            lint_findings: list[dict] = []
            if layer == "staging" or layer == "base":
                from scripts.grain.staging_lint import run_staging_lint
                lint_findings = run_staging_lint(target, args.output)
            elif layer == "integration":
                from scripts.grain.integration_lint import run_integration_lint
                lint_findings = run_integration_lint(target, args.output)
            elif layer == "marts":
                from scripts.grain.mart_lint import run_mart_lint
                lint_findings = run_mart_lint(target, args.output)

            from scripts.grain.dag_lint import run_dag_lint
            dag_findings = run_dag_lint(target, args.output)

            if args.output != "terminal":
                all_findings = lint_findings + dag_findings
                sections.append(("Lint", _format_findings(all_findings)))

        if args.output != "terminal" and sections:
            out_path = _write_markdown(target.table, sections)
            print(f"  wrote {out_path}")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
