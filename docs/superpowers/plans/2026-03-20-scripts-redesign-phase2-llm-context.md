# Phase 2: `llm_context/` — LLM Context Generation, CDM Advisor, Guided Intake — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `llm_context/` package — the primary analyst workflow entry point. Provides a guided intake questionnaire (`new-model`) that makes entity-first modeling the path of least resistance, a CDM entity matching advisor (`cdm-match`), and LLM-friendly context generators for existing models and sources.

**Architecture:** Four modules behind a CLI with subcommands. `new_model` uses questionary for interactive intake, branches by layer (staging/integration/mart), and calls `cdm_advisor` and `scaffold/` for output. `cdm_advisor` implements three-tier matching (synonym map → description search → LLM prompt). `model_context` and `source_context` read manifest + query warehouse to produce LLM-pasteable summaries.

**Tech Stack:** Python 3.10+, questionary (interactive prompts), `_core/selector` and `_core/connectors` (dbt/warehouse), CDM seed CSVs

**Spec:** `docs/superpowers/specs/2026-03-20-scripts-redesign-design.md` (section: "Phase 2: `llm_context/`")

**Depends on:** Phase 0 (`_core/`), Phase 1 (`grain/` — for key discovery in source_context)

---

### Task 1: Create `llm_context/` package structure, CLI, and CDM seed files

**Files:**
- Create: `scripts/llm_context/__init__.py`
- Create: `scripts/llm_context/cli.py`
- Create: `seeds/cdm_catalogs/cdm_concept_synonyms.csv`
- Create: `seeds/cdm_catalogs/entity_catalog.csv`
- Test: `tests/scripts/test_llm_context_cli.py`

- [ ] **Step 1: Write test for CLI subcommand parsing**

```python
# tests/scripts/test_llm_context_cli.py
from scripts.llm_context.cli import parse_args


def test_parse_cdm_match():
    args = parse_args(["cdm-match", "--concept", "grant application"])
    assert args.subcommand == "cdm-match"
    assert args.concept == "grant application"


def test_parse_cdm_match_with_columns():
    args = parse_args([
        "cdm-match", "--concept", "park", "--source-columns", "id,name,acres"
    ])
    assert args.source_columns == "id,name,acres"


def test_parse_model_summary():
    args = parse_args(["model-summary", "--select", "int_parks"])
    assert args.subcommand == "model-summary"
    assert args.select == "int_parks"


def test_parse_source_summary():
    args = parse_args(["source-summary", "--select", "source:peoplefirst.employees"])
    assert args.subcommand == "source-summary"
    assert args.select == "source:peoplefirst.employees"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/scripts/test_llm_context_cli.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement CLI skeleton and create seed CSVs**

```python
# scripts/llm_context/__init__.py
```

```python
# scripts/llm_context/cli.py
"""LLM context generation, CDM advisor, and guided intake.

Usage:
    python -m scripts.llm_context new-model
    python -m scripts.llm_context cdm-match --concept "grant application"
    python -m scripts.llm_context model-summary --select int_parks
    python -m scripts.llm_context source-summary --select source:peoplefirst.employees
"""
from __future__ import annotations

import argparse
import logging
import sys


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="LLM context generation, CDM advisor, and guided intake.",
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # new-model
    sub_new = subparsers.add_parser("new-model", help="Guided intake questionnaire")

    # cdm-match
    sub_cdm = subparsers.add_parser("cdm-match", help="CDM entity matching")
    sub_cdm.add_argument("--concept", required=True, help="Business concept to match")
    sub_cdm.add_argument(
        "--source-columns", default="",
        help="Comma-separated source column names for column overlap bonus",
    )

    # model-summary
    sub_model = subparsers.add_parser("model-summary", help="Summarize existing model for LLM")
    sub_model.add_argument("--select", "-s", required=True, help="dbt model selector")

    # source-summary
    sub_source = subparsers.add_parser("source-summary", help="Summarize source table for LLM")
    sub_source.add_argument("--select", "-s", required=True, help="dbt source selector")

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

    if args.subcommand == "new-model":
        from scripts.llm_context.new_model import run_new_model
        return run_new_model()

    elif args.subcommand == "cdm-match":
        from scripts.llm_context.cdm_advisor import run_cdm_match
        columns = [c.strip() for c in args.source_columns.split(",") if c.strip()]
        return run_cdm_match(args.concept, source_columns=columns)

    elif args.subcommand == "model-summary":
        from scripts.llm_context.model_context import run_model_summary
        return run_model_summary(args.select)

    elif args.subcommand == "source-summary":
        from scripts.llm_context.source_context import run_source_summary
        return run_source_summary(args.select)

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Create CDM seed CSVs. **Do not include comment lines in CSVs — dbt treats all lines as data rows.**

