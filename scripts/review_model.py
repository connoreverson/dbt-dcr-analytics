import warnings
warnings.warn(
    "scripts/review_model.py is deprecated. Use: python -m scripts.reviewer --select <model>",
    DeprecationWarning,
    stacklevel=2,
)

import sys
import os
import argparse
import json
import shutil
import subprocess
from pathlib import Path

# Add project root to path so we can import from scripts
sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.check_model import run_checks

from rich.console import Console
from rich.panel import Panel

console = Console()

try:
    import questionary
except ImportError:
    questionary = None

def get_layer(model_name):
    if model_name.startswith("stg_"): return "staging"
    if model_name.startswith("int_"): return "integration"
    if model_name.startswith("fct_") or model_name.startswith("dim_"): return "marts"
    if model_name.startswith("base_"): return "base"
    return "unknown"

def run_automated_checks(model_name, is_agent=False):
    console.print(f"\n[dim]Running automated checks for {model_name}...[/dim]")
    try:
        if is_agent:
            # dbtRunner.invoke() writes directly to stdout regardless of rich's quiet flag.
            # Redirect stdout to suppress the noise when running non-interactively.
            with open(os.devnull, "w") as devnull:
                old_stdout, sys.stdout = sys.stdout, devnull
                try:
                    results = run_checks(model_name, quiet=True)
                finally:
                    sys.stdout = old_stdout
        else:
            results = run_checks(model_name, quiet=False)
        # Convert CheckResult objects into the dict format
        return [{"rule": r.name, "status": r.status, "messages": r.messages} for r in results]
    except Exception as e:
        console.print(f"[red]Error running check_model for {model_name}: {e}[/red]")
        return []

def get_model_metadata(model_name):
    """Returns (sql_content, yaml_content, sql_path, yaml_path) for a model."""
    manifest_path = Path("target/manifest.json")
    sql_content = "SQL content not found."
    yaml_content = "YAML content not found."
    sql_path = None
    yaml_path = None
    
    if manifest_path.exists():
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
            
        node = None
        for k, v in manifest.get("nodes", {}).items():
            if v.get("name") == model_name and v.get("resource_type") == "model":
                node = v
                break
                
        if node:
            # Get SQL
            sql_path = node.get("original_file_path")
            if sql_path and os.path.exists(sql_path):
                with open(sql_path, "r", encoding="utf-8") as f:
                    sql_content = f.read()
                    
            # Get YAML block and supplemental YAMLs
            patch_path = node.get("patch_path")
            
            # --- Expanded YAML Context Gathering ---
            yaml_parts = []
            
            # 1. Get the primary model YAML
            if patch_path:
                yaml_file_path = patch_path.split("://")[-1]
                yaml_path = yaml_file_path
                if os.path.exists(yaml_file_path):
                     try:
                         with open(yaml_file_path, "r", encoding="utf-8") as f:
                             yaml_parts.append(f"# {yaml_file_path}\n" + f.read())
                     except Exception as e:
                         yaml_parts.append(f"# Error reading {yaml_file_path}: {e}")
            
            # 2. Get local _sources.yml if it exists
            if sql_path:
                model_dir = Path(sql_path).parent
                source_yaml = model_dir / "_sources.yml"
                if source_yaml.exists():
                    try:
                        with open(source_yaml, "r", encoding="utf-8") as f:
                            yaml_parts.append(f"# {source_yaml}\n" + f.read())
                    except Exception as e:
                        pass
            
            # 3. Get generic macro / seed context (if relevant to the project structure)
            # Find any _seeds.yml or _macros.yml near the root directories
            for supplemental_file in ["seeds/_seeds.yml", "macros/_macros.yml"]:
                supp_path = Path(supplemental_file)
                if supp_path.exists():
                    try:
                        with open(supp_path, "r", encoding="utf-8") as f:
                            yaml_parts.append(f"# {supp_path}\n" + f.read())
                    except Exception:
                        pass
                        
            if yaml_parts:
                yaml_content = "\n\n".join(yaml_parts)
            else:
                yaml_content = "YAML content not found."
                        
    return sql_content, yaml_content, sql_path, yaml_path

