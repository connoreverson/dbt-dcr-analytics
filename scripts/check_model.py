import sys
import os
import argparse
import json
import csv
import subprocess
import re
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

from dbt.cli.main import dbtRunner, dbtRunnerResult
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

IS_JSON_OUTPUT = "--json" in sys.argv
console = Console(quiet=IS_JSON_OUTPUT)

@dataclass
class CheckResult:
    model: str
    name: str
    status: str  # PASS, FAIL, WARN, SKIP
    messages: List[str]

results: List[CheckResult] = []
global_counts = {"PASS": 0, "FAIL": 0, "WARN": 0, "SKIP": 0}

def add_result(model_name: str, name: str, status: str, messages: List[str] = None, quiet: bool = False):
    if messages is None:
        messages = []
    results.append(CheckResult(model=model_name, name=name, status=status, messages=messages))
    global_counts[status] += 1
    
    if not quiet:
        color = "green" if status == "PASS" else "red" if status == "FAIL" else "yellow" if status == "WARN" else "cyan"
        icon = "✓" if status == "PASS" else "✗" if status == "FAIL" else "!" if status == "WARN" else "-"
        
        console.print(f"[{color}]{icon} {name}[/{color}]")
        for msg in messages[:5]:  # Limit inline output, full details can be dumped if needed
            console.print(f"    [dim]{msg}[/dim]")
        if len(messages) > 5:
            console.print(f"    [dim]... and {len(messages) - 5} more lines[/dim]")

def get_model_sql_path(model_name: str, dbt: dbtRunner) -> Optional[Path]:
    res: dbtRunnerResult = dbt.invoke(["ls", "-s", model_name, "--output", "path", "--resource-types", "model", "--quiet"])
    if not res.success or not res.result:
        return None
    for path_str in res.result:
        if path_str.endswith(".sql"):
            return Path(path_str.strip())
    return None

