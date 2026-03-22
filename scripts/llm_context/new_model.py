# scripts/llm_context/new_model.py
"""Guided intake questionnaire for new dbt models.

Uses questionary for interactive prompts. Branches by layer
(staging/integration/mart) and guides entity-first modeling.
"""
from __future__ import annotations

import datetime
import logging
import sys
from typing import Any

logger = logging.getLogger(__name__)


def classify_entity_behavior(behavior: str) -> str:
    """Map entity behavior description to likely model type.

    Args:
        behavior: A description of how the entity behaves over time.

    Returns:
        "dimension", "fact", or "unknown".
    """
    behavior_lower = behavior.lower()
    if "static" in behavior_lower or "lifecycle" in behavior_lower:
        return "dimension"
    if "event" in behavior_lower or "transaction" in behavior_lower or "measurement" in behavior_lower:
        return "fact"
    return "unknown"


def build_intake_meta(
    grain: str,
    model_type: str,
    entity: str = "",
    cdm_entity: str = "",
) -> dict[str, Any]:
    """Build the meta block for YAML from intake questionnaire answers.

    Args:
        grain: Description of what each row represents.
        model_type: One of "fact", "dimension", "integration", "report".
        entity: Optional business entity name.
        cdm_entity: Optional CDM entity name.

    Returns:
        Dict suitable for use as a dbt model's meta block.
    """
    meta: dict[str, Any] = {
        "intake_completed": True,
        "intake_date": datetime.date.today().isoformat(),
        "model_type": model_type,
        "grain": grain,
    }
    if entity:
        meta["entity"] = entity
    if cdm_entity:
        meta["cdm_entity"] = cdm_entity
    return meta


def get_existing_models_by_prefix(
    manifest_nodes: dict,
    prefix: str,
) -> list[str]:
    """Get model names matching a prefix from manifest nodes.

    Args:
        manifest_nodes: The "nodes" dict from a dbt manifest.
        prefix: Prefix to filter by (e.g., "fct_", "dim_", "int_").

    Returns:
        List of model names starting with the given prefix.
    """
    return [
        node["name"]
        for node in manifest_nodes.values()
        if isinstance(node, dict) and node.get("name", "").startswith(prefix)
    ]


def run_new_model() -> int:
    """Run the interactive guided intake questionnaire.

    Returns:
        Exit code (0 for success, 1 for failure or user cancellation).
    """
    try:
        import questionary
    except ImportError:
        print("Error: questionary is required. Run `pip install questionary`.", file=sys.stderr)
        return 1

    from rich.console import Console
    console = Console()

    console.print("\n[bold]New Model Intake[/bold]")
    console.print("This questionnaire helps you design your model entity-first.\n")

    source = questionary.text(
        "What data are you working with? (source system and table names)"
    ).ask()
    if source is None:
        return 1

    grain = questionary.text(
        "What does each row represent? (e.g., 'one reservation', 'one park')"
    ).ask()
    if grain is None:
        return 1

    behavior = questionary.select(
        "What happens to this thing over time?",
        choices=[
            "Static reference (rarely changes)",
            "Lifecycle with statuses (created → active → closed)",
            "Point-in-time measurement (sensor reading, count, score)",
            "One-time event/transaction (sale, booking, inspection)",
        ],
    ).ask()
    if behavior is None:
        return 1

    related = questionary.text(
        "Who or what is involved? (related entities, e.g., 'parks, customers, employees')"
    ).ask()

    questions = questionary.text(
        "What questions should the data answer? (not report names — business questions)"
    ).ask()

    layer = questionary.select(
        "Which layer is this model for?",
        choices=[
            "Staging (cast/rename from source)",
            "Integration (normalize an entity across systems)",
            "Mart (business-facing: fact, dimension, or report)",
        ],
    ).ask()
    if layer is None:
        return 1

    suggested_type = classify_entity_behavior(behavior)

    if "Integration" in layer:
        _handle_integration_branch(console, source, grain, related or "")
    elif "Mart" in layer:
        _handle_mart_branch(console, source, grain, related or "", suggested_type)
    else:
        _handle_staging_branch(console, source, grain)

    return 0


def _handle_staging_branch(console: Any, source: str, grain: str) -> None:
    """Handle staging layer intake -- print guidance and next steps.

    Args:
        console: Rich Console instance.
        source: Source system and table description.
        grain: Row grain description.
    """
    console.print("\n[bold]Staging Model[/bold]")
    console.print("Staging models cast, rename, and return -- nothing else.")
    console.print(f"\nGrain: {grain}")
    console.print(f"Source: {source}")
    console.print("\nNext steps:")
    console.print("  1. Create the staging SQL (cast + rename only)")
    console.print("  2. Run: python -m scripts.scaffold tests --select <model>")


