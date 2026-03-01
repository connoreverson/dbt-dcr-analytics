import sys
import os
import argparse
import json
import subprocess
from pathlib import Path

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

def run_automated_checks(model_name):
    print(f"Running automated checks for {model_name}...")
    env = os.environ.copy()
    try:
        result = subprocess.run(
            ["python", "scripts/check_model.py", "--select", model_name, "--json"],
            capture_output=True,
            text=True,
            env=env
        )
        if not result.stdout.strip():
            print("No JSON output from check_model.py.")
            return []
        
        # Output could contain some other noise before the JSON array, let's find the array
        stdout = result.stdout
        json_start = stdout.find('[')
        if json_start != -1:
            try:
                return json.loads(stdout[json_start:])
            except json.JSONDecodeError:
                pass
        print("Failed to decode check_model.py JSON output.")
        return []
    except Exception as e:
        print(f"Error running check_model.py: {e}")
        return []

def main():
    parser = argparse.ArgumentParser(description="Interactive review of a dbt model against qualitative standards.")
    parser.add_argument("--select", "-s", type=str, required=True, help="dbt model name (e.g. int_parks)")
    parser.add_argument("--agent", action="store_true", help="Agent mode: generate a markdown template instead of interactive prompt")
    args = parser.parse_args()
    
    model_name = args.select
    
    # Run automated checks
    auto_results = run_automated_checks(model_name)
    fails = [r for r in auto_results if r.get("status") == "FAIL"]
    
    if fails:
        print(f"\n[!] WARNING: {model_name} failed {len(fails)} automated checks.")
        for f in fails:
            print(f"  - {f['rule']}")
        print("You should probably fix these before qualitative review.\n")
    else:
        print(f"\n[+] {model_name} passed all automated checks.\n")
        
    # Load standards
    standards_path = Path("reference/dbt_project_standards.json")
    if not standards_path.exists():
        print(f"Standards JSON not found at {standards_path}. Run python scripts/parse_standards.py first.")
        sys.exit(1)
        
    with open(standards_path, "r", encoding="utf-8") as f:
        rules = json.load(f)
        
    layer = get_layer(model_name)
    manual_rules = [r for r in rules if not r.get("is_automated") and r.get("layer") in ["all", layer]]
    
    if not manual_rules:
        print(f"No manual rules found for layer: {layer}.")
        sys.exit(0)
        
    if args.agent:
        # Agent mode: generate template
        template_lines = [f"# Qualitative Review Template for {model_name}"]
        template_lines.append(f"Model Layer: {layer}\n")
        template_lines.append("Instructions: For each rule below, mark PASS or FAIL and provide a brief rationale.\n")
        
        for rule in manual_rules:
            template_lines.append(f"## {rule['id']} - {rule['title']}")
            template_lines.append(f"Result: [ ] PASS / [ ] FAIL")
            template_lines.append(f"Rationale: \n\n")
            
        out_path = Path(f"tmp/review_{model_name}.md")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(template_lines))
            
        print(f"\n[Agent Mode] Template generated at {out_path}.")
        print("Please read the template, fill it out, and save it.")
        print("Refer to reference/dbt_project_standards.json for full rule descriptions if needed.")
        sys.exit(0)
        
    # Human mode
    if questionary is None:
        print("The 'questionary' package is required for interactive mode. Please 'pip install questionary' or use --agent.")
        sys.exit(1)
        
    print(f"Starting interactive review for {model_name} ({layer} layer)...\n")
    
    review_results = []
    
    for rule in manual_rules:
        print("-" * 80)
        print(f"Rule: {rule['id']} - {rule['title']}")
        print(f"Description:\n{rule['description']}\n")
        
        status = questionary.select(
            "Evaluation:",
            choices=["PASS", "FAIL", "SKIP (Not Applicable)"]
        ).ask()
        
        if status is None:
            print("Review aborted.")
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
            
    print(f"\nReview complete. Summary saved to {summary_path}")

if __name__ == "__main__":
    main()
