# scripts/grain/integration_lint.py
"""Integration model anti-pattern detection."""
from __future__ import annotations

import logging
from typing import Any

from scripts._core.models import SelectionTarget

logger = logging.getLogger(__name__)


def check_single_source(depends_on: list[str]) -> dict[str, Any] | None:
    """Flag integration models that depend on only one staging source."""
    staging_parents = [d for d in depends_on if ".stg_" in d or ".base_" in d]
    if len(staging_parents) <= 1:
        return {
            "check": "single_source",
            "severity": "warning",
            "message": f"Single staging source: {staging_parents[0] if staging_parents else 'none'}",
            "detail": "Integration models should normalize an entity across multiple sources. "
                      "A single-source integration model may be a pass-through.",
        }
    return None


def check_no_surrogate_key(columns: list[str]) -> dict[str, Any] | None:
    """Flag integration models without a surrogate key column."""
    sk_cols = [c for c in columns if c.endswith("_sk")]
    if not sk_cols:
        return {
            "check": "no_surrogate_key",
            "severity": "warning",
            "message": "No surrogate key (_sk) column in output",
            "detail": "Integration models should generate surrogate keys via "
                      "dbt_utils.generate_surrogate_key() for downstream joins.",
        }
    return None


def check_no_cdm_mapping(meta: dict) -> dict[str, Any] | None:
    """Flag integration models without a CDM entity in meta."""
    if not meta.get("cdm_entity"):
        return {
            "check": "no_cdm_mapping",
            "severity": "warning",
            "message": "No cdm_entity in YAML meta block",
            "detail": "Integration models should map to a CDM entity. "
                      "Run `python -m scripts.llm_context cdm-match` to find one.",
        }
    return None


def check_no_intake_metadata(
    meta: dict,
    is_pre_existing: bool = False,
) -> dict[str, Any] | None:
    """Flag models without intake metadata."""
    if not meta.get("intake_completed"):
        severity = "info" if is_pre_existing else "warning"
        return {
            "check": "no_intake_metadata",
            "severity": severity,
            "message": "No intake_completed in YAML meta block",
            "detail": "Consider running `python -m scripts.llm_context new-model` "
                      "to document this model's entity and grain.",
        }
    return None


def run_integration_lint(
    target: SelectionTarget,
    output_mode: str = "terminal",
) -> list[dict]:
    """Run all integration lint checks for a model."""
    from scripts._core.selector import load_manifest

    manifest = load_manifest()
    node_key = f"model.dcr_analytics.{target.table}"
    node = manifest.get("nodes", {}).get(node_key)

    if node is None:
        logger.warning("Model %s not found in manifest", target.table)
        return []

    depends_on = node.get("depends_on", {}).get("nodes", [])
    columns = list(node.get("columns", {}).keys())
    meta = node.get("meta", {})

    # Heuristic: models without intake_completed that were committed
    # before this tooling are "pre-existing"
    is_pre_existing = not meta.get("intake_completed")

    findings: list[dict] = []

    result = check_single_source(depends_on)
    if result:
        findings.append(result)

    result = check_no_surrogate_key(columns)
    if result:
        findings.append(result)

    result = check_no_cdm_mapping(meta)
    if result:
        findings.append(result)

    result = check_no_intake_metadata(meta, is_pre_existing=is_pre_existing)
    if result:
        findings.append(result)

    if output_mode == "terminal":
        _render_terminal(target, findings)

    return findings


def _render_terminal(target: SelectionTarget, findings: list[dict]) -> None:
    """Print integration lint results."""
    print(f"\nINTEGRATION LINT: {target.table}")
    print("=" * (18 + len(target.table)))

    if not findings:
        print("  \u2713 No anti-patterns detected.")
        return

    for f in findings:
        icon = {"error": "\u2717", "warning": "\u26a0", "info": "\u2139"}.get(f["severity"], "?")
        print(f"  {icon} {f['message']}")
        print(f"    -> {f['detail']}")