```csv
concept,cdm_entity,confidence_note
park,Asset,"Parks are physical assets managed by the organization"
facility,Asset,"Facilities (buildings, shelters, pools) are assets within parks"
reservation,Reservation,"A booking or reservation of a facility or resource"
booking,Reservation,"Synonym for reservation — same CDM entity"
permit,Permit,"Authorization to use a park resource or perform an activity"
transaction,FinancialTransaction,"A monetary exchange — POS sale, fee payment, refund"
payment,FinancialTransaction,"Synonym for transaction — same CDM entity"
sale,FinancialTransaction,"A point-of-sale transaction"
employee,Employee,"A person employed by the organization"
staff,Employee,"Synonym for employee"
worker,Employee,"Synonym for employee"
visitor,VisitorCount,"Aggregated visitor traffic measurement"
traffic,VisitorCount,"Vehicle or pedestrian traffic count at a park entrance"
inspection,EcologicalSurvey,"Field observation or inspection of ecological conditions"
survey,EcologicalSurvey,"Ecological or environmental survey"
observation,EcologicalSurvey,"A field observation (flora, fauna, water quality)"
officer,OfficerShift,"Law enforcement officer shift assignment"
shift,OfficerShift,"A work shift for park police or rangers"
patrol,OfficerShift,"Synonym for officer shift"
grant,Grant,"A financial grant application or award"
application,Grant,"A grant or permit application"
customer,Contact,"A person or organization that interacts with DCR services"
contact,Contact,"A person or organization — the CDM Contact entity"
guest,Contact,"A park visitor or reservation guest"
```

Save as `seeds/cdm_catalogs/cdm_concept_synonyms.csv` (the file above — no header comment, just the CSV header row as first line).

```csv
cdm_entity_name,entity_description,cdm_manifest
Asset,"Physical assets owned or managed by the organization — parks, facilities, infrastructure, equipment. Tracked by location, type, condition, and lifecycle status.",Asset
Contact,"People and organizations that interact with DCR — visitors, permittees, grantees, vendors. Stores name, address, communication preferences.",nonProfitCore
Employee,"People employed by the organization. Stores position, department, hire date, compensation, duty station.",nonProfitCore
Reservation,"A booking or reservation of a park facility or resource. Captures dates, guest, facility, party size, status, and fees.",applicationCommon
FinancialTransaction,"A monetary exchange — point-of-sale purchases, fee payments, refunds, transfers. Captures amount, date, method, and associated entity.",nonProfitCore
EcologicalSurvey,"Field observations of ecological conditions — flora/fauna sightings, water quality measurements, invasive species tracking. Captures location, date, observer, and measurement values.",cdmfoundation
VisitorCount,"Aggregated visitor traffic measurements from sensors at park entrances. Captures sensor location, date, count, and vehicle/pedestrian classification.",Visits
OfficerShift,"Law enforcement officer work assignments — shift times, assigned park, patrol area, duty type. Subject to CJIS air-gap isolation requirements.",cdmfoundation
Grant,"Financial grant applications and awards — applicant, program, amount requested/awarded, status, dates.",nonProfitCore
Permit,"Authorization to use a park resource or perform a regulated activity. Captures applicant, type, location, dates, and conditions.",applicationCommon
```