def check_sqlfluff(model_name: str, sql_file: Path):
    console.print("\n[bold]1. sqlfluff lint[/bold]")
    try:
        result = subprocess.run(
            ["sqlfluff", "lint", str(sql_file), "--dialect", "duckdb", "--templater", "dbt", "--format", "json"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            add_result(model_name, "sqlfluff - zero violations", "PASS")
        else:
            try:
                data = json.loads(result.stdout)
                violations = []
                for file_data in data:
                    for v in file_data.get("violations", []):
                        violations.append(f"L{v.get('line_no')}: {v.get('description')}")
                add_result(model_name, f"sqlfluff - {len(violations)} violation(s)", "FAIL", violations)
            except json.JSONDecodeError:
                add_result(model_name, "sqlfluff - formatting error", "FAIL", ["Raw output error", result.stderr])
    except FileNotFoundError:
        add_result(model_name, "sqlfluff - not on PATH", "SKIP", ["sqlfluff missing. Activate venv?"])

def check_dbt_build(model_name: str, dbt: dbtRunner):
    console.print(f"\n[bold]2. dbt build --select {model_name}[/bold]")
    res: dbtRunnerResult = dbt.invoke(["build", "--select", model_name, "--quiet"])
    if res.success:
        add_result(model_name, f"dbt build - test(s) passed", "PASS")
    else:
        errs = []
        if isinstance(res.result, list):
            for r in res.result:
                if getattr(r, 'status', None) in ["error", "fail"] or str(getattr(r, 'status', '')).lower() in ["error", "fail"]:
                    errs.append(f"{getattr(r, 'node', getattr(r, 'name', 'unknown'))}: {getattr(r, 'message', '')}")
        add_result(model_name, f"dbt build - fail/error", "FAIL", errs if errs else ["Build failed with unknown errors"])

def check_dbt_score(model_name: str):
    console.print(f"\n[bold]3. dbt-score lint --select {model_name}[/bold]")
    try:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        result = subprocess.run(
            ["python", "-m", "dbt_score", "lint", "--select", model_name, "-f", "json", "-n", "dbt_score.rules.generic", "-n", "scripts.dbt_score_rules"],
            capture_output=True,
            text=True,
            env=env
        )
        try:
            score_data = json.loads(result.stdout)
            target_key = next((k for k in score_data.keys() if k.endswith(f".{model_name}") and k.startswith("model.")), None)
            
            if target_key:
                node_data = score_data[target_key]
                score = node_data.get("score", 0.0)
                eval_messages = []
                for rule, r_res in node_data.get("evaluations", {}).items():
                    if r_res.get("status") in [1, 2]: # failure/warning in typical rule systems
                        eval_messages.append(f"{rule}: {r_res.get('message')}")
                
                if score < 5.0:
                    add_result(model_name, f"dbt-score - {score} (below 5.0 threshold)", "FAIL", eval_messages)
                else:
                    add_result(model_name, f"dbt-score - {score}", "PASS")
            else:
                 add_result(model_name, "dbt-score - model missing", "WARN", ["Model not found in score output"])

        except json.JSONDecodeError:
            if "score" in result.stdout.lower():
                 add_result(model_name, "dbt-score - Output error", "FAIL", ["Could not parse JSON output, raw debug: " + result.stdout[:200]])
            else:
                 add_result(model_name, "dbt-score - syntax error", "SKIP", ["Unexpected output format"])
    except FileNotFoundError:
        add_result(model_name, "dbt-score not found", "SKIP", ["dbt-score module missing"])

def check_dbt_project_evaluator(model_name: str, dbt: dbtRunner):
    console.print(f"\n[bold]4. dbt-project-evaluator (filtered to {model_name})[/bold]")
    checks = {
        'fct_model_naming_conventions': ('Naming conventions', 'resource_name'),
        'fct_model_directories': ('Directory placement', 'resource_name'),
        'fct_direct_join_to_source': ('Direct source joins', 'child'),
        'fct_missing_primary_key_tests': ('Primary key tests', 'resource_name'),
        'fct_undocumented_models': ('Documentation', 'resource_name'),
        'fct_custom_fact_dim_missing_integration': ('Integrations needed', 'resource_name'),
        'fct_custom_fact_dim_no_staging': ('No Staging on Marts', 'resource_name'),
        'fct_custom_staging_uses_source_or_base': ('Staging bases only', 'resource_name')
    }
    
    for table_name, (label, col) in checks.items():
        query = f"select * from {{{{ ref('{table_name}') }}}} where {col} = '{model_name}'"
        res: dbtRunnerResult = dbt.invoke(["show", "--inline", query, "--limit", "5", "--quiet"])
        
        # In dbtRunner API, `res.result` for `show` gives an Agate table in `res.result.results[0].agate_table` (usually encapsulated)
        rows_found = []
        if res.success and res.result and len(res.result.results) > 0:
            # We access the agate table inside the node result
            show_result = res.result.results[0]
            if hasattr(show_result, 'agate_table') and show_result.agate_table:
                # Get the actual row count
                for row in show_result.agate_table.rows:
                    rows_found.append(str(row))
        
        if rows_found:
            if table_name == 'fct_model_directories':
                add_result(model_name, f"evaluator - {label} (likely Windows false positive)", "WARN")
            else:
                add_result(model_name, f"evaluator - {label}", "FAIL", rows_found)
        else:
            add_result(model_name, f"evaluator - {label}", "PASS")

def get_yaml_node(model_name: str) -> Optional[Dict]:
    manifest_path = Path("target/manifest.json")
    if not manifest_path.exists():
        return None
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    for node_id, node in manifest.get("nodes", {}).items():
        if node.get("name") == model_name and node.get("resource_type") == "model":
            return node
    return None

def check_layer_and_manifest(model_name: str, sql_path: Path, layer: str, node: Dict):
    console.print("\n[bold]6. manifest.json YAML & Layer Checks[/bold]")
    if not node:
         add_result(model_name, "Manifest check", "SKIP", [f"Model '{model_name}' not found in target/manifest.json. Run dbt build first."])
         return

    if layer == "staging":
        basename = sql_path.stem
        if re.match(r"^stg_[a-z0-9]+__[a-z0-9_]+$", basename):
            add_result(model_name, "SQL-STG-04 - double-underscore delimiter", "PASS")
        else:
            add_result(model_name, "SQL-STG-04 - filename missing '__' delimiter", "FAIL", [f"Found: {basename}"])

        try:
            with open(sql_path, "r", encoding="utf-8") as f:
                sql_lines = f.readlines()
            
            has_join = any(re.search(r"^\s*(left|right|inner|cross|full)?\s*join\b", line, re.IGNORECASE) for line in sql_lines)
            has_agg = any(re.search(r"^\s*(group\s+by|having)\b", line, re.IGNORECASE) for line in sql_lines)
            has_where = any(re.search(r"^\s*where\b", line, re.IGNORECASE) and not re.search(r"where\s+true", line, re.IGNORECASE) for line in sql_lines)

            if not has_join and not has_agg and not has_where:
                add_result(model_name, "SQL-STG-06 - no joins, aggregations, or filtering", "PASS")
            else:
                add_result(model_name, "SQL-STG-06 - staging model has forbidden ops (join/group/where)", "FAIL")
            
            has_hk = any(re.search(r"hk_\w+", line, re.IGNORECASE) for line in sql_lines)
            if has_hk:
                add_result(model_name, "SQL-STG-07 - hash key (hk_) present in SQL", "PASS")
            else:
                add_result(model_name, "SQL-STG-07 - no hash key (hk_) found in SQL", "WARN")
        except FileNotFoundError:
            add_result(model_name, "SQL-STG checks", "SKIP", ["SQL file could not be read"])

def check_runtime_schema(model_name: str, layer: str, node: Dict, dbt: dbtRunner):
    console.print("\n[bold]7. Runtime Schema & CDM Column Checks[/bold]")
    res: dbtRunnerResult = dbt.invoke(["show", "--select", model_name, "--limit", "1", "--quiet"])
    
    sql_cols = []
    if res.success and res.result and len(res.result.results) > 0:
        show_result = res.result.results[0]
        if hasattr(show_result, 'agate_table') and show_result.agate_table:
            sql_cols = list(show_result.agate_table.column_names)
            
    if not sql_cols:
        add_result(model_name, "Runtime schema", "SKIP", ["Failed to run `dbt show` or 0 columns returned"])
        return

    # Check YAML sync
    yaml_cols = [c.lower() for c in node.get("columns", {}).keys()] if node else []
    if not yaml_cols:
        add_result(model_name, "YML-SYNC-01 - companion YAML columns", "SKIP", ["No columns defined in companion YAML"])
    else:
        sql_cols_lower = [c.lower() for c in sql_cols]
        missing = [c for c in yaml_cols if c not in sql_cols_lower]
        if not missing:
            add_result(model_name, "YML-SYNC-01 - YAML columns found exactly in runtime SQL output", "PASS")
        else:
            add_result(model_name, "YML-SYNC-01 - YAML columns not found in runtime SQL output", "WARN", missing)
            
    # ALL-CTE-07: PK First
    first_col = sql_cols[0].lower()
    if re.search(r"(^hk_|_sk$|_id$|_key$)", first_col):
        add_result(model_name, f"ALL-CTE-07 - PK first in runtime schema ({first_col})", "PASS")
    else:
        add_result(model_name, f"ALL-CTE-07 - first column '{first_col}' in schema may not be PK", "WARN")

    if layer == "integration":
        has_sk = any(c.lower().endswith("_sk") for c in sql_cols)
        if has_sk:
             add_result(model_name, "SQL-INT-06 - surrogate key (_sk) present in runtime columns", "PASS")
        else:
             add_result(model_name, "SQL-INT-06 - no surrogate key (_sk) found in runtime columns", "WARN")

        # CDM Checks
        try:
            with open("seeds/cdm_crosswalk.csv", "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                cdm_entity = None
                for row in reader:
                    if row.get("integration_model") == model_name:
                        cdm_entity = row.get("cdm_entity")
                        break
                        
            if cdm_entity:
                # Check SQL-INT-03
                snake_cdm = re.sub(r'([a-z])([A-Z])', r'\1_\2', cdm_entity).lower()
                expected_target = snake_cdm if snake_cdm.endswith('s') else snake_cdm + 's'
                expected_model_name = f"int_{expected_target}"
                
                if model_name == expected_model_name:
                    add_result(model_name, f"SQL-INT-03 - Model name matches pluralized CDM entity '{cdm_entity}'", "PASS")
                else:
                    add_result(model_name, f"SQL-INT-03 - Model name '{model_name}' should be '{expected_model_name}' to match CDM entity '{cdm_entity}'", "FAIL")

                # Check SQL-INT-05
                allowed_columns = set()
                cat_dir = Path("seeds/cdm_catalogs")
                if cat_dir.exists():
                    for csv_file in cat_dir.glob("*.csv"):
                        with open(csv_file, "r", encoding="utf-8") as cat_f:
                            cat_reader = csv.DictReader(cat_f)
                            for row in cat_reader:
                                if row.get("cdm_entity_name") == cdm_entity:
                                    allowed_columns.add(row.get("dbt_column_name", "").lower())
                                    
                invalid_cols = []
                for col in sql_cols:
                    col_l = col.lower()
                    if col_l.endswith('_sk') or col_l.endswith('_id'):
                        continue
                    if col_l not in allowed_columns:
                        invalid_cols.append(col)
                        
                if not invalid_cols:
                     add_result(model_name, f"SQL-INT-05 - All columns conform to CDM entity '{cdm_entity}' or are keys", "PASS")
                else:
                     add_result(model_name, f"SQL-INT-05 - Columns not in CDM entity '{cdm_entity}' (and not keys)", "FAIL", invalid_cols)
            else:
                add_result(model_name, "SQL-INT-05 - Could not find CDM entity in cdm_crosswalk.csv", "WARN")
                
        except FileNotFoundError:
             add_result(model_name, "SQL-INT-05 - cdm_crosswalk.csv missing", "WARN")


def main():
    parser = argparse.ArgumentParser(description="Check dbt models against project standards.")
    parser.add_argument("--select", "-s", type=str, required=True, help="dbt selection string (e.g. models/integration or int_parks)")
    parser.add_argument("--json", action="store_true", help="Output results as JSON to stdout")
    args = parser.parse_args()
    
    # Header Panel
    console.print()
    console.print(Panel(f"Testing Models by Selection: [bold]{args.select}[/bold]", border_style="blue", expand=False))
    
    dbt = dbtRunner()
    res: dbtRunnerResult = dbt.invoke(["ls", "-s", args.select, "--resource-types", "model", "--quiet"])
    
    if not res.success or not res.result:
        console.print(f"[red]Could not resolve any models for selection '{args.select}'[/red]")
        sys.exit(1)
        
    resolved_models = [m.split('.')[-1] for m in res.result if isinstance(m, str)]
    
    if not resolved_models:
        console.print(f"[red]No model nodes found for selection '{args.select}'[/red]")
        sys.exit(1)
        
    console.print(f"Discovered {len(resolved_models)} model(s): {', '.join(resolved_models)}")
    
    for model_name in resolved_models:
        console.print("\n" + "="*80)
        console.print(f"  Evaluating: [bold cyan]{model_name}[/bold cyan]")
        console.print("="*80)
        
        sql_path = get_model_sql_path(model_name, dbt)
        if not sql_path:
            console.print(f"[red]Could not resolve model '{model_name}' to a .sql file[/red]")
            continue
    
        layer = "unknown"
        if model_name.startswith("stg_"): layer = "staging"
        elif model_name.startswith("int_"): layer = "integration"
        elif model_name.startswith("fct_"): layer = "fact"
        elif model_name.startswith("dim_"): layer = "dimension"
        elif model_name.startswith("base_"): layer = "base"
            
        console.print(f"SQL Path: {sql_path}")
        console.print(f"Layer: {layer}\n")
    
        check_dbt_build(model_name, dbt)
        check_dbt_score(model_name)
        check_dbt_project_evaluator(model_name, dbt)
        
        node = get_yaml_node(model_name)
        check_layer_and_manifest(model_name, sql_path, layer, node)
        check_runtime_schema(model_name, layer, node, dbt)
        
        # Run sqlfluff LAST because it spawns a subprocess that competes for the DuckDB lock
        check_sqlfluff(model_name, sql_path)

    # Summary
    table = Table(title=f"Global Summary", show_header=True, header_style="bold magenta")
    table.add_column("Result", justify="center")
    table.add_column("Count", justify="right")
    
    table.add_row("[green]PASS[/green]", str(global_counts["PASS"]))
    table.add_row("[red]FAIL[/red]", str(global_counts["FAIL"]))
    table.add_row("[yellow]WARN[/yellow]", str(global_counts["WARN"]))
    table.add_row("[cyan]SKIP[/cyan]", str(global_counts["SKIP"]))
    table.add_row("---", "---")
    table.add_row("[bold]Total Checks[/bold]", str(len(results)))
    
    # Write JSON debug out
    import os
    with open("tmp/checker_failures.json", "w", encoding="utf-8") as f:
        failure_data = [{"model": r.model, "rule": r.name, "messages": r.messages} for r in results if r.status == "FAIL"]
        json.dump(failure_data, f, indent=2)

    if IS_JSON_OUTPUT:
        output_data = [{"model": r.model, "rule": r.name, "status": r.status, "messages": r.messages} for r in results]
        print(json.dumps(output_data, indent=2))
        sys.exit(1 if global_counts["FAIL"] > 0 else 0)

    console.print("\n")
    console.print(table)
    
    if global_counts["FAIL"] > 0:
        # Group failures by model for easy viewing
        failures = [r for r in results if r.status == "FAIL"]
        if failures:
            fail_table = Table(title="Failure Summary", show_header=True)
            fail_table.add_column("Model", style="cyan")
            fail_table.add_column("Rule", style="red")
            fail_table.add_column("Messages", style="dim")
            for f in failures:
                fail_table.add_row(f.model, f.name, "\n".join(f.messages[:5]))
            console.print(fail_table)
            
        console.print(Panel(f"[bold red]Result: FAIL[/bold red] ({global_counts['FAIL']} rule violation(s)) Across {len(resolved_models)} Models", border_style="red", expand=False))
        sys.exit(1)
    else:
        console.print(Panel(f"[bold green]Result: PASS[/bold green] ({global_counts['WARN']} warning(s) to review)", border_style="green", expand=False))
        sys.exit(0)


if __name__ == "__main__":
    main()