def process_model(model_name, args, rules):
    console.print()
    console.print(Panel(f"Evaluating Model: [bold cyan]{model_name}[/bold cyan]", border_style="blue", expand=False))

    # Run automated checks for context
    auto_results = run_automated_checks(model_name, is_agent=args.agent or args.export_yaml)
    fails = [r for r in auto_results if r.get("status") == "FAIL"]

    if fails:
        console.print(f"\n[yellow]![/yellow] [bold]{model_name}[/bold] failed [red]{len(fails)}[/red] automated check(s).")
        for f_item in fails:
            console.print(f"\n  [red]✗[/red] {f_item['rule']}")
            for msg in f_item.get('messages', [])[:5]:
                console.print(f"      [dim]{msg}[/dim]")
            if len(f_item.get('messages', [])) > 5:
                console.print(f"      [dim]... and {len(f_item.get('messages', [])) - 5} more lines[/dim]")
        console.print("\n[yellow]Fix these before qualitative review.[/yellow]\n")
    else:
        console.print(f"\n[green]✓[/green] {model_name} passed all automated checks.\n")

    layer = get_layer(model_name)
    manual_rules = [r for r in rules if not r.get("is_automated") and r.get("layer") in ["all", layer]]

    if not manual_rules:
        console.print(f"[dim]No manual rules found for layer: {layer}.[/dim]")
        return

    console.print(f"[bold]{len(manual_rules)}[/bold] manual rules to evaluate.\n")
        
    if args.export_yaml:
        # Export mode: generate a single YAML review file per model
        try:
            import yaml
        except ImportError:
            console.print(f"[red]The 'pyyaml' package is required for YAML export. Please 'pip install pyyaml'.[/red]")
            return
            
        # Setup a custom representer for multiline block scalars (|)
        class LiteralStr(str):
            pass
            
        def literal_presenter(dumper, data):
            if '\n' in data:
                return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
            return dumper.represent_scalar('tag:yaml.org,2002:str', data)
            
        yaml.add_representer(LiteralStr, literal_presenter)
        
        sql_content, yaml_content, sql_path, yaml_path = get_model_metadata(model_name)
        reviews_dir = Path(args.reviews_dir) if args.reviews_dir else Path("tmp/reviews")
        reviews_dir.mkdir(parents=True, exist_ok=True)
        
        # Build context block
        context = {
            "sql_path": sql_path or "Path not found",
            "yaml_path": yaml_path or "Path not found"
        }
        if args.inline:
            context["sql"] = LiteralStr(sql_content) if sql_content else ""
            context["yaml"] = LiteralStr(yaml_content) if yaml_content else ""
        
        # Build rules list with empty evaluation slots
        rules_list = []
        for rule in manual_rules:
            desc = rule.get('description', '')
            rule_entry = {
                "id": rule['id'],
                "title": rule['title'],
                "description": LiteralStr(desc) if '\n' in desc else desc,
                "evaluation": {
                    "status": "",
                    "rationale": "",
                    "evidence": [
                        {"file": "", "start_line": None, "end_line": None}
                    ]
                }
            }
            rules_list.append(rule_entry)
        
        review_doc = {
            "model": model_name,
            "layer": layer,
            "context": context,
            "instructions": LiteralStr(
                "SCOPE: Read ONLY the two files listed in context (sql_path and yaml_path). "
                "Do NOT read other project files, search the codebase, run commands, or consult external references. "
                "Evaluate each rule based solely on what is visible in those two files.\n\n"
                "TASK: For each rule below, fill in the evaluation fields:\n"
                "  - status: PASS, FAIL, or SKIP (use SKIP only if the rule is structurally inapplicable)\n"
                "  - rationale: 1-2 sentences explaining your judgment\n"
                "  - evidence: cite the file path and start_line/end_line of the relevant code. "
                "Add multiple evidence entries if the rule applies to more than one location.\n\n"
                "SAVE this file in place when complete. Do not create other files or reports."
            ),
            "rules": rules_list
        }
        
        out_path = reviews_dir / f"{model_name}.yml"
        with open(out_path, "w", encoding="utf-8") as f:
            yaml.dump(review_doc, f, sort_keys=False, allow_unicode=True)
                
        console.print(f"[green]✓[/green] Review file exported to [bold]{out_path}[/bold]")
        return

    if args.agent:
        # Agent mode: generate markdown template
        sql_content, yaml_content, _, _ = get_model_metadata(model_name)
        
        template_lines = [f"# Qualitative Review Template for {model_name}"]
        template_lines.append(f"Model Layer: {layer}\n")
        
        template_lines.append("## Setup Data\n")
        template_lines.append("### Model SQL\n```sql\n" + sql_content.strip() + "\n```\n")
        template_lines.append("### Model YAML\n```yaml\n" + yaml_content.strip() + "\n```\n")
        
        template_lines.append("Instructions: For each rule below, mark PASS or FAIL and provide a brief rationale.\n")
        
        for rule in manual_rules:
            template_lines.append(f"## {rule['id']} - {rule['title']}")
            if rule.get('description'):
                template_lines.append(f"**Description:**\n{rule['description']}\n")
            template_lines.append(f"Result: [ ] PASS / [ ] FAIL / [ ] SKIP")
            template_lines.append(f"Rationale: \n\n")
            
        out_path = Path(f"tmp/review_{model_name}.md")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(template_lines))
            
        console.print(f"\n[green]✓[/green] [bold]Agent mode:[/bold] Template generated at [bold]{out_path}[/bold].")
        return
        
    # Human mode
    if questionary is None:
        console.print("[red]The 'questionary' package is required for interactive mode. Please 'pip install questionary', or use --agent or --export-yaml.[/red]")
        sys.exit(1)

    console.print(f"Starting interactive review for [bold cyan]{model_name}[/bold cyan] ([dim]{layer}[/dim] layer)...\n")
    
    review_results = []
    
    total_rules = len(manual_rules)
    for i, rule in enumerate(manual_rules, 1):
        console.print("-" * 80)
        console.print(f"Rule [bold]{i}[/bold] of {total_rules}: [cyan]{rule['id']}[/cyan] - {rule['title']}")
        console.print(f"[dim]{rule['description']}[/dim]\n")
        
        status = questionary.select(
            "Evaluation:",
            choices=["PASS", "FAIL", "SKIP (Not Applicable)"]
        ).ask()
        
        if status is None:
            console.print("[red]Review aborted.[/red]")
            sys.exit(1)
            
        rationale = ""
        if status != "SKIP (Not Applicable)":
            rationale = questionary.text("Rationale/Notes (optional):").ask()
            
        review_results.append({
            "rule": rule['id'],
            "title": rule['title'],
            "status": status.split()[0], # PASS, FAIL, SKIP
            "rationale": rationale
        })
        
    # Save summary
    summary_path = Path(f"tmp/human_review_{model_name}.md")
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(f"# Review Summary: {model_name}\n\n")
        for r in review_results:
            f.write(f"### {r['rule']} - {r['title']}\n")
            f.write(f"**Result:** {r['status']}\n")
            if r['rationale']:
                f.write(f"**Rationale:** {r['rationale']}\n")
            f.write("\n")
            
    console.print(Panel(f"[bold green]Review complete.[/bold green] Summary saved to [bold]{summary_path}[/bold]", border_style="green", expand=False))

