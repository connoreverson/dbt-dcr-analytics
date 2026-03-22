# scripts/scaffold/mart_scaffold.py
"""Generate fact, dimension, and report model skeletons."""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def _dim_sk(dim_name: str) -> str:
    """Derive FK column name from dimension name (dim_parks -> parks_sk)."""
    entity = dim_name.removeprefix("dim_")
    return f"{entity}_sk"


def generate_fact_sql(
    name: str,
    grain: str,
    dimensions: list[str],
    measures: list[str],
) -> str:
    """Generate fact model SQL skeleton."""
    lines = [
        f"-- Fact model: {name}",
        f"-- Grain: {grain}",
        f"-- Descriptive attributes come from dimensions, not from this table.",
        "",
        "with",
        "",
    ]

    # Source CTE placeholder
    lines.append("source as (")
    lines.append("    select")
    lines.append("        -- TODO: select from integration model(s)")
    lines.append("        *")
    lines.append("    from {{ ref('TODO_integration_model') }}")
    lines.append("),")
    lines.append("")

    # Final select with dimension FKs and measures only
    lines.append("final as (")
    lines.append("    select")

    # Dimension FK columns
    for dim in dimensions:
        if dim == "dim_date":
            lines.append("        date_key,")
        else:
            lines.append(f"        {_dim_sk(dim)},")

    # Measures
    for measure in measures:
        lines.append(f"        {measure},")

    lines.append("        -- TODO: add remaining measures")
    lines.append("    from source")

    # Dimension joins
    for dim in dimensions:
        if dim == "dim_date":
            lines.append(f"    -- TODO: join to {{{{ ref('{dim}') }}}} on date_key")
        else:
            lines.append(f"    -- TODO: join to {{{{ ref('{dim}') }}}} on {_dim_sk(dim)}")

    lines.append(")")
    lines.append("")
    lines.append("select * from final")
    lines.append("")

    return "\n".join(lines)


def generate_dimension_sql(
    name: str,
    grain: str,
    key: str,
) -> str:
    """Generate dimension model SQL skeleton."""
    sk = name.removeprefix("dim_") + "_sk"

    return f"""-- Dimension model: {name}
-- Grain: {grain}

with

source as (
    select
        -- TODO: select from integration model
        *
    from {{{{ ref('TODO_integration_model') }}}}
),

final as (
    select
        {{{{ dbt_utils.generate_surrogate_key(['{key}']) }}}} as {sk},
        {key},
        -- TODO: add descriptive attributes
        -- TODO: add derived classifications (e.g., CASE WHEN ... END as size_tier)
    from source
)

select * from final
"""


def generate_report_sql(
    name: str,
    facts: list[str],
    grain: str,
) -> str:
    """Generate report model SQL skeleton."""
    lines = [
        f"-- Report model: {name}",
        f"-- Grain: {grain}",
        f"-- This report combines {len(facts)} fact table(s) at the {grain} grain.",
        f"-- If consuming a single fact without aggregation, consider connecting",
        f"-- your BI tool directly.",
        "",
        "with",
        "",
    ]

    # One CTE per fact with aggregation
    for fact in facts:
        cte_name = fact.removeprefix("fct_")
        lines.append(f"{cte_name} as (")
        lines.append("    select")
        lines.append(f"        -- TODO: group by columns for {grain} grain")
        lines.append("        -- TODO: aggregate measures (sum, count, avg)")
        lines.append(f"    from {{{{ ref('{fact}') }}}}")
        lines.append("    group by")
        lines.append("        -- TODO: group by keys")
        lines.append("        1")
        lines.append("),")
        lines.append("")

    # Final join
    cte_names = [f.removeprefix("fct_") for f in facts]
    lines.append("final as (")
    lines.append("    select *")
    lines.append(f"    from {cte_names[0]}")
    for cte in cte_names[1:]:
        lines.append(f"    -- TODO: join {cte} on shared grain columns")
        lines.append(f"    left join {cte} using (/* TODO: grain columns */)")
    lines.append(")")
    lines.append("")
    lines.append("select * from final")
    lines.append("")

    return "\n".join(lines)


def generate_mart_yaml(name: str, grain: str, model_type: str) -> str:
    """Generate YAML properties for a mart model."""
    sk = name.removeprefix("fct_").removeprefix("dim_").removeprefix("rpt_") + "_sk"
    return f"""  - name: {name}
    description: >
      {model_type.title()} model. {grain}.
    meta:
      model_type: {model_type}
      grain: "{grain}"
      intake_completed: true
    columns:
      - name: {sk}
        description: "Surrogate key"
        tests:
          - unique
          - not_null
"""


def run_mart_scaffold(args: argparse.Namespace) -> int:
    """Generate mart model SQL + YAML skeleton based on subcommand."""
    out_dir = Path("tmp/scaffold")
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.subcommand == "fact":
        measures = list(args.measures) if args.measures else []
        sql = generate_fact_sql(args.name, args.grain, args.dimensions, measures)
        yaml_str = generate_mart_yaml(args.name, args.grain, "fact")
    elif args.subcommand == "dimension":
        sql = generate_dimension_sql(args.name, args.grain, args.key)
        yaml_str = generate_mart_yaml(args.name, args.grain, "dimension")
    elif args.subcommand == "report":
        sql = generate_report_sql(args.name, args.facts, args.grain)
        yaml_str = generate_mart_yaml(args.name, args.grain, "report")
    else:
        return 1

    sql_path = out_dir / f"{args.name}.sql"
    sql_path.write_text(sql, encoding="utf-8")
    print(f"Generated SQL: {sql_path}")

    yaml_path = out_dir / f"{args.name}.yml"
    yaml_path.write_text(yaml_str, encoding="utf-8")
    print(f"Generated YAML: {yaml_path}")
    return 0
