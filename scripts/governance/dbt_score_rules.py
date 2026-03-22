import re
import os
from dbt_score import Model, RuleViolation, rule

FLAGS_REGEX = re.compile(
    r'\b(unique|not_null|fan\.out|deduplication|protecting against|tests verify|collision|ensures that|guards against)\b',
    re.IGNORECASE
)

@rule
def no_test_rationale_in_description(model: Model) -> RuleViolation | None:
    """Descriptions should not contain test rationale or red-flag words (ALL-TST-02)."""
    red_flags_found = []

    if model.description and FLAGS_REGEX.search(model.description):
        match = FLAGS_REGEX.search(model.description)
        red_flags_found.append(f"model desc: {match.group(0)}")

    columns = getattr(model, "columns", {})
    columns_list = columns.values() if isinstance(columns, dict) else columns

    for col in columns_list:
        if col.description and FLAGS_REGEX.search(col.description):
            match = FLAGS_REGEX.search(col.description)
            red_flags_found.append(f"{col.name}: {match.group(0)}")

    if red_flags_found:
        return RuleViolation(message=f"ALL-TST-02 - test rationale in description: {', '.join(red_flags_found)}")

@rule
def mart_contract_enforced(model: Model) -> RuleViolation | None:
    """Fact and dimension models must have contracts enforced (MRT-YML-04)."""
    if model.name.startswith("fct_") or model.name.startswith("dim_"):
        contract = getattr(model.config, "contract", {})
        enforced = False
        if isinstance(contract, dict):
            enforced = contract.get("enforced")
        elif hasattr(contract, "enforced"):
            enforced = contract.enforced

        if not enforced:
            return RuleViolation(message="MRT-YML-04 - mart needs contract: { enforced: true }")

@rule
def mart_columns_have_data_type(model: Model) -> RuleViolation | None:
    """Mart models must have data_type on all columns (MRT-YML-05)."""
    if model.name.startswith("fct_") or model.name.startswith("dim_"):
        columns = getattr(model, "columns", {})
        columns_list = columns.values() if isinstance(columns, dict) else columns
        
        total_cols = len(columns_list)
        if total_cols == 0:
            return None
        
        typed_cols = sum(1 for col in columns_list if getattr(col, "data_type", None))
        
        if typed_cols < total_cols:
            return RuleViolation(message=f"MRT-YML-05 - {typed_cols}/{total_cols} columns have data_type")

@rule
def no_per_model_yaml(model: Model) -> RuleViolation | None:
    """Models should not use per-model YAML files (YML-02)."""
    patch_path = getattr(model, "patch_path", None)
    if patch_path:
        # patch_path format e.g. "project_name://models/.../file.yml"
        filename = getattr(model, "patch_path", "").split("://")[-1]
        basename = os.path.basename(filename)
        # Often models shouldn't be configured in a file named exactly after them 
        if basename == f"{model.name}.yml":
            return RuleViolation(message=f"YML-02 - per-model YAML file '{basename}' not permitted. Use _models.yml")