Save as `seeds/cdm_catalogs/entity_catalog.csv`.

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/scripts/test_llm_context_cli.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/llm_context/ tests/scripts/test_llm_context_cli.py seeds/cdm_catalogs/cdm_concept_synonyms.csv seeds/cdm_catalogs/entity_catalog.csv
git commit -m "feat(llm_context): create package structure, CLI, and CDM seed files"
```

Also create `scripts/llm_context/__main__.py`:
```python
# scripts/llm_context/__main__.py
from scripts.llm_context.cli import main
import sys
sys.exit(main())
```
Add it to the same commit, or:
```bash
git add scripts/llm_context/__main__.py
git commit -m "feat(llm_context): add __main__.py for python -m scripts.llm_context"
```

---

### Task 2: Implement `cdm_advisor.py` — Three-tier CDM entity matching

**Files:**
- Create: `scripts/llm_context/cdm_advisor.py`
- Test: `tests/scripts/test_cdm_advisor.py`

- [ ] **Step 1: Write test for CDM matching tiers**

```python
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
        "cdm_entity_name": ["Asset", "Reservation", "Employee", "Grant"],
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/scripts/test_cdm_advisor.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement `cdm_advisor.py`**

```python
# scripts/llm_context/cdm_advisor.py
"""Three-tier CDM entity matching advisor."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

SYNONYMS_PATH = Path("seeds/cdm_catalogs/cdm_concept_synonyms.csv")
ENTITY_CATALOG_PATH = Path("seeds/cdm_catalogs/entity_catalog.csv")
COLUMN_CATALOGS_DIR = Path("seeds/cdm_catalogs")


def _load_synonyms(path: Path = SYNONYMS_PATH) -> pd.DataFrame:
    return pd.read_csv(path)


def _load_entity_catalog(path: Path = ENTITY_CATALOG_PATH) -> pd.DataFrame | None:
    if path.exists():
        return pd.read_csv(path)
    return None


def _tokenize(text: str) -> set[str]:
    """Split text into lowercase tokens, stripping common suffixes."""
    import re
    words = set(re.findall(r"[a-z]+", text.lower()))
    # Add stemmed forms (naive: strip trailing 's', 'ing', 'tion')
    stemmed = set()
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

    Returns list of {"cdm_entity": str, "score": float, "confidence_note": str}
    """
    concept_lower = concept.lower().strip()
    concept_tokens = _tokenize(concept)

    results: list[dict[str, Any]] = []
    seen_entities: set[str] = set()

    for _, row in synonyms_df.iterrows():
        syn = str(row["concept"]).lower().strip()
        syn_tokens = _tokenize(syn)

        # Exact match
        if concept_lower == syn:
            score = 1.0
        # Token overlap (fuzzy)
        elif concept_tokens & syn_tokens:
            overlap = len(concept_tokens & syn_tokens) / max(len(concept_tokens), len(syn_tokens))
            score = round(overlap * 0.9, 3)  # cap fuzzy at 0.9
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
    """Tier 2: Match concept against entity descriptions.

    Returns list of {"cdm_entity": str, "score": float, "description": str}
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
            "cdm_entity": str(row["cdm_entity_name"]),
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
    """Tier 3: Generate an LLM prompt for CDM entity discovery."""
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
    """Combine results from multiple tiers with weighted scoring.

    Formula: final = (0.6 * synonym) + (0.3 * description) + (0.1 * column_overlap)
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

    results = sorted(entity_scores.values(), key=lambda r: r["final_score"], reverse=True)
    return results


def run_cdm_match(
    concept: str,
    source_columns: list[str] | None = None,
) -> int:
    """Full CDM matching pipeline."""
    synonyms_df = _load_synonyms()
    entity_catalog_df = _load_entity_catalog()

    # Tier 1
    tier1 = tier1_synonym_match(concept, synonyms_df)

    # Tier 2
    tier2 = []
    if entity_catalog_df is not None:
        tier2 = tier2_description_match(concept, entity_catalog_df)

    # Combine
    combined = score_candidates(tier1, tier2)

    if combined:
        print(f"\nCDM MATCH: \"{concept}\"")
        print("=" * (12 + len(concept)))
        for i, r in enumerate(combined[:5], 1):
            print(f"\n  {i}. {r['cdm_entity']} (score: {r['final_score']:.2f})")
            if r.get("confidence_note"):
                print(f"     Why: {r['confidence_note']}")
            if r.get("description"):
                print(f"     Description: {r['description'][:100]}")
    else:
        print(f"\nNo CDM match found for \"{concept}\".")

    # Tier 3 fallback
    if not combined or combined[0]["final_score"] < 0.3:
        prompt = tier3_generate_prompt(concept, source_columns)
        print(f"\n--- LLM Prompt (paste into Gemini) ---\n")
        print(prompt)

    return 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/scripts/test_cdm_advisor.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/llm_context/cdm_advisor.py tests/scripts/test_cdm_advisor.py
git commit -m "feat(llm_context): implement cdm_advisor with three-tier entity matching"
```