def _handle_integration_branch(
    console: Any, source: str, grain: str, related: str
) -> None:
    """Handle integration layer intake -- CDM matching and scaffold output.

    Args:
        console: Rich Console instance.
        source: Source system and table description.
        grain: Row grain description.
        related: Related entities description.
    """
    import questionary

    console.print("\n[bold]Integration Model[/bold]")

    entity_name = questionary.text(
        "What business entity does this model represent? "
        "(e.g., 'park', 'reservation', 'employee')"
    ).ask()
    if entity_name is None:
        return

    console.print(f"\nSearching CDM for: {entity_name}")
    from scripts.llm_context.cdm_advisor import run_cdm_match
    run_cdm_match(entity_name)

    sources_raw = questionary.text(
        "Which staging models does this integrate? "
        "(comma-separated, e.g., stg_system_a__table, stg_system_b__table)"
    ).ask() or ""
    sources = [s.strip() for s in sources_raw.split(",") if s.strip()]

    key_col = questionary.text("What is the natural primary key column?").ask() or "id"

    meta = build_intake_meta(grain=grain, model_type="integration", entity=entity_name)
    model_name = f"int_{entity_name.lower().replace(' ', '_')}s"

    from scripts._core.renderers.llm import render_llm_context
    llm_context = render_llm_context(
        sections={
            "Task": f"Build integration model {model_name}",
            "Business Entity": entity_name,
            "Grain": grain,
            "Sources": sources if sources else ["TODO: specify sources"],
            "Related Entities": related or "Not specified",
            "CDM Entity": "(see CDM match above)",
            "Natural Key": key_col,
        },
        suggested_prompt=(
            f"I am building a dbt integration model called {model_name} that normalizes "
            f"the {entity_name} entity across {len(sources)} staging source(s). "
            f"Grain: {grain}. "
            f"Help me design the union structure, surrogate key strategy, and CDM column mappings."
        ),
    )
    console.print("\n[bold]--- LLM Context Block (paste into Gemini) ---[/bold]")
    print(llm_context)


def _handle_mart_branch(
    console: Any, source: str, grain: str, related: str, suggested_type: str
) -> None:
    """Handle mart layer intake -- fact/dim/report classification.

    Args:
        console: Rich Console instance.
        source: Source system and table description.
        grain: Row grain description.
        related: Related entities description.
        suggested_type: Pre-classified type from classify_entity_behavior.
    """
    import questionary

    model_type = questionary.select(
        "What kind of mart model is this?",
        choices=[
            "A business event that happened (transaction, booking, inspection) \u2192 FACT",
            "A descriptive entity (a park, a person, an asset, a date) \u2192 DIMENSION",
            "A summary that combines multiple facts or aggregates to a different grain \u2192 REPORT",
            "Not sure",
        ],
    ).ask()

    if model_type is None:
        return

    if "FACT" in model_type:
        _handle_fact_intake(console, grain, related)
    elif "DIMENSION" in model_type:
        _handle_dimension_intake(console, grain)
    elif "REPORT" in model_type:
        _handle_report_intake(console, grain)
    else:
        console.print(f"\nBased on your answers, this looks like a [bold]{suggested_type}[/bold].")
        console.print("A FACT captures a business event. A DIMENSION describes an entity.")


def _handle_fact_intake(console: Any, grain: str, related: str) -> None:
    """Handle fact model intake -- check for duplicate facts, suggest dimensions.

    Args:
        console: Rich Console instance.
        grain: Row grain description.
        related: Related entities description.
    """
    import questionary

    console.print("\n[bold]Fact Model Design[/bold]")

    try:
        from scripts._core.selector import load_manifest
        manifest = load_manifest()
        existing_facts = get_existing_models_by_prefix(manifest.get("nodes", {}), "fct_")
        if existing_facts:
            console.print("\nExisting fact models:")
            for f in existing_facts:
                console.print(f"  - {f}")
            dupe = questionary.confirm(
                "Do any of these already capture the same business event?"
            ).ask()
            if dupe:
                console.print("\u2192 You may need a REPORT model that aggregates the existing fact.")
                return
    except Exception:
        pass

    dimension_categories = questionary.checkbox(
        "What dimensions describe this event?",
        choices=[
            "Who (a person, customer, or organization)",
            "Where (a park, facility, or location)",
            "When (a date or time period)",
            "What (an asset, product, or item)",
        ],
    ).ask()

    if dimension_categories:
        try:
            from scripts._core.selector import load_manifest
            manifest = load_manifest()
            existing_dims = get_existing_models_by_prefix(manifest.get("nodes", {}), "dim_")
            for cat in dimension_categories:
                matching = [d for d in existing_dims if any(
                    kw in d for kw in cat.lower().split()
                )]
                if matching:
                    console.print(f"  \u2713 {cat}: join via {matching[0]}")
                else:
                    console.print(f"  \u26a0 {cat}: no existing dimension found -- consider building one first")
        except Exception:
            pass

    meta = build_intake_meta(grain=grain, model_type="fact")
    console.print(f"\n[dim]YAML meta:[/dim] {meta}")


def _handle_dimension_intake(console: Any, grain: str) -> None:
    """Handle dimension model intake.

    Args:
        console: Rich Console instance.
        grain: Row grain description.
    """
    console.print("\n[bold]Dimension Model Design[/bold]")
    console.print("Dimensions describe entities. They have a surrogate key and descriptive attributes.")
    meta = build_intake_meta(grain=grain, model_type="dimension")
    console.print(f"\n[dim]YAML meta:[/dim] {meta}")


def _handle_report_intake(console: Any, grain: str) -> None:
    """Handle report model intake.

    Args:
        console: Rich Console instance.
        grain: Row grain description.
    """
    import questionary

    console.print("\n[bold]Report Model Design[/bold]")
    console.print("Reports earn their place when they combine multiple facts or aggregate to a different grain.")

    agg_grain = questionary.text(
        "What grain does the report aggregate to? (e.g., 'park + month')"
    ).ask()

    meta = build_intake_meta(grain=agg_grain or grain, model_type="report")
    console.print(f"\n[dim]YAML meta:[/dim] {meta}")
