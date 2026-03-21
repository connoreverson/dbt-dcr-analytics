# scripts/grain/dag_lint.py
"""DAG direction checker -- detects same-layer, reverse, and skip-layer references."""
from __future__ import annotations

import logging
from typing import Any

from scripts._core.models import SelectionTarget

logger = logging.getLogger(__name__)

# Valid dependency directions: layer -> set of allowed dependency layers.
VALID_DIRECTIONS: dict[str, set[str]] = {
    "staging": {"source"},
    "base": {"source"},
    "integration": {"staging", "base"},
    "marts": {"integration", "staging"},  # staging for seeds/lookups
}


def _dep_layer(unique_id: str) -> str:
    """Determine the layer of a dependency from its unique_id."""
    if unique_id.startswith("source."):
        return "source"
    # Extract model name from unique_id like "model.dcr_analytics.stg_parks__raw"
    parts = unique_id.split(".")
    name = parts[-1] if len(parts) >= 3 else unique_id

    if name.startswith("stg_"):
        return "staging"
    if name.startswith("base_"):
        return "base"
    if name.startswith("int_"):
        return "integration"
    if name.startswith(("fct_", "dim_", "rpt_")):
        return "marts"
    if name.startswith("seed_") or unique_id.startswith("seed."):
        return "seed"
    return "unknown"


def check_dependency_direction(
    model_name: str,
    model_layer: str,
    depends_on: list[str],
    meta: dict | None = None,
) -> list[dict[str, Any]]:
    """Check all dependencies for direction violations.

    Args:
        model_name: The model being checked.
        model_layer: Layer of the model (staging/integration/marts/etc.).
        depends_on: List of unique_ids this model depends on.
        meta: Optional YAML meta block (for shared_integration_dependency suppression).

    Returns:
        List of findings.
    """
    findings: list[dict[str, Any]] = []
    allowed = VALID_DIRECTIONS.get(model_layer, set())
    suppressed: set[str] = set()

    if meta and meta.get("shared_integration_dependency"):
        dep = meta["shared_integration_dependency"]
        if isinstance(dep, list):
            suppressed.update(dep)
        else:
            suppressed.add(dep)

    for dep_id in depends_on:
        dep_name = dep_id.split(".")[-1]
        dep_lyr = _dep_layer(dep_id)

        # Seeds are always allowed
        if dep_lyr in ("seed", "unknown"):
            continue

        if dep_lyr in allowed:
            continue

        # Mart-to-mart (fact depends on fact) -- check BEFORE same-layer generic
        if model_layer == "marts" and dep_lyr == "marts":
            findings.append({
                "check": "mart_to_mart",
                "severity": "warning",
                "message": f"Mart-to-mart reference: depends on {dep_name}",
                "detail": "Facts should not depend on other facts. "
                          "Use a report model to combine them.",
            })

        # Same-layer reference (non-mart)
        elif dep_lyr == model_layer:
            if dep_name in suppressed:
                continue
            findings.append({
                "check": "same_layer_reference",
                "severity": "warning",
                "message": (
                    f"Same-layer reference: depends on {dep_name} "
                    f"({model_layer} -> {dep_lyr})"
                ),
                "detail": (
                    f"{model_layer.title()} models should not depend on other "
                    f"{model_layer} models. If intentional, add meta: "
                    "{ shared_integration_dependency: "
                    f'"{dep_name}" '
                    "} to suppress."
                ),
            })

        # Skip-layer (mart directly referencing source)
        elif dep_lyr == "source" and model_layer in ("marts", "integration"):
            if model_layer == "marts":
                findings.append({
                    "check": "skip_layer",
                    "severity": "warning",
                    "message": (
                        f"Skip-layer: mart depends directly on source ({dep_name})"
                    ),
                    "detail": (
                        "Mart models should depend on integration or staging, "
                        "not sources directly."
                    ),
                })

        # Reverse reference
        else:
            findings.append({
                "check": "reverse_reference",
                "severity": "error",
                "message": (
                    f"Reverse reference: {model_layer} depends on "
                    f"{dep_lyr} ({dep_name})"
                ),
                "detail": (
                    f"{model_layer.title()} models must not depend on "
                    f"{dep_lyr} models."
                ),
            })

    return findings


def run_dag_lint(
    target: SelectionTarget,
    output_mode: str = "terminal",
) -> list[dict]:
    """Run DAG direction checks for a model."""
    from scripts._core.selector import load_manifest, determine_layer

    manifest = load_manifest()
    node_key = f"model.dcr_analytics.{target.table}"
    node = manifest.get("nodes", {}).get(node_key)

    if node is None:
        logger.warning("Model %s not found in manifest", target.table)
        return []

    model_layer = determine_layer(target.table)
    depends_on = node.get("depends_on", {}).get("nodes", [])
    meta = node.get("meta", {})

    findings = check_dependency_direction(target.table, model_layer, depends_on, meta)

    if output_mode == "terminal":
        _render_terminal(target, findings)

    return findings


def _render_terminal(target: SelectionTarget, findings: list[dict]) -> None:
    """Print DAG lint results."""
    print(f"\nDAG LINT: {target.table}")
    print("=" * (10 + len(target.table)))

    if not findings:
        print("  All dependencies follow valid DAG direction.")
        return

    for f in findings:
        icon = "X" if f["severity"] == "error" else "!"
        print(f"  {icon} {f['message']}")
        print(f"    -> {f['detail']}")
