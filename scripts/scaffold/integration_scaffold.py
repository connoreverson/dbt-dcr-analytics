# scripts/scaffold/integration_scaffold.py
"""Generate integration model SQL + YAML skeleton."""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def _sk_name(model_name: str) -> str:
    """Derive surrogate key column name from model name (int_parks -> parks_sk)."""
    entity = model_name.removeprefix("int_")
    return f"{entity}_sk"


def generate_integration_sql(
    model_name: str,
    entity: str,
    sources: list[str],
    key_column: str,
) -> str:
    """Generate integration model SQL with CTE-per-source and surrogate key."""
    sk = _sk_name(model_name)
    lines = [f"-- Integration model: {model_name}"]
    lines.append(f"-- CDM entity: {entity}")
    lines.append(f"-- Grain: one row per {entity.lower()}")
    lines.append("")
    lines.append("with")
    lines.append("")

    cte_names = []
    for source in sources:
        cte_name = source.split("__")[-1] if "__" in source else source.removeprefix("stg_")
        cte_names.append(cte_name)
        lines.append(f"{cte_name} as (")
        lines.append("    select")
        lines.append(f"        {key_column},")
        lines.append("        -- TODO: map source columns to CDM entity columns")
        lines.append(f"        '{source}' as _source_model")
        lines.append(f"    from {{{{ ref('{source}') }}}}")
        lines.append("),")
        lines.append("")

    if len(sources) > 1:
        lines.append("unioned as (")
        for i, cte_name in enumerate(cte_names):
            if i > 0:
                lines.append("    union all")
            lines.append(f"    select * from {cte_name}")
        lines.append("),")
        lines.append("")
        final_cte = "unioned"
    else:
        final_cte = cte_names[0]

    lines.append("final as (")
    lines.append("    select")
    lines.append(
        f"        {{{{ dbt_utils.generate_surrogate_key(['{key_column}', '_source_model']) }}}} as {sk},"
    )
    lines.append("        *")
    lines.append(f"    from {final_cte}")
    lines.append(")")
    lines.append("")
    lines.append("select * from final")
    lines.append("")

    return "\n".join(lines)


def generate_integration_yaml(
    model_name: str,
    entity: str,
    grain: str,
    key_column: str,
) -> str:
    """Generate YAML properties for the integration model."""
    sk = _sk_name(model_name)

    return f"""  - name: {model_name}
    description: >
      {entity} integration model. {grain}.
    meta:
      cdm_entity: {entity}
      intake_completed: true
      grain: "{grain}"
    columns:
      - name: {sk}
        description: "Surrogate key for {entity.lower()} entity"
        tests:
          - unique
          - not_null
      - name: {key_column}
        description: "Natural key from source system"
        tests:
          - not_null
"""


def run_integration_scaffold(
    entity: str,
    sources: list[str],
    key_column: str,
) -> int:
    """Generate and output integration model files.

    Args:
        entity: CDM entity name (e.g., "Grant").
        sources: List of staging model names to consume.
        key_column: Natural key column name.

    Returns:
        Exit code (0 for success).
    """
    model_name = f"int_{entity.lower()}s"
    sql = generate_integration_sql(model_name, entity, sources, key_column)
    yaml_str = generate_integration_yaml(
        model_name, entity, f"one row per {entity.lower()}", key_column
    )

    out_dir = Path("tmp/scaffold")
    out_dir.mkdir(parents=True, exist_ok=True)

    sql_path = out_dir / f"{model_name}.sql"
    sql_path.write_text(sql, encoding="utf-8")

    yaml_path = out_dir / f"{model_name}.yml"
    yaml_path.write_text(yaml_str, encoding="utf-8")

    print(f"Generated: {sql_path}")
    print(f"Generated: {yaml_path}")
    return 0
