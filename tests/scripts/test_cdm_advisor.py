# tests/scripts/test_cdm_advisor.py
import pandas as pd
import pytest
from scripts.llm_context.cdm_advisor import (
    tier1_synonym_match,
    tier2_description_match,
    tier3_generate_prompt,
    score_candidates,
)


@pytest.fixture
def synonyms_df():
    return pd.DataFrame({
        "concept": ["park", "facility", "reservation", "booking", "employee", "staff"],
        "cdm_entity": ["Asset", "Asset", "Reservation", "Reservation", "Employee", "Employee"],
        "confidence_note": ["Parks are assets"] * 6,
    })


@pytest.fixture
def entity_catalog_df():
    return pd.DataFrame({
        "cdm_entity": ["Asset", "Reservation", "Employee", "Grant"],
        "entity_description": [
            "Physical assets owned or managed by the organization",
            "A booking or reservation of a park facility",
            "People employed by the organization",
            "Financial grant applications and awards",
        ],
        "cdm_manifest": ["Asset", "applicationCommon", "nonProfitCore", "nonProfitCore"],
    })


def test_tier1_exact_match(synonyms_df):
    results = tier1_synonym_match("park", synonyms_df)
    assert len(results) == 1
    assert results[0]["cdm_entity"] == "Asset"
    assert results[0]["score"] == 1.0


def test_tier1_fuzzy_match(synonyms_df):
    results = tier1_synonym_match("parks", synonyms_df)
    assert len(results) >= 1
    assert results[0]["cdm_entity"] == "Asset"


def test_tier1_no_match(synonyms_df):
    results = tier1_synonym_match("xyzzy_nonexistent", synonyms_df)
    assert len(results) == 0


def test_tier2_description_match(entity_catalog_df):
    results = tier2_description_match("grant application", entity_catalog_df)
    assert len(results) >= 1
    assert results[0]["cdm_entity"] == "Grant"


def test_tier3_generates_prompt():
    prompt = tier3_generate_prompt(
        concept="inspection checklist",
        source_columns=["inspection_id", "date", "inspector", "result"],
    )
    assert "inspection checklist" in prompt
    assert "inspection_id" in prompt
    assert "CDM" in prompt


def test_score_candidates_weighted():
    tier1 = [{"cdm_entity": "Asset", "score": 1.0}]
    tier2 = [{"cdm_entity": "Asset", "score": 0.8}, {"cdm_entity": "Grant", "score": 0.5}]
    results = score_candidates(tier1, tier2)
    # Asset should score higher due to both tiers matching
    assert results[0]["cdm_entity"] == "Asset"
    assert results[0]["final_score"] > results[1]["final_score"]