def main():
    parser = argparse.ArgumentParser(description="Qualitative review of dbt models against project standards.")
    parser.add_argument("--select", "-s", type=str, required=True, help="dbt selection string (e.g. models/integration or int_parks)")
    parser.add_argument("--agent", action="store_true", help="Agent mode: generate a markdown template instead of interactive prompt")
    parser.add_argument("--export-yaml", action="store_true", help="Export a single YAML review file per model for LLM evaluation")
    parser.add_argument("--inline", action="store_true", help="When used with --export-yaml, embed full SQL and YAML content inline")
    parser.add_argument("--reviews-dir", type=str, help="Output directory for review files (default: tmp/reviews)", default=None)
    args = parser.parse_args()
    
    # Load standards once
    standards_path = Path("reference/dbt_project_standards.json")
    if not standards_path.exists():
        console.print(f"[red]Standards JSON not found at {standards_path}. Run python scripts/parse_standards.py first.[/red]")
        sys.exit(1)
        
    with open(standards_path, "r", encoding="utf-8") as f:
        rules = json.load(f)

    console.print(f"Resolving model selection: [bold]{args.select}[/bold] (excluding packages)...")
    # dbtRunner.invoke("ls") in dbt-core 1.9.x prints to stdout but returns res.result=[].
    # Use subprocess to capture the output reliably.
    dbt_exe = shutil.which("dbt") or "dbt"
    completed = subprocess.run(
        [dbt_exe, "ls", "-s", args.select, "--resource-types", "model"],
        capture_output=True, text=True
    )
    # Strip ANSI codes, keep only lines that look like dbt node names (contain a dot)
    import re
    ansi_escape = re.compile(r"\x1b\[[0-9;]*m")
    raw_lines = [ansi_escape.sub("", l).strip() for l in completed.stdout.splitlines()]
    resolved_models = [m.split(".")[-1] for m in raw_lines if "." in m and not m.startswith("2")]
    
    if not resolved_models:
        console.print(f"[red]No model nodes found for selection '{args.select}'[/red]")
        sys.exit(1)

    console.print(f"Discovered [bold]{len(resolved_models)}[/bold] model(s): [cyan]{', '.join(resolved_models)}[/cyan]")

    for model_name in resolved_models:
        process_model(model_name, args, rules)

if __name__ == "__main__":
    main()
