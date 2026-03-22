# scripts/llm_context/cdm_advisor.py
"""Three-tier CDM entity matching advisor.

Tier 1: Curated synonym map lookup (highest confidence)
Tier 2: Token overlap against entity descriptions (medium confidence)
Tier 3: LLM prompt generation when no match found (fallback)
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

SYNONYMS_PATH = Path(__file__).parents[2] / "seeds" / "cdm_catalogs" / "cdm_concept_synonyms.csv"
ENTITY_CATALOG_PATH = Path(__file__).parents[2] / "seeds" / "cdm_catalogs" / "entity_catalog.csv"


def _load_synonyms(path: Path = SYNONYMS_PATH) -> pd.DataFrame:
    """Load the curated CDM concept synonym map."""
    return pd.read_csv(path)


def _load_entity_catalog(path: Path = ENTITY_CATALOG_PATH) -> pd.DataFrame | None:
    """Load the CDM entity catalog, or return None if not found."""
    if path.exists():
        return pd.read_csv(path)
    return None


def _tokenize(text: str) -> set[str]:
    """Split text into lowercase tokens, adding naively stemmed forms."""
    words = set(re.findall(r"[a-z]+", text.lower()))
    stemmed: set[str] = set()
    for w in words:
        if w.endswith("s") and len(w) > 3:
            stemmed.add(w[:-1])
        if w.endswith("ing") and len(w) > 5:
            stemmed.add(w[:-3])
        if w.endswith("tion") and len(w) > 6:
            stemmed.add(w[:-4])
    return words | stemmed


def tier1_synonym_match(
    concept: str,
    synonyms_df: pd.DataFrame,
) -> list[dict[str, Any]]:
    """Tier 1: Match concept against curated synonym map.

    Args:
        concept: Business concept string to match.
        synonyms_df: DataFrame with columns: concept, cdm_entity, confidence_note.

    Returns:
        List of dicts with cdm_entity, score (0-1), confidence_note, tier=1.
        Sorted by score descending. At most one entry per CDM entity.
    """
    concept_lower = concept.lower().strip()
    concept_tokens = _tokenize(concept)

    results: list[dict[str, Any]] = []
    seen_entities: set[str] = set()

    for _, row in synonyms_df.iterrows():
        syn = str(row["concept"]).lower().strip()
        syn_tokens = _tokenize(syn)

        if concept_lower == syn:
            score = 1.0
        elif concept_tokens & syn_tokens:
            overlap = len(concept_tokens & syn_tokens) / max(len(concept_tokens), len(syn_tokens))
            score = round(overlap * 0.9, 3)
        else:
            continue

        entity = str(row["cdm_entity"])
        if entity not in seen_entities:
            seen_entities.add(entity)
            results.append({
                "cdm_entity": entity,
                "score": score,
                "confidence_note": str(row.get("confidence_note", "")),
                "tier": 1,
            })

    results.sort(key=lambda r: r["score"], reverse=True)
    return results


def tier2_description_match(
    concept: str,
    entity_catalog_df: pd.DataFrame,
) -> list[dict[str, Any]]:
    """Tier 2: Match concept against entity descriptions via token overlap.

    Args:
        concept: Business concept string to match.
        entity_catalog_df: DataFrame with columns: cdm_entity, entity_description, cdm_manifest.

    Returns:
        List of dicts with cdm_entity, score (0-0.8), description, tier=2.
        Sorted by score descending.
    """
    concept_tokens = _tokenize(concept)
    results: list[dict[str, Any]] = []

    for _, row in entity_catalog_df.iterrows():
        desc = str(row.get("entity_description", ""))
        desc_tokens = _tokenize(desc)

        overlap = concept_tokens & desc_tokens
        if not overlap:
            continue

        score = round(len(overlap) / max(len(concept_tokens), 1) * 0.8, 3)
        results.append({
            "cdm_entity": str(row["cdm_entity"]),
            "score": score,
            "description": desc,
            "tier": 2,
        })

    results.sort(key=lambda r: r["score"], reverse=True)
    return results


def tier3_generate_prompt(
    concept: str,
    source_columns: list[str] | None = None,
) -> str:
    """Tier 3: Generate an LLM prompt for CDM entity discovery.

    Args:
        concept: Business concept that could not be matched automatically.
        source_columns: Optional list of source column names to include in the prompt.

    Returns:
        Formatted prompt string suitable for pasting into an LLM.
    """
    cols_section = ""
    if source_columns:
        cols_list = "\n".join(f"  - {c}" for c in source_columns)
        cols_section = f"\n\nSource columns:\n{cols_list}"

    return (
        f"I am building an integration model for a public sector data warehouse.\n\n"
        f"Business concept: {concept}{cols_section}\n\n"
        f"Which Microsoft Common Data Model (CDM) entity best represents this concept?\n"
        f"If no standard entity fits, which entity should I extend or adapt?\n"
        f"What other business operations might share this same entity pattern?\n\n"
        f"Please suggest:\n"
        f"1. The CDM entity name and why it fits\n"
        f"2. Core columns I should map from the CDM entity\n"
        f"3. Columns that are specific to my domain (not in CDM) that I should add\n"
    )


def score_candidates(
    tier1_results: list[dict],
    tier2_results: list[dict],
    column_overlap_bonus: float = 0.0,
) -> list[dict[str, Any]]:
    """Combine tier 1 and tier 2 results with weighted scoring.

    Formula: final = (0.6 * synonym_score) + (0.3 * description_score) + (0.1 * column_bonus)

    Args:
        tier1_results: Output of tier1_synonym_match.
        tier2_results: Output of tier2_description_match.
        column_overlap_bonus: Optional 0-1 bonus for column name overlap (default 0.0).

    Returns:
        List of dicts with cdm_entity, final_score, and contributing tier scores.
        Sorted by final_score descending.
    """
    entity_scores: dict[str, dict] = {}

    for r in tier1_results:
        entity = r["cdm_entity"]
        entity_scores[entity] = {
            "cdm_entity": entity,
            "synonym_score": r["score"],
            "description_score": 0.0,
            "column_bonus": column_overlap_bonus,
            "confidence_note": r.get("confidence_note", ""),
            "description": "",
        }

    for r in tier2_results:
        entity = r["cdm_entity"]
        if entity in entity_scores:
            entity_scores[entity]["description_score"] = r["score"]
            entity_scores[entity]["description"] = r.get("description", "")
        else:
            entity_scores[entity] = {
                "cdm_entity": entity,
                "synonym_score": 0.0,
                "description_score": r["score"],
                "column_bonus": 0.0,
                "confidence_note": "",
                "description": r.get("description", ""),
            }

    for entity_data in entity_scores.values():
        entity_data["final_score"] = round(
            0.6 * entity_data["synonym_score"]
            + 0.3 * entity_data["description_score"]
            + 0.1 * entity_data["column_bonus"],
            3,
        )

    return sorted(entity_scores.values(), key=lambda r: r["final_score"], reverse=True)


def run_cdm_match(
    concept: str,
    source_columns: list[str] | None = None,
) -> int:
    """Run the full CDM matching pipeline and print results.

    Args:
        concept: Business concept to match against CDM entities.
        source_columns: Optional list of source column names for context.

    Returns:
        Exit code (always 0).
    """
    synonyms_df = _load_synonyms()
    entity_catalog_df = _load_entity_catalog()

    tier1 = tier1_synonym_match(concept, synonyms_df)

    tier2: list[dict] = []
    if entity_catalog_df is not None:
        tier2 = tier2_description_match(concept, entity_catalog_df)

    combined = score_candidates(tier1, tier2)

    if combined:
        print(f'\nCDM MATCH: "{concept}"')
        print("=" * (12 + len(concept)))
        for i, r in enumerate(combined[:5], 1):
            print(f"\n  {i}. {r['cdm_entity']} (score: {r['final_score']:.2f})")
            if r.get("confidence_note"):
                print(f"     Why: {r['confidence_note']}")
            if r.get("description"):
                print(f"     Description: {r['description'][:100]}")
    else:
        print(f'\nNo CDM match found for "{concept}".')

    if not combined or combined[0]["final_score"] < 0.3:
        prompt = tier3_generate_prompt(concept, source_columns)
        print("\n--- LLM Prompt (paste into Gemini) ---\n")
        print(prompt)

    return 0
