#!/usr/bin/env python3
import sys
import argparse
from pathlib import Path
import pandas as pd
import re
import textwrap
import difflib

def fuzzy_match_text(text, keyword, cutoff=0.8):
    if " " in keyword or len(keyword) <= 3:
        return keyword in text
    if keyword in text:
        return True
        
    words = set(re.findall(r'[a-z0-9]+', text))
    # Filter out very short words from the text to avoid noisy matches on things like 'id', 'of', 'in', 'to'
    words = {w for w in words if len(w) > 3}
    return bool(difflib.get_close_matches(keyword, words, n=1, cutoff=cutoff))

def main():
    parser = argparse.ArgumentParser(description="Search CDM catalogs by keywords in names, descriptions, and semantic meanings.")
    parser.add_argument("keywords", nargs="+", help="Keywords to search for (case-insensitive). By default, finding any keyword is a match.")
    parser.add_argument("--all", action="store_true", help="Require ALL keywords to match a row instead of ANY keyword.")
    parser.add_argument("--entity", type=str, help="Filter results to a specific CDM entity name.")
    parser.add_argument("--exact", action="store_true", help="Require exact substring matches (disables fuzzy matching).")
    parser.add_argument("--cutoff", type=float, default=0.8, help="Fuzzy match threshold (0.0 to 1.0, default: 0.8).")
    parser.add_argument("--output", type=str, help="Optional file path to save the output instead of only printing to the console.")
    args = parser.parse_args()

    project_root = Path(__file__).parent.parent
    catalogs_dir = project_root / "source_data" / "cdm_metadata" / "columns"
    entities_dir = project_root / "source_data" / "cdm_metadata" / "entities"
    
    if not catalogs_dir.exists():
        print(f"Error: CDM catalogs directory not found at {catalogs_dir}")
        sys.exit(1)

    entity_desc_map = {}
    if entities_dir.exists():
        entity_csv_files = list(entities_dir.glob("*.csv"))
        entity_df_list = []
        for filepath in entity_csv_files:
            try:
                df = pd.read_csv(filepath, dtype=str)
                entity_df_list.append(df)
            except Exception:
                pass
        
        if entity_df_list:
            entity_df = pd.concat(entity_df_list, ignore_index=True)
            if 'cdm_entity_name' in entity_df.columns and 'description' in entity_df.columns:
                valid_entities = entity_df.dropna(subset=['cdm_entity_name', 'description'])
                valid_entities = valid_entities[valid_entities['description'].str.strip() != '']
                entity_desc_map = valid_entities.groupby('cdm_entity_name')['description'].first().to_dict()

    csv_files = list(catalogs_dir.glob("*.csv"))
    if not csv_files:
        print(f"Error: No CSV files found in {catalogs_dir}")
        sys.exit(1)

    df_list = []
    for filepath in csv_files:
        try:
            df = pd.read_csv(filepath, dtype=str)
            df_list.append(df)
        except Exception as e:
            print(f"Warning: Could not read {filepath.name}: {e}")

    if not df_list:
        sys.exit(1)

    catalog_df = pd.concat(df_list, ignore_index=True)
    
    # Map entity descriptions into the catalog dataframe
    catalog_df['entity_description'] = catalog_df['cdm_entity_name'].map(entity_desc_map).fillna('')
    
    # Filter only available columns from our desired list
    cols_to_search = ["cdm_entity_name", "cdm_attribute_name", "cdm_display_name", "description", "cdm_semantic_meanings", "entity_description"]
    valid_cols = [c for c in cols_to_search if c in catalog_df.columns]
    
    catalog_df[valid_cols] = catalog_df[valid_cols].fillna("")

    # Combine searchable text into one column for easy searching
    catalog_df["search_text"] = catalog_df[valid_cols].agg(lambda x: ' | '.join(x.values), axis=1).str.lower()
    
    keywords = [k.lower() for k in args.keywords]
    
    def process_keyword(kw):
        if args.exact:
            return catalog_df["search_text"].str.contains(re.escape(kw), regex=True)
        else:
            return catalog_df["search_text"].apply(lambda x: fuzzy_match_text(x, kw, args.cutoff))

    if args.all:
        mask = pd.Series([True] * len(catalog_df))
        for kw in keywords:
            mask = mask & process_keyword(kw)
    else:
        mask = pd.Series([False] * len(catalog_df))
        for kw in keywords:
            mask = mask | process_keyword(kw)
    if args.entity:
        mask = mask & (catalog_df["cdm_entity_name"].str.lower() == args.entity.lower())
        
    results = catalog_df[mask]
    
    if results.empty:
        print(f"No matches found for keywords: {', '.join(args.keywords)}")
        sys.exit(0)
        
    output_lines = []
    def log_print(text=""):
        print(text)
        output_lines.append(str(text))
        
    # Count matches per entity and sort them
    entity_counts = results['cdm_entity_name'].value_counts()
    sorted_entities = entity_counts.index.tolist()
    
    log_print(f"Found {len(results)} matching columns across {len(sorted_entities)} entities.")
    log_print("Entities are ranked by number of matched columns.\n")
    
    for entity in sorted_entities:
        group = results[results['cdm_entity_name'] == entity]
        
        manifest_col = group.get('cdm_manifest', pd.Series(dtype=str))
        manifests = [str(m) for m in manifest_col.unique() if pd.notna(m) and str(m).strip()]
        manifest_str = ", ".join(manifests) if manifests else "Unknown"
        
        log_print(f"=== Entity: {entity} [Manifest: {manifest_str}] ({len(group)} matches) ===")
        ent_desc = entity_desc_map.get(entity, "")
        if ent_desc:
            wrapped_ent_desc = textwrap.fill(ent_desc, width=90, initial_indent="  Entity Desc: ", subsequent_indent="               ")
            log_print(wrapped_ent_desc)
            log_print()
            
        for _, row in group.iterrows():
            attr = row.get("cdm_attribute_name", "Unknown")
            desc = row.get("description", "")
            semantic = row.get("cdm_semantic_meanings", "")
            
            log_print(f"  • {attr}")
            if desc:
                wrapped_desc = textwrap.fill(desc, width=90, initial_indent="    Desc: ", subsequent_indent="          ")
                log_print(wrapped_desc)
            if semantic:
                log_print(f"    Semantic: {semantic}")
        log_print()

    if args.output:
        out_path = Path(args.output)
        # Ensure parent directory exists
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("\n".join(output_lines), encoding="utf-8")
        print(f"Results successfully saved to {out_path.absolute()}")

if __name__ == "__main__":
    main()
