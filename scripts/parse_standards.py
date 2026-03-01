import re
import json
from pathlib import Path

def parse_standards():
    standards_path = Path("reference/dbt_project_standards.md")
    if not standards_path.exists():
        print("Could not find reference/dbt_project_standards.md")
        return

    with open(standards_path, "r", encoding="utf-8") as f:
        content = f.read()

    rules = []
    
    # regex to match rules
    rule_pattern = re.compile(
        r'#### \*\*Rule: ([A-Z0-9-]+) (.*?)\*\* \[(Automated|Manual)\]\n(.*?(?=#### \*\*Rule: |^### |^## |\Z))',
        re.MULTILINE | re.DOTALL
    )

    for match in rule_pattern.finditer(content):
        rule_id = match.group(1).strip()
        title = match.group(2).strip()
        tag = match.group(3).strip()
        description = match.group(4).strip()
        
        is_automated = tag == "Automated"
        
        # determine layer
        layer = "all"
        if rule_id.startswith("SQL-STG"):
            layer = "staging"
        elif rule_id.startswith("SQL-INT"):
            layer = "integration"
        elif rule_id.startswith("SQL-BASE"):
            layer = "base"
        elif rule_id.startswith("SQL-FCT") or rule_id.startswith("SQL-DIM"):
            layer = "marts"

        rules.append({
            "id": rule_id,
            "title": title,
            "is_automated": is_automated,
            "layer": layer,
            "description": description
        })

    with open("reference/dbt_project_standards.json", "w", encoding="utf-8") as f:
        json.dump(rules, f, indent=2)
    
    print(f"Parsed {len(rules)} rules into reference/dbt_project_standards.json")

if __name__ == "__main__":
    parse_standards()