---

### Task 3: Implement `model_context.py` — Existing model summary for LLM

**Files:**
- Create: `scripts/llm_context/model_context.py`
- Test: `tests/scripts/test_model_context.py`

- [ ] **Step 1: Write test for model context extraction**

```python
# tests/scripts/test_model_context.py
from scripts.llm_context.model_context import build_model_context


def test_build_model_context_basic():
    """Build context from a manifest node dict."""
    node = {
        "name": "int_parks",
        "resource_type": "model",
        "schema": "main",
        "description": "Parks integration model",
        "meta": {"cdm_entity": "Asset"},
        "depends_on": {
            "nodes": [
                "model.dcr_analytics.stg_geoparks__parks",
                "model.dcr_analytics.stg_infratrak__assets",
            ]
        },
        "columns": {
            "parks_sk": {"name": "parks_sk", "description": "Surrogate key"},
            "name": {"name": "name", "description": "Park name"},
        },
    }
    context = build_model_context(node)
    assert context["Model"] == "int_parks"
    assert context["Layer"] == "Integration"
    assert context["CDM Entity"] == "Asset"
    assert "stg_geoparks__parks" in context["Parents"]


def test_build_model_context_no_meta():
    """Handles missing meta gracefully."""
    node = {
        "name": "stg_test",
        "resource_type": "model",
        "schema": "main",
        "description": "",
        "meta": {},
        "depends_on": {"nodes": []},
        "columns": {},
    }
    context = build_model_context(node)
    assert context["CDM Entity"] == "Not specified"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/scripts/test_model_context.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement `model_context.py`**

```python
# scripts/llm_context/model_context.py
"""Summarize an existing dbt model for LLM consumption."""
from __future__ import annotations

import logging
from typing import Any

from scripts._core.selector import _determine_layer

logger = logging.getLogger(__name__)

LAYER_LABELS = {
    "staging": "Staging",
    "base": "Base",
    "integration": "Integration",
    "marts": "Mart",
    "unknown": "Unknown",
}


def build_model_context(node: dict) -> dict[str, Any]:
    """Extract structured context from a manifest node.

    Returns an ordered dict of section_name -> content for rendering.
    """
    name = node.get("name", "")
    layer = _determine_layer(name)
    layer_label = LAYER_LABELS.get(layer, "Unknown")

    # Refine mart label
    if layer == "marts":
        if name.startswith("fct_"):
            layer_label = "Mart (fact)"
        elif name.startswith("dim_"):
            layer_label = "Mart (dimension)"
        elif name.startswith("rpt_"):
            layer_label = "Mart (report)"

    meta = node.get("meta", {})
    depends_on = node.get("depends_on", {}).get("nodes", [])
    parents = [d.split(".")[-1] for d in depends_on]
    columns = node.get("columns", {})

    # Classify columns
    keys = [c for c in columns if c.endswith("_sk") or c.endswith("_id") or c.endswith("_key")]
    measures = [c for c in columns if any(c.endswith(s) for s in ("_amount", "_count", "_total", "_sum", "_avg", "_rate"))]
    attributes = [c for c in columns if c not in keys and c not in measures]

    context: dict[str, Any] = {
        "Model": name,
        "Layer": layer_label,
        "Description": node.get("description", "") or "No description",
        "CDM Entity": meta.get("cdm_entity", "Not specified"),
        "Grain": meta.get("grain", "Not documented"),
        "Parents": parents if parents else ["None"],
        "Key Columns": keys if keys else ["None identified"],
        "Measures": measures if measures else ["None"],
        "Attributes": attributes[:15] if attributes else ["None"],
    }

    return context


