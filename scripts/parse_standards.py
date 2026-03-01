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
    
    # regex to match rules at both #### and ##### heading depths
    # tag is optional; missing tag defaults to is_automated = False
    rule_pattern = re.compile(
        r'^(#{4,5}) \*\*Rule: ([A-Z0-9-]+) (.*?)\*\*(?:\s*\[(Automated|Manual)\])?\n(.*?(?=^#{4,5} \*\*Rule: |^### |^## |\Z))',
        re.MULTILINE | re.DOTALL
    )

    for match in rule_pattern.finditer(content):
        rule_id = match.group(2).strip()
        title = match.group(3).strip()
        tag = match.group(4)
        description = match.group(5).strip()

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
        elif rule_id.startswith("SQL-RPT"):
            layer = "marts"
        elif rule_id.startswith("SQL-MAC"):
            layer = "macros"
        elif rule_id.startswith("SQL-TST"):
            layer = "tests"
        elif rule_id.startswith("SQL-SEED"):
            layer = "seeds"
        elif rule_id.startswith("SQL-SNAP"):
            layer = "snapshots"
        elif rule_id.startswith("SQL-ANL"):
            layer = "analyses"
        elif rule_id.startswith("SQL-HOOK"):
            layer = "hooks"
        elif rule_id.startswith("SRC-YML") or rule_id.startswith("STG-YML"):
            layer = "staging"
        elif rule_id.startswith("INT-YML"):
            layer = "integration"
        elif rule_id.startswith("MRT-YML"):
            layer = "marts"
        elif rule_id.startswith("MAC-YML") or rule_id.startswith("DOC-YML"):
            layer = "macros"

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
