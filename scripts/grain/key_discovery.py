# scripts/grain/key_discovery.py
"""Candidate primary key detection via analytical queries."""
from __future__ import annotations

import itertools
import logging
from typing import Any

import pandas as pd

from scripts._core.models import SelectionTarget

logger = logging.getLogger(__name__)

# Columns with individual uniqueness ratio below this threshold
# are excluded from combination testing.
ELIGIBILITY_THRESHOLD = 0.5

# Stop testing 3-column combos if a 1- or 2-column candidate
# achieves at least this uniqueness ratio.
CANDIDATE_THRESHOLD = 0.99

# Cap on number of 2-column combinations to test.
MAX_2COL_COMBOS = 50


def compute_uniqueness_ratios(df: pd.DataFrame) -> dict[str, float]:
    """Compute count_distinct / total_rows for every column."""
    total = len(df)
    if total == 0:
        return {}
    return {col: df[col].nunique() / total for col in df.columns}


def find_candidate_keys(
    df: pd.DataFrame,
    eligibility_threshold: float = ELIGIBILITY_THRESHOLD,
    candidate_threshold: float = CANDIDATE_THRESHOLD,
    max_2col_combos: int = MAX_2COL_COMBOS,
) -> list[dict[str, Any]]:
    """Find candidate primary keys by testing column uniqueness.

    Returns a list of candidates sorted by uniqueness ratio (desc),
    each as: {"columns": [...], "uniqueness_ratio": float}
    """
    total = len(df)
    if total == 0:
        return []

    # Phase 1: single-column sweep
    ratios = compute_uniqueness_ratios(df)
    candidates: list[dict[str, Any]] = []

    for col, ratio in ratios.items():
        if ratio >= eligibility_threshold:
            candidates.append({"columns": [col], "uniqueness_ratio": ratio})

    # If we already have a perfect single-column key, skip composites
    if any(c["uniqueness_ratio"] >= candidate_threshold for c in candidates):
        candidates.sort(key=lambda c: c["uniqueness_ratio"], reverse=True)
        return candidates

    # Phase 2: 2-column combinations of eligible columns
    eligible = [col for col, ratio in ratios.items() if ratio >= eligibility_threshold]
    combos_2 = list(itertools.combinations(eligible, 2))[:max_2col_combos]

    for combo in combos_2:
        distinct = df.groupby(list(combo)).ngroups
        ratio = distinct / total
        candidates.append({"columns": list(combo), "uniqueness_ratio": ratio})

    if any(c["uniqueness_ratio"] >= candidate_threshold for c in candidates):
        candidates.sort(key=lambda c: c["uniqueness_ratio"], reverse=True)
        return candidates

    # Phase 3: 3-column combinations (only if needed)
    combos_3 = list(itertools.combinations(eligible, 3))[:max_2col_combos]
    for combo in combos_3:
        distinct = df.groupby(list(combo)).ngroups
        ratio = distinct / total
        candidates.append({"columns": list(combo), "uniqueness_ratio": ratio})

    candidates.sort(key=lambda c: c["uniqueness_ratio"], reverse=True)
    return candidates


def check_yaml_test_coverage(
    key_columns: list[str],
    yaml_tests: dict[str, list[str]],
) -> dict[str, Any]:
    """Check if candidate key columns have unique/unique_combination tests.

    Args:
        key_columns: The columns forming the candidate key.
        yaml_tests: Dict of column_name -> list of test names from YAML.

    Returns:
        {"covered": bool, "missing_tests": list[str]}
    """
    missing = []
    if len(key_columns) == 1:
        col = key_columns[0]
        col_tests = yaml_tests.get(col, [])
        if "unique" not in col_tests:
            missing.append("unique")
        if "not_null" not in col_tests:
            missing.append("not_null")
    else:
        # For composite keys, check that all key columns have not_null
        for col in key_columns:
            col_tests = yaml_tests.get(col, [])
            if "not_null" not in col_tests:
                missing.append(f"not_null on {col}")
        # Composite keys always need a unique_combination_of_columns test
        missing.append("unique_combination_of_columns")

    return {"covered": len(missing) == 0, "missing_tests": missing}


def _extract_yaml_tests(node: dict) -> dict[str, list[str]]:
    """Extract existing test names per column from a manifest node.

    In the dbt manifest, per-column tests live under node["columns"][col_name]["data_tests"]
    as a list of strings (e.g. ["unique", "not_null"]) or dicts with test configs.
    """
    yaml_tests: dict[str, list[str]] = {}
    for col_name, col_info in node.get("columns", {}).items():
        tests: list[str] = []
        for test in col_info.get("data_tests", []):
            if isinstance(test, str):
                tests.append(test)
            elif isinstance(test, dict):
                # Dict form: {"not_null": {...}} or {"accepted_values": {...}}
                tests.extend(test.keys())
        yaml_tests[col_name] = tests
    return yaml_tests


def run_key_discovery(target: SelectionTarget, output_mode: str = "terminal") -> list[dict]:
    """Full key discovery pipeline for a model.

    Queries the materialized table, finds candidate keys, checks YAML coverage.
    """
    from scripts._core.connectors.duckdb import DuckDBConnector
    from scripts._core.connectors.bigquery import BigQueryConnector
    from scripts._core.selector import load_manifest

    if target.connector_type == "duckdb":
        connector = DuckDBConnector(target)
    else:
        connector = BigQueryConnector(target)

    try:
        df = connector.get_sample(10000)
    finally:
        if hasattr(connector, "close"):
            connector.close()

    candidates = find_candidate_keys(df)

    # Cross-reference with YAML tests
    try:
        manifest = load_manifest()
        node_key = f"model.dcr_analytics.{target.table}"
        node = manifest.get("nodes", {}).get(node_key, {})
        yaml_tests = _extract_yaml_tests(node)
        for candidate in candidates:
            coverage = check_yaml_test_coverage(candidate["columns"], yaml_tests)
            candidate["yaml_covered"] = coverage["covered"]
            candidate["missing_tests"] = coverage["missing_tests"]
    except Exception:
        pass  # YAML cross-reference is best-effort

    if output_mode == "terminal":
        _render_terminal(target, candidates)

    return candidates


def _render_terminal(target: SelectionTarget, candidates: list[dict]) -> None:
    """Print key discovery results to terminal."""
    print(f"\nKEY DISCOVERY: {target.table}")
    print("=" * (16 + len(target.table)))

    if not candidates:
        print("  No candidate keys found.")
        return

    for i, c in enumerate(candidates[:10]):
        cols = ", ".join(c["columns"])
        ratio = c["uniqueness_ratio"]
        marker = "\u2713" if ratio >= 0.99 else "~" if ratio >= 0.9 else "\u2717"
        print(f"  {marker} [{ratio:.1%}] {cols}")