def _build_suggested_prompt(context: dict) -> str:
    """Generate a suggested Gemini prompt pre-filled with model context."""
    parents_str = ", ".join(context.get("Parents", []))
    return (
        f"I have a dbt {context['Layer'].lower()} model called {context['Model']}.\n"
        f"It consumes: {parents_str}.\n"
        f"CDM entity: {context.get('CDM Entity', 'unknown')}.\n\n"
        f"How should I improve this model's design? "
        f"Consider: grain clarity, join cardinality, test coverage, "
        f"and whether the column classification is correct."
    )


def run_model_summary(selector: str) -> int:
    """Resolve a model and print its LLM-friendly context."""
    from scripts._core.selector import resolve_selector, load_manifest
    from scripts._core.renderers.llm import render_llm_context

    targets = resolve_selector(selector)
    manifest = load_manifest()

    for target in targets:
        node_key = f"model.dcr_analytics.{target.table}"
        node = manifest.get("nodes", {}).get(node_key)
        if node is None:
            print(f"Model {target.table} not found in manifest.")
            continue

        context = build_model_context(node)
        prompt = _build_suggested_prompt(context)
        output = render_llm_context(context, suggested_prompt=prompt)
        print(output)

    return 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/scripts/test_model_context.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/llm_context/model_context.py tests/scripts/test_model_context.py
git commit -m "feat(llm_context): implement model_context for LLM-friendly model summaries"
```

---

### Task 4: Implement `source_context.py` — Source table summary for LLM

**Files:**
- Create: `scripts/llm_context/source_context.py`
- Test: `tests/scripts/test_source_context.py`

- [ ] **Step 1: Write test for source context extraction**

```python
# tests/scripts/test_source_context.py
from scripts.llm_context.source_context import build_source_context


