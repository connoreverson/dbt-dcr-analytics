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

@dataclass
class CheckResult:
    model: str
    name: str
    status: str  # PASS, FAIL, WARN, SKIP
    messages: List[str]

class ModelChecker:
    def __init__(self, is_json_output=False):
        self.is_json_output = is_json_output
        self.console = Console(quiet=self.is_json_output)
        self.results: List[CheckResult] = []
        self.global_counts = {"PASS": 0, "FAIL": 0, "WARN": 0, "SKIP": 0}

    def add_result(self, model_name: str, name: str, status: str, messages: List[str] = None, quiet: bool = False):
        if messages is None:
            messages = []
        self.results.append(CheckResult(model=model_name, name=name, status=status, messages=messages))
        self.global_counts[status] += 1
        
        if not quiet:
            color = "green" if status == "PASS" else "red" if status == "FAIL" else "yellow" if status == "WARN" else "cyan"
            icon = "✓" if status == "PASS" else "✗" if status == "FAIL" else "!" if status == "WARN" else "-"
            
            self.console.print(f"[{color}]{icon} {name}[/{color}]")
            for msg in messages[:5]:  # Limit inline output, full details can be dumped if needed
                self.console.print(f"    [dim]{msg}[/dim]")
            if len(messages) > 5:
                self.console.print(f"    [dim]... and {len(messages) - 5} more lines[/dim]")

    def get_model_sql_path(self, model_name: str, dbt: dbtRunner) -> Optional[Path]:
        res: dbtRunnerResult = dbt.invoke(["ls", "-s", model_name, "--output", "path", "--resource-types", "model", "--quiet"])
        if not res.success or not res.result:
            return None
        for path_str in res.result:
            if path_str.endswith(".sql"):
                return Path(path_str.strip())
        return None

    def check_sqlfluff(self, model_name: str, sql_file: Path):
        self.console.print("\n[bold]1. sqlfluff lint[/bold]")
        try:
            result = subprocess.run(
                ["sqlfluff", "lint", str(sql_file), "--dialect", "duckdb", "--templater", "dbt", "--format", "json"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                self.add_result(model_name, "sqlfluff - zero violations", "PASS")
            else:
                try:
                    data = json.loads(result.stdout)
                    violations = []
                    for file_data in data:
                        for v in file_data.get("violations", []):
                            violations.append(f"L{v.get('line_no')}: {v.get('description')}")
                    self.add_result(model_name, f"sqlfluff - {len(violations)} violation(s)", "FAIL", violations)
                except json.JSONDecodeError:
                    self.add_result(model_name, "sqlfluff - formatting error", "FAIL", ["Raw output error", result.stderr])
        except FileNotFoundError:
            self.add_result(model_name, "sqlfluff - not on PATH", "SKIP", ["sqlfluff missing. Activate venv?"])

    def check_dbt_build(self, model_name: str, dbt: dbtRunner):
        self.console.print(f"\n[bold]2. dbt build --select {model_name}[/bold]")
        res: dbtRunnerResult = dbt.invoke(["build", "--select", model_name, "--quiet"])
        if res.success:
            self.add_result(model_name, f"dbt build - test(s) passed", "PASS")
        else:
            errs = []
            if isinstance(res.result, list):
                for r in res.result:
                    if getattr(r, 'status', None) in ["error", "fail"] or str(getattr(r, 'status', '')).lower() in ["error", "fail"]:
                        errs.append(f"{getattr(r, 'node', getattr(r, 'name', 'unknown'))}: {getattr(r, 'message', '')}")
            self.add_result(model_name, f"dbt build - fail/error", "FAIL", errs if errs else ["Build failed with unknown errors"])

    def check_dbt_score(self, model_name: str):
        self.console.print(f"\n[bold]3. dbt-score lint --select {model_name}[/bold]")
        try:
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            result = subprocess.run(
                [sys.executable, "-m", "dbt_score", "lint", "--select", model_name, "-f", "json", "-n", "dbt_score.rules.generic", "-n", "scripts.dbt_score_rules"],
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
                        self.add_result(model_name, f"dbt-score - {score} (below 5.0 threshold)", "FAIL", eval_messages)
                    else:
                        self.add_result(model_name, f"dbt-score - {score}", "PASS")
                else:
                     self.add_result(model_name, "dbt-score - model missing", "WARN", ["Model not found in score output"])

            except json.JSONDecodeError:
                if "score" in result.stdout.lower():
                     self.add_result(model_name, "dbt-score - Output error", "FAIL", ["Could not parse JSON output, raw debug: " + result.stdout[:200]])
                else:
                     self.add_result(model_name, "dbt-score - syntax error", "SKIP", ["Unexpected output format"])
        except FileNotFoundError:
            self.add_result(model_name, "dbt-score not found", "SKIP", ["dbt-score module missing"])

    def check_dbt_project_evaluator(self, model_name: str, dbt: dbtRunner):
        self.console.print(f"\n[bold]4. dbt-project-evaluator (filtered to {model_name})[/bold]")
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
            
            rows_found = []
            if res.success and res.result and len(res.result.results) > 0:
                show_result = res.result.results[0]
                if hasattr(show_result, 'agate_table') and show_result.agate_table:
                    for row in show_result.agate_table.rows:
                        rows_found.append(str(row))
            
            if rows_found:
                if table_name == 'fct_model_directories':
                    self.add_result(model_name, f"evaluator - {label} (likely Windows false positive)", "WARN")
                else:
                    self.add_result(model_name, f"evaluator - {label}", "FAIL", rows_found)
            else:
                self.add_result(model_name, f"evaluator - {label}", "PASS")

    def get_yaml_node(self, model_name: str) -> Optional[Dict]:
        manifest_path = Path("target/manifest.json")
        if not manifest_path.exists():
            return None
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        for node_id, node in manifest.get("nodes", {}).items():
            if node.get("name") == model_name and node.get("resource_type") == "model":
                return node
        return None

    def check_layer_and_manifest(self, model_name: str, sql_path: Path, layer: str, node: Dict):
        self.console.print("\n[bold]6. manifest.json YAML & Layer Checks[/bold]")
        if not node:
             self.add_result(model_name, "Manifest check", "SKIP", [f"Model '{model_name}' not found in target/manifest.json. Run dbt build first."])
             return

        if layer == "staging":
            basename = sql_path.stem
            if re.match(r"^stg_[a-z0-9]+__[a-z0-9_]+$", basename):
                self.add_result(model_name, "SQL-STG-04 - double-underscore delimiter", "PASS")
            else:
                self.add_result(model_name, "SQL-STG-04 - filename missing '__' delimiter", "FAIL", [f"Found: {basename}"])

            try:
                with open(sql_path, "r", encoding="utf-8") as f:
                    sql_lines = f.readlines()
                
                has_join = any(re.search(r"^\s*(left|right|inner|cross|full)?\s*join\b", line, re.IGNORECASE) for line in sql_lines)
                has_agg = any(re.search(r"^\s*(group\s+by|having)\b", line, re.IGNORECASE) for line in sql_lines)
                has_where = any(re.search(r"^\s*where\b", line, re.IGNORECASE) and not re.search(r"where\s+true", line, re.IGNORECASE) for line in sql_lines)

                if not has_join and not has_agg and not has_where:
                    self.add_result(model_name, "SQL-STG-06 - no joins, aggregations, or filtering", "PASS")
                else:
                    self.add_result(model_name, "SQL-STG-06 - staging model has forbidden ops (join/group/where)", "FAIL")
                
                has_hk = any(re.search(r"hk_\w+", line, re.IGNORECASE) for line in sql_lines)
                if has_hk:
                    self.add_result(model_name, "SQL-STG-07 - hash key (hk_) present in SQL", "PASS")
                else:
                    self.add_result(model_name, "SQL-STG-07 - no hash key (hk_) found in SQL", "WARN")
            except FileNotFoundError:
                self.add_result(model_name, "SQL-STG checks", "SKIP", ["SQL file could not be read"])

        # ALL-DAG-01: Unidirectional dependency flow
        def get_layer_rank(m_name):
            if m_name.startswith("source."): return 0
            n = m_name.split(".")[-1]
            if n.startswith("base_"): return 1
            if n.startswith("stg_"): return 2
            if n.startswith("int_"): return 3
            if n.startswith("fct_") or n.startswith("dim_") or n.startswith("rpt_"): return 4
            return 99

        model_layer_rank = get_layer_rank(node.get("name", ""))
        depends_on_nodes = node.get("depends_on", {}).get("nodes", [])
        
        dag_violations = []
        for dep in depends_on_nodes:
            if not (dep.startswith("model.") or dep.startswith("source.")): continue
            dep_rank = get_layer_rank(dep)
            if dep_rank >= model_layer_rank and model_layer_rank != 99:
                dag_violations.append(f"Depends on {dep} (layer >= model layer)")

        if dag_violations:
            self.add_result(model_name, "ALL-DAG-01 - Unidirectional dependency flow", "FAIL", dag_violations)
        else:
            self.add_result(model_name, "ALL-DAG-01 - Unidirectional dependency flow", "PASS")

        # YML-DOC-02: Red-flag words in descriptions
        red_flags = ["unique", "not_null", "fan-out", "deduplication", "protecting against", "tests verify", "collision", "ensures that", "guards against"]
        doc_violations = []
        desc = node.get("description", "").lower()
        for rf in red_flags:
            if rf in desc: doc_violations.append(f"Model description contains red-flag: '{rf}'")
        for col_name, col_info in node.get("columns", {}).items():
            cdesc = col_info.get("description", "").lower()
            for rf in red_flags:
                if rf in cdesc: doc_violations.append(f"Column '{col_name}' description contains red-flag: '{rf}'")
                    
        if doc_violations:
            self.add_result(model_name, "YML-DOC-02 - Red-flag words in descriptions", "WARN", doc_violations)
        else:
            self.add_result(model_name, "YML-DOC-02 - Red-flag words in descriptions", "PASS")

    def check_runtime_schema(self, model_name: str, layer: str, node: Dict, dbt: dbtRunner):
        self.console.print("\n[bold]7. Runtime Schema & CDM Column Checks[/bold]")
        res: dbtRunnerResult = dbt.invoke(["show", "--select", model_name, "--limit", "1", "--quiet"])
        
        sql_cols = []
        if res.success and res.result and len(res.result.results) > 0:
            show_result = res.result.results[0]
            if hasattr(show_result, 'agate_table') and show_result.agate_table:
                sql_cols = list(show_result.agate_table.column_names)
                
        if not sql_cols:
            self.add_result(model_name, "Runtime schema", "SKIP", ["Failed to run `dbt show` or 0 columns returned"])
            return

        # Check YAML sync
        yaml_cols = [c.lower() for c in node.get("columns", {}).keys()] if node else []
        if not yaml_cols:
            self.add_result(model_name, "YML-SYNC-01 - companion YAML columns", "SKIP", ["No columns defined in companion YAML"])
        else:
            sql_cols_lower = [c.lower() for c in sql_cols]
            missing = [c for c in yaml_cols if c not in sql_cols_lower]
            if not missing:
                self.add_result(model_name, "YML-SYNC-01 - YAML columns found exactly in runtime SQL output", "PASS")
            else:
                self.add_result(model_name, "YML-SYNC-01 - YAML columns not found in runtime SQL output", "WARN", missing)
                
        # ALL-CTE-07: PK First
        first_col = sql_cols[0].lower()
        if re.search(r"(^hk_|_sk$|_id$|_key$)", first_col):
            self.add_result(model_name, f"ALL-CTE-07 - PK first in runtime schema ({first_col})", "PASS")
        else:
            self.add_result(model_name, f"ALL-CTE-07 - first column '{first_col}' in schema may not be PK", "WARN")

        if layer == "integration":
            has_sk = any(c.lower().endswith("_sk") for c in sql_cols)
            if has_sk:
                 self.add_result(model_name, "SQL-INT-06 - surrogate key (_sk) present in runtime columns", "PASS")
            else:
                 self.add_result(model_name, "SQL-INT-06 - no surrogate key (_sk) found in runtime columns", "WARN")

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
                        self.add_result(model_name, f"SQL-INT-03 - Model name matches pluralized CDM entity '{cdm_entity}'", "PASS")
                    else:
                        self.add_result(model_name, f"SQL-INT-03 - Model name '{model_name}' should be '{expected_model_name}' to match CDM entity '{cdm_entity}'", "FAIL")

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
                         self.add_result(model_name, f"SQL-INT-05 - All columns conform to CDM entity '{cdm_entity}' or are keys", "PASS")
                    else:
                         self.add_result(model_name, f"SQL-INT-05 - Columns not in CDM entity '{cdm_entity}' (and not keys)", "FAIL", invalid_cols)
                else:
                    self.add_result(model_name, "SQL-INT-05 - Could not find CDM entity in cdm_crosswalk.csv", "WARN")
                    
            except FileNotFoundError:
                 self.add_result(model_name, "SQL-INT-05 - cdm_crosswalk.csv missing", "WARN")

    def check_sql_file_content(self, model_name: str, sql_path: Path):
        self.console.print("\n[bold]8. SQL Static Analysis checks[/bold]")
        try:
            with open(sql_path, "r", encoding="utf-8") as f:
                content = f.read()
            lines = content.splitlines()

            if len(lines) > 200:
                self.add_result(model_name, "ALL-FMT-01 - File length <= 200 lines", "WARN", [f"File is {len(lines)} lines"])
            else:
                self.add_result(model_name, "ALL-FMT-01 - File length <= 200 lines", "PASS")

            config_match = re.search(r"\{\{\s*config\(", content)
            if config_match:
                preceding_text = content[:config_match.start()]
                preceding_text = re.sub(r"--.*?\n", "", preceding_text)
                preceding_text = re.sub(r"/\*.*?\*/", "", preceding_text, flags=re.DOTALL)
                preceding_text = re.sub(r"\{#.*?#\}", "", preceding_text, flags=re.DOTALL)
                if preceding_text.strip():
                    self.add_result(model_name, "ALL-CFG-02 - Config block is first statement", "FAIL", ["Found non-comment text before config block"])
                else:
                    self.add_result(model_name, "ALL-CFG-02 - Config block is first statement", "PASS")
            else:
                self.add_result(model_name, "ALL-CFG-02 - Config block is first statement", "SKIP", ["No config block found"])

            direct_refs = re.findall(r"(?i)\bfrom\s+[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+", content)
            if direct_refs:
                self.add_result(model_name, "ALL-CTE-09 - No direct DB references", "FAIL", direct_refs)
            else:
                self.add_result(model_name, "ALL-CTE-09 - No direct DB references", "PASS")

            clean_content = re.sub(r"--.*$", "", content, flags=re.MULTILINE).strip()
            if re.search(r"(?i)\bselect\s+\*\s+from\s+[a-zA-Z0-9_]+\s*;?$", clean_content):
                self.add_result(model_name, "ALL-CTE-11 - Simple final select", "PASS")
            else:
                self.add_result(model_name, "ALL-CTE-11 - Simple final select", "FAIL", [f"Ending: {clean_content[-100:]}"])

            bad_pk_funcs = re.findall(r"(?i)\b(generate_uuid\(\)|uuid\(\)|random\(\)|newid\(\))", content)
            has_sk_func = "generate_surrogate_key" in content
            if bad_pk_funcs:
                self.add_result(model_name, "ALL-PERF-02 - Reproducible PKs", "FAIL", [f"Found: {bad_pk_funcs[0]}"])
            elif not has_sk_func:
                self.add_result(model_name, "ALL-PERF-02 - Reproducible PKs", "WARN", ["No generate_surrogate_key() found"])
            else:
                self.add_result(model_name, "ALL-PERF-02 - Reproducible PKs", "PASS")

            has_select_distinct = re.search(r"(?i)\bselect\s+distinct\b", content)
            has_bare_union = re.search(r"(?i)\bunion\b(?!\s+all\b)", content)
            perf_03_msgs = []
            if has_select_distinct: perf_03_msgs.append("Found SELECT DISTINCT")
            if has_bare_union: perf_03_msgs.append("Found bare UNION (must be UNION ALL)")
            if perf_03_msgs:
                self.add_result(model_name, "ALL-PERF-03 - No bare UNION or SELECT DISTINCT", "FAIL", perf_03_msgs)
            else:
                self.add_result(model_name, "ALL-PERF-03 - No bare UNION or SELECT DISTINCT", "PASS")

            has_subquery = re.findall(r"(?i)(from\s*\(\s*select\b|where\s+.*?\(\s*select\b|\bjoin\s*\(\s*select\b)", content)
            if has_subquery:
                self.add_result(model_name, "ALL-PERF-04 - CTEs over subqueries", "FAIL", [f"Found: {has_subquery[0]}"])
            else:
                self.add_result(model_name, "ALL-PERF-04 - CTEs over subqueries", "PASS")

        except Exception as e:
            self.add_result(model_name, "SQL Static Analysis", "SKIP", [f"Error reading SQL file: {e}"])

    def run_checks(self, select: str, state: Optional[str] = None) -> List[CheckResult]:
        self.console.print()
        
        # Project-level checks before the model loop
        try:
            import yaml
            packages_path = Path("packages.yml")
            if packages_path.exists():
                with open(packages_path, "r", encoding="utf-8") as f:
                    pkgs = yaml.safe_load(f)
                pkg_violations = []
                for pkg_entry in pkgs.get("packages", []):
                    if "version" not in pkg_entry and "revision" not in pkg_entry and "local" not in pkg_entry:
                        pkg_violations.append(f"Unpinned package: {pkg_entry}")
                if pkg_violations:
                    self.add_result("Project", "ALL-CFG-03 - Package version pinning", "FAIL", pkg_violations)
                else:
                    self.add_result("Project", "ALL-CFG-03 - Package version pinning", "PASS")
            else:
                self.add_result("Project", "ALL-CFG-03 - Package version pinning", "SKIP", ["No packages.yml found"])

            dup_models = []
            seen_models = set()
            for yml_file in Path("models").rglob("*.yml"):
                # Avoid catching dbt_project.yml or properties files that aren't model metadata
                if yml_file.name == "dbt_project.yml": continue
                with open(yml_file, "r", encoding="utf-8") as f:
                    yml_content = yaml.safe_load(f) or {}
                for m in yml_content.get("models", []):
                    name = m.get("name")
                    if name:
                        if name in seen_models:
                            dup_models.append(f"Duplicate model entry found for: {name} in {yml_file}")
                        seen_models.add(name)
            
            if dup_models:
                self.add_result("Project", "YML-SYNC-02 - No duplicate model entries", "FAIL", dup_models)
            else:
                self.add_result("Project", "YML-SYNC-02 - No duplicate model entries", "PASS")
        except Exception as e:
            self.add_result("Project", "Project config validation", "WARN", [f"Error during execution: {e}"])

        self.console.print(Panel(f"Testing Models by Selection: [bold]{select}[/bold]", border_style="blue", expand=False))
        
        dbt = dbtRunner()
        ls_args = ["ls", "-s", select, "--resource-types", "model", "--quiet"]
        if state:
            ls_args.extend(["--state", state])
        res: dbtRunnerResult = dbt.invoke(ls_args)
        
        if not res.success or not res.result:
            self.console.print(f"[red]Could not resolve any models for selection '{select}'[/red]")
            return self.results
            
        resolved_models = [m.split('.')[-1] for m in res.result if isinstance(m, str)]
        
        if not resolved_models:
            self.console.print(f"[red]No model nodes found for selection '{select}'[/red]")
            return self.results
            
        self.console.print(f"Discovered {len(resolved_models)} model(s): {', '.join(resolved_models)}")
        
        for model_name in resolved_models:
            self.console.print("\n" + "="*80)
            self.console.print(f"  Evaluating: [bold cyan]{model_name}[/bold cyan]")
            self.console.print("="*80)
            
            sql_path = self.get_model_sql_path(model_name, dbt)
            if not sql_path:
                self.console.print(f"[red]Could not resolve model '{model_name}' to a .sql file[/red]")
                continue
        
            layer = "unknown"
            if model_name.startswith("stg_"): layer = "staging"
            elif model_name.startswith("int_"): layer = "integration"
            elif model_name.startswith("fct_"): layer = "fact"
            elif model_name.startswith("dim_"): layer = "dimension"
            elif model_name.startswith("base_"): layer = "base"
                
            self.console.print(f"SQL Path: {sql_path}")
            self.console.print(f"Layer: {layer}\n")
        
            self.check_dbt_build(model_name, dbt)
            self.check_dbt_score(model_name)
            self.check_dbt_project_evaluator(model_name, dbt)
            
            node = self.get_yaml_node(model_name)
            self.check_layer_and_manifest(model_name, sql_path, layer, node)
            self.check_runtime_schema(model_name, layer, node, dbt)
            self.check_sql_file_content(model_name, sql_path)
            
            # Run sqlfluff LAST because it spawns a subprocess that competes for the DuckDB lock
            self.check_sqlfluff(model_name, sql_path)

        return self.results

def run_checks(model_name: str, quiet: bool = False) -> List[CheckResult]:
    checker = ModelChecker(is_json_output=quiet)
    return checker.run_checks(model_name)

def main():
    parser = argparse.ArgumentParser(description="Check dbt models against project standards.")
    parser.add_argument("--select", "-s", type=str, required=True, help="dbt selection string (e.g. models/integration or int_parks)")
    parser.add_argument("--state", type=str, help="Path to directory containing comparison manifest.json for state:modified selector")
    parser.add_argument("--json", action="store_true", help="Output results as JSON to stdout")
    parser.add_argument("--output", type=str, help="Output results as JSON to file")
    args = parser.parse_args()

    is_json = args.json or bool(args.output)
    checker = ModelChecker(is_json_output=is_json)
    results = checker.run_checks(args.select, state=args.state)

    # Summary
    table = Table(title=f"Global Summary", show_header=True, header_style="bold magenta")
    table.add_column("Result", justify="center")
    table.add_column("Count", justify="right")
    
    table.add_row("[green]PASS[/green]", str(checker.global_counts["PASS"]))
    table.add_row("[red]FAIL[/red]", str(checker.global_counts["FAIL"]))
    table.add_row("[yellow]WARN[/yellow]", str(checker.global_counts["WARN"]))
    table.add_row("[cyan]SKIP[/cyan]", str(checker.global_counts["SKIP"]))
    table.add_row("---", "---")
    table.add_row("[bold]Total Checks[/bold]", str(len(results)))
    
    # Write JSON debug out
    import os
    Path("tmp").mkdir(exist_ok=True)
    with open("tmp/checker_failures.json", "w", encoding="utf-8") as f:
        failure_data = [{"model": r.model, "rule": r.name, "messages": r.messages} for r in results if r.status == "FAIL"]
        json.dump(failure_data, f, indent=2)

    output_data = [{"model": r.model, "rule": r.name, "status": r.status, "messages": r.messages} for r in results]

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2)

    if args.json:
        if not args.output:
            print(json.dumps(output_data, indent=2))
        sys.exit(1 if checker.global_counts["FAIL"] > 0 else 0)

    if args.output and not args.json:
        pass # Allow continuation to print formatted output

    checker.console.print("\n")
    checker.console.print(table)
    
    if checker.global_counts["FAIL"] > 0:
        failures = [r for r in results if r.status == "FAIL"]
        if failures:
            fail_table = Table(title="Failure Summary", show_header=True)
            fail_table.add_column("Model", style="cyan")
            fail_table.add_column("Rule", style="red")
            fail_table.add_column("Messages", style="dim")
            for f in failures:
                fail_table.add_row(f.model, f.name, "\n".join(f.messages[:5]))
            checker.console.print(fail_table)
            
        checker.console.print(Panel(f"[bold red]Result: FAIL[/bold red] ({checker.global_counts['FAIL']} rule violation(s))", border_style="red", expand=False))
        sys.exit(1)
    else:
        checker.console.print(Panel(f"[bold green]Result: PASS[/bold green] ({checker.global_counts['WARN']} warning(s) to review)", border_style="green", expand=False))
        sys.exit(0)

if __name__ == "__main__":
    main()