def test_build_source_context_basic():
    """Build context from a manifest source node."""
    node = {
        "name": "reservations",
        "source_name": "vistareserve",
        "schema": "main",
        "description": "Raw reservation data from VistaReserve",
        "columns": {
            "id": {"name": "id", "data_type": "INTEGER"},
            "guest_name": {"name": "guest_name", "data_type": "VARCHAR"},
            "amount": {"name": "amount", "data_type": "DECIMAL"},
        },
    }
    context = build_source_context(node)
    assert context["Source System"] == "vistareserve"
    assert context["Table"] == "reservations"
    assert "id" in str(context["Columns"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/scripts/test_source_context.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement `source_context.py`**

```python
# scripts/llm_context/source_context.py
"""Summarize a dbt source table for LLM consumption."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def build_source_context(node: dict) -> dict[str, Any]:
    """Extract structured context from a manifest source node."""
    columns = node.get("columns", {})
    col_list = []
    for col_name, col_info in columns.items():
        dtype = col_info.get("data_type", "unknown")
        col_list.append(f"{col_name} ({dtype})")

    return {
        "Source System": node.get("source_name", "unknown"),
        "Table": node.get("name", ""),
        "Schema": node.get("schema", ""),
        "Description": node.get("description", "") or "No description",
        "Columns": col_list if col_list else ["No column metadata in manifest"],
    }


def _build_suggested_prompt(context: dict) -> str:
    """Generate a Gemini prompt pre-filled with source context."""
    cols_str = ", ".join(context.get("Columns", [])[:10])
    return (
        f"I have a source table '{context['Table']}' from the "
        f"'{context['Source System']}' system.\n"
        f"Columns: {cols_str}\n\n"
        f"What business entity does this table represent? "
        f"What is the likely grain (what does each row represent)? "
        f"Which columns are candidate primary keys? "
        f"What CDM entity should I map this to in the integration layer?"
    )


def run_source_summary(selector: str) -> int:
    """Resolve a source and print its LLM-friendly context."""
    from scripts._core.selector import resolve_selector, load_manifest
    from scripts._core.renderers.llm import render_llm_context

    targets = resolve_selector(selector)
    manifest = load_manifest()

    for target in targets:
        source_key = f"source.dcr_analytics.{target.schema}.{target.table}"
        node = manifest.get("sources", {}).get(source_key)
        if node is None:
            # Try alternate key format
            for key, val in manifest.get("sources", {}).items():
                if val.get("name") == target.table:
                    node = val
                    break

        if node is None:
            print(f"Source {target.table} not found in manifest.")
            continue

        context = build_source_context(node)
        prompt = _build_suggested_prompt(context)
        output = render_llm_context(context, suggested_prompt=prompt)
        print(output)

    return 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/scripts/test_source_context.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/llm_context/source_context.py tests/scripts/test_source_context.py
git commit -m "feat(llm_context): implement source_context for LLM-friendly source summaries"
```

---

### Task 5: Implement `new_model.py` — Guided intake questionnaire

**Files:**
- Create: `scripts/llm_context/new_model.py`
- Test: `tests/scripts/test_new_model.py`

- [ ] **Step 1: Write test for intake helper functions**

The full intake is interactive (questionary), so test the non-interactive helpers.

```python
# tests/scripts/test_new_model.py
from scripts.llm_context.new_model import (
    classify_entity_behavior,
    build_intake_meta,
    get_existing_models_by_prefix,
)


def test_classify_entity_behavior():
    assert classify_entity_behavior("static reference") == "dimension"
    assert classify_entity_behavior("lifecycle with statuses") == "dimension"
    assert classify_entity_behavior("one-time event/transaction") == "fact"
    assert classify_entity_behavior("point-in-time measurement") == "fact"


def test_build_intake_meta():
    meta = build_intake_meta(
        grain="one row per reservation",
        model_type="fact",
        entity="reservation",
    )
    assert meta["intake_completed"] is True
    assert meta["model_type"] == "fact"
    assert meta["grain"] == "one row per reservation"
    assert "intake_date" in meta


def test_get_existing_models_by_prefix():
    manifest_nodes = {
        "model.dcr_analytics.fct_reservations": {"name": "fct_reservations"},
        "model.dcr_analytics.fct_pos_transactions": {"name": "fct_pos_transactions"},
        "model.dcr_analytics.dim_parks": {"name": "dim_parks"},
        "model.dcr_analytics.int_parks": {"name": "int_parks"},
    }
    facts = get_existing_models_by_prefix(manifest_nodes, "fct_")
    assert len(facts) == 2
    dims = get_existing_models_by_prefix(manifest_nodes, "dim_")
    assert len(dims) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/scripts/test_new_model.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement `new_model.py`**

```python
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
    """Map entity behavior answer to likely model type."""
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
    """Build the meta block for YAML from intake answers."""
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
    """Get model names matching a prefix from manifest nodes."""
    return [
        node["name"]
        for node in manifest_nodes.values()
        if isinstance(node, dict) and node.get("name", "").startswith(prefix)
    ]


def run_new_model() -> int:
    """Run the interactive intake questionnaire."""
    try:
        import questionary
    except ImportError:
        print("Error: questionary is required. Run `pip install questionary`.", file=sys.stderr)
        return 1

    from rich.console import Console
    console = Console()

    console.print("\n[bold]New Model Intake[/bold]")
    console.print("This questionnaire helps you design your model entity-first.\n")

    # Q1: Source data
    source = questionary.text(
        "What data are you working with? (source system and table names)"
    ).ask()
    if source is None:
        return 1

    # Q2: Grain
    grain = questionary.text(
        "What does each row represent? (e.g., 'one reservation', 'one park')"
    ).ask()
    if grain is None:
        return 1

    # Q3: Entity behavior
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

    # Q4: Related entities
    related = questionary.text(
        "Who or what is involved? (related entities, e.g., 'parks, customers, employees')"
    ).ask()

    # Q5: Business questions
    questions = questionary.text(
        "What questions should the data answer? (not report names — business questions)"
    ).ask()

    # Q6: Layer selection
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
        _handle_integration_branch(console, source, grain, related)
    elif "Mart" in layer:
        _handle_mart_branch(console, source, grain, related, suggested_type)
    else:
        _handle_staging_branch(console, source, grain)

    return 0


def _handle_staging_branch(console, source: str, grain: str) -> None:
    """Handle staging layer intake — minimal, just generate YAML snippet."""
    console.print("\n[bold]Staging Model[/bold]")
    console.print("Staging models cast, rename, and return — nothing else.")
    console.print(f"\nGrain: {grain}")
    console.print(f"Source: {source}")
    console.print("\nNext steps:")
    console.print("  1. Create the staging SQL (cast + rename only)")
    console.print("  2. Run: python -m scripts.scaffold tests --select <model>")


def _handle_integration_branch(console, source: str, grain: str, related: str) -> None:
    """Handle integration layer intake — CDM matching + scaffold output."""
    import questionary

    console.print("\n[bold]Integration Model[/bold]")

    # CDM matching
    entity_name = questionary.text(
        "What business entity does this model represent? "
        "(e.g., 'park', 'reservation', 'employee')"
    ).ask()
    if entity_name is None:
        return

    console.print(f"\nSearching CDM for: {entity_name}")
    from scripts.llm_context.cdm_advisor import run_cdm_match
    run_cdm_match(entity_name)

    # Source models
    sources_raw = questionary.text(
        "Which staging models does this integrate? "
        "(comma-separated, e.g., stg_system_a__table, stg_system_b__table)"
    ).ask() or ""
    sources = [s.strip() for s in sources_raw.split(",") if s.strip()]

    key_col = questionary.text("What is the natural primary key column?").ask() or "id"

    meta = build_intake_meta(grain=grain, model_type="integration", entity=entity_name)
    model_name = f"int_{entity_name.lower().replace(' ', '_')}s"

    # Generate scaffold
    if sources:
        from scripts.scaffold.integration_scaffold import generate_integration_sql, generate_integration_yaml
        sql = generate_integration_sql(model_name, entity_name, sources, key_col)
        yaml_str = generate_integration_yaml(model_name, entity_name, grain, key_col)

        console.print(f"\n[bold]Generated SQL skeleton → copy to models/integration/{model_name}.sql[/bold]")
        console.print(sql[:600] + "..." if len(sql) > 600 else sql)

        console.print(f"\n[bold]Generated YAML → add to your _models.yml[/bold]")
        console.print(yaml_str)

    # LLM context block
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
    console, source: str, grain: str, related: str, suggested_type: str,
) -> None:
    """Handle mart layer intake — fact/dim/report classification."""
    import questionary

    model_type = questionary.select(
        "What kind of mart model is this?",
        choices=[
            "A business event that happened (transaction, booking, inspection) → FACT",
            "A descriptive entity (a park, a person, an asset, a date) → DIMENSION",
            "A summary that combines multiple facts or aggregates to a different grain → REPORT",
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


def _handle_fact_intake(console, grain: str, related: str) -> None:
    """Fact model intake — check for duplicate facts, suggest dimensions."""
    import questionary

    console.print("\n[bold]Fact Model Design[/bold]")

    # Check existing facts
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
                console.print("→ You may need a REPORT model that aggregates the existing fact.")
                return
    except Exception:
        pass

    # Dimension suggestions
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
                    console.print(f"  ✓ {cat}: join via {matching[0]}")
                else:
                    console.print(f"  ⚠ {cat}: no existing dimension found — consider building one first")
        except Exception:
            pass

    meta = build_intake_meta(grain=grain, model_type="fact")
    console.print(f"\n[dim]YAML meta:[/dim] {meta}")


def _handle_dimension_intake(console, grain: str) -> None:
    """Dimension model intake."""
    console.print("\n[bold]Dimension Model Design[/bold]")
    console.print("Dimensions describe entities. They have a surrogate key and descriptive attributes.")
    meta = build_intake_meta(grain=grain, model_type="dimension")
    console.print(f"\n[dim]YAML meta:[/dim] {meta}")


def _handle_report_intake(console, grain: str) -> None:
    """Report model intake — verify it combines facts or changes grain."""
    import questionary

    console.print("\n[bold]Report Model Design[/bold]")
    console.print("Reports earn their place when they combine multiple facts or aggregate to a different grain.")

    agg_grain = questionary.text(
        "What grain does the report aggregate to? (e.g., 'park + month')"
    ).ask()

    meta = build_intake_meta(grain=agg_grain or grain, model_type="report")
    console.print(f"\n[dim]YAML meta:[/dim] {meta}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/Scripts/activate && PYTHONUTF8=1 python -m pytest tests/scripts/test_new_model.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/llm_context/new_model.py tests/scripts/test_new_model.py
git commit -m "feat(llm_context): implement new_model guided intake questionnaire"
```
