#!/usr/bin/env python3
"""
inspect_source.py

A utility script to inspect data sources (DuckDB or BigQuery) before staging.
This tool helps analysts understand table schemas and data characteristics.

Usage:
  python scripts/inspect_source.py --type duckdb --conn path/to.duckdb
  python scripts/inspect_source.py --type bigquery --conn my-project.my_dataset
  python scripts/inspect_source.py --type duckdb --conn path/to.duckdb --table my_table
"""

import argparse
import sys
import pandas as pd


def print_header(title: str):
    print(f"\n{'=' * 80}")
    print(f" {title.upper()}")
    print(f"{'=' * 80}")


def inspect_duckdb(conn_path: str, schema: str = None, table: str = None):
    try:
        import duckdb
    except ImportError:
        print("Error: duckdb package is not installed. Run `pip install duckdb`.")
        sys.exit(1)

    print(f"Connecting to DuckDB: {conn_path}")
    con = duckdb.connect(conn_path, read_only=True)

    try:
        if not table:
            # Database/Schema Level Inspection
            print_header("Tables Overview")
            
            schema_filter = f"WHERE table_schema = '{schema}'" if schema else ""
            query = f"""
                SELECT 
                    table_schema, 
                    table_name, 
                    table_type
                FROM information_schema.tables
                {schema_filter}
                ORDER BY table_schema, table_name
            """
            
            tables_df = con.query(query).df()
            
            if tables_df.empty:
                print("No tables found.")
                return
                
            print(f"Found {len(tables_df)} table(s).")
            print("-" * 40)
            
            # Get column counts for each table
            for _, row in tables_df.iterrows():
                t_schema = row['table_schema']
                t_name = row['table_name']
                t_type = row['table_type']
                
                col_query = f"""
                    SELECT count(*) as col_count 
                    FROM information_schema.columns 
                    WHERE table_schema = '{t_schema}' AND table_name = '{t_name}'
                """
                col_count = con.query(col_query).fetchone()[0]
                
                print(f"[{t_type}] {t_schema}.{t_name} ({col_count} columns)")
                
            print(f"\nTip: Run with `--table <table_name>` to inspect a specific table.")
            
        else:
            # Table Level Inspection
            schema_prefix = f"{schema}." if schema else ""
            full_table_name = f"{schema_prefix}{table}"
            
            print_header(f"Inspecting Table: {full_table_name}")
            
            # Fetch complete table metadata
            count_query = f"SELECT count(*) as total_rows FROM {full_table_name}"
            
            try:
                total_rows = con.query(count_query).fetchone()[0]
            except duckdb.Error as e:
                print(f"Error querying table {full_table_name}: {e}")
                return
                
            if total_rows == 0:
                print(f"Table {full_table_name} is empty.")
                return
            
            # Get full column list
            # We use DESCRIBE or query information_schema to get all columns
            describe_query = f"DESCRIBE {full_table_name}"
            try:
                columns_df = con.query(describe_query).df()
            except duckdb.Error as e:
                print(f"Error describing table {full_table_name}: {e}")
                return
                
            print(f"Total Rows in Table: {total_rows}")
            print(f"Total Columns: {len(columns_df)}")
            print("\n--- Column Schema ---")
            print(columns_df[['column_name', 'column_type']].to_string(index=False))
            
            # Fetch a sample
            sample_query = f"SELECT * FROM {full_table_name} LIMIT 1000"
            df = con.query(sample_query).df()
                
            print(f"\nSampled {len(df)} rows.")
            print("\n--- DataFrame Info ---")
            
            # df.info() prints to standard output by default
            df.info(verbose=True, show_counts=True)
            
            print("\n--- Uniqueness & Cardinality (Sample) ---")
            unique_counts = df.nunique()
            uniqueness_pct = (unique_counts / len(df)) * 100
            
            cardinality_df = pd.DataFrame({
                'Distinct Values': unique_counts, 
                'Uniqueness %': uniqueness_pct
            })
            
            # Flag potential primary keys (100% unique)
            potential_pks = cardinality_df[cardinality_df['Uniqueness %'] == 100].index.tolist()
            if potential_pks:
                print(f"Potential Primary Keys (100% unique in sample): {', '.join(potential_pks)}\n")
            
            # Print low cardinality values (<= 10 distinct values)
            low_card_cols = cardinality_df[(cardinality_df['Distinct Values'] > 0) & (cardinality_df['Distinct Values'] <= 10)]
            if not low_card_cols.empty:
                print("Low Cardinality Columns (Potential Enums/Booleans):")
                for col in low_card_cols.index:
                    counts = df[col].value_counts(dropna=False).to_dict()
                    print(f"  - {col}: {counts}")
            else:
                print("No low cardinality columns found.")
                
            print("\n--- Empty Strings & Whitespace (String Columns) ---")
            str_cols = df.select_dtypes(include=['object', 'string']).columns
            issue_found = False
            for col in str_cols:
                # Handle possible non-string values gracefully
                mask_str = df[col].apply(lambda x: isinstance(x, str))
                if not mask_str.any(): continue
                
                empty_str_count = (df.loc[mask_str, col] == '').sum()
                whitespace_count = df.loc[mask_str, col].str.contains(r'^\s+|\s+$', regex=True, na=False).sum()
                
                if empty_str_count > 0 or whitespace_count > 0:
                    issue_found = True
                    print(f"  - {col}: {empty_str_count} empty strings (\"\"), {whitespace_count} values with leading/trailing whitespace")
            
            if not issue_found:
                 print("No empty strings or padded whitespace detected in sample.")

            print("\n--- Date/Time Bounds (Sample) ---")
            date_cols = df.select_dtypes(include=['datetime', 'datetimetz']).columns
            if not date_cols.empty:
                for col in date_cols:
                    print(f"  - {col}: Min = {df[col].min()}, Max = {df[col].max()}")
            else:
                print("No datetime columns found in sample to bound.")

            print("\n--- Null Counts (Top 10) ---")
            null_counts = df.isnull().sum()
            null_pct = (null_counts / len(df)) * 100
            null_df = pd.DataFrame({'Null Count': null_counts, 'Null %': null_pct})
            null_df = null_df[null_df['Null Count'] > 0].sort_values(by='Null Count', ascending=False).head(10)
            
            if null_df.empty:
                print("No null values found in sample.")
            else:
                print(null_df.to_string(formatters={'Null %': '{:.2f}%'.format}))
            
            print("\n--- Sample Data (Head 5) ---")
            pd.set_option('display.max_columns', None)
            pd.set_option('display.width', 1000)
            print(df.head(5))

    finally:
        con.close()


def inspect_bigquery(conn_str: str, schema: str = None, table: str = None):
    try:
        from google.cloud import bigquery
    except ImportError:
        print("Error: google-cloud-bigquery package is not installed. Run `pip install google-cloud-bigquery`.")
        sys.exit(1)

    print(f"Connecting to BigQuery")
    client = bigquery.Client()
    
    # Parse conn_str which could be project.dataset
    parts = conn_str.split('.')
    if len(parts) >= 2:
        project = parts[0]
        dataset = parts[1]
    else:
        # Assume it's just a dataset in the default project
        project = client.project
        dataset = parts[0]
        
    print(f"Project: {project}, Dataset: {dataset}")
    
    try:
        if not table:
            # Database/Schema Level Inspection
            print_header("Tables Overview")
            
            query = f"""
                SELECT table_name, table_type
                FROM `{project}.{dataset}.INFORMATION_SCHEMA.TABLES`
                ORDER BY table_name
            """
            
            try:
                tables_df = client.query(query).to_dataframe()
            except Exception as e:
                print(f"Error querying INFORMATION_SCHEMA: {e}")
                return
                
            if tables_df.empty:
                print("No tables found.")
                return
                
            print(f"Found {len(tables_df)} table(s).")
            print("-" * 40)
            
            # Get column info
            col_query = f"""
                SELECT table_name, count(*) as col_count
                FROM `{project}.{dataset}.INFORMATION_SCHEMA.COLUMNS`
                GROUP BY table_name
            """
            cols_df = client.query(col_query).to_dataframe()
            
            # Join for display
            merged_df = pd.merge(tables_df, cols_df, on='table_name', how='left')
            
            for _, row in merged_df.iterrows():
                t_name = row['table_name']
                t_type = row['table_type']
                col_count = row['col_count']
                print(f"[{t_type}] {dataset}.{t_name} ({col_count} columns)")
                
            print(f"\nTip: Run with `--table <table_name>` to inspect a specific table.")
            
        else:
            # Table Level Inspection
            full_table_name = f"{project}.{dataset}.{table}"
            print_header(f"Inspecting Table: {full_table_name}")
            
            # Fetch complete table metadata
            count_query = f"SELECT count(*) as total_rows FROM `{full_table_name}`"
            
            try:
                count_df = client.query(count_query).to_dataframe()
                total_rows = count_df.iloc[0]['total_rows']
            except Exception as e:
                print(f"Error querying table {full_table_name}: {e}")
                return
                
            if total_rows == 0:
                print(f"Table {full_table_name} is empty.")
                return
                
            # Get full column list
            columns_query = f"""
                SELECT column_name, data_type 
                FROM `{project}.{dataset}.INFORMATION_SCHEMA.COLUMNS`
                WHERE table_name = '{table}'
                ORDER BY ordinal_position
            """
            try:
                columns_df = client.query(columns_query).to_dataframe()
            except Exception as e:
                print(f"Error fetching columns for {full_table_name}: {e}")
                return
                
            print(f"Total Rows in Table: {total_rows}")
            print(f"Total Columns: {len(columns_df)}")
            print("\n--- Column Schema ---")
            print(columns_df.to_string(index=False))
            
            # Fetch a sample
            sample_query = f"SELECT * FROM `{full_table_name}` LIMIT 1000"
            df = client.query(sample_query).to_dataframe()
            
            print(f"\nSampled {len(df)} rows.")
            print("\n--- DataFrame Info ---")
            
            df.info(verbose=True, show_counts=True)
            
            print("\n--- Uniqueness & Cardinality (Sample) ---")
            unique_counts = df.nunique()
            uniqueness_pct = (unique_counts / len(df)) * 100
            
            cardinality_df = pd.DataFrame({
                'Distinct Values': unique_counts, 
                'Uniqueness %': uniqueness_pct
            })
            
            # Flag potential primary keys (100% unique)
            potential_pks = cardinality_df[cardinality_df['Uniqueness %'] == 100].index.tolist()
            if potential_pks:
                print(f"Potential Primary Keys (100% unique in sample): {', '.join(potential_pks)}\n")
            
            # Print low cardinality values (<= 10 distinct values)
            low_card_cols = cardinality_df[(cardinality_df['Distinct Values'] > 0) & (cardinality_df['Distinct Values'] <= 10)]
            if not low_card_cols.empty:
                print("Low Cardinality Columns (Potential Enums/Booleans):")
                for col in low_card_cols.index:
                    counts = df[col].value_counts(dropna=False).to_dict()
                    print(f"  - {col}: {counts}")
            else:
                print("No low cardinality columns found.")
                
            print("\n--- Empty Strings & Whitespace (String Columns) ---")
            str_cols = df.select_dtypes(include=['object', 'string']).columns
            issue_found = False
            for col in str_cols:
                mask_str = df[col].apply(lambda x: isinstance(x, str))
                if not mask_str.any(): continue
                
                empty_str_count = (df.loc[mask_str, col] == '').sum()
                whitespace_count = df.loc[mask_str, col].str.contains(r'^\s+|\s+$', regex=True, na=False).sum()
                
                if empty_str_count > 0 or whitespace_count > 0:
                    issue_found = True
                    print(f"  - {col}: {empty_str_count} empty strings (\"\"), {whitespace_count} values with leading/trailing whitespace")
            
            if not issue_found:
                 print("No empty strings or padded whitespace detected in sample.")

            print("\n--- Date/Time Bounds (Sample) ---")
            date_cols = df.select_dtypes(include=['datetime', 'datetimetz']).columns
            if not date_cols.empty:
                for col in date_cols:
                    print(f"  - {col}: Min = {df[col].min()}, Max = {df[col].max()}")
            else:
                print("No datetime columns found in sample to bound.")
            
            print("\n--- Null Counts (Top 10) ---")
            null_counts = df.isnull().sum()
            null_pct = (null_counts / len(df)) * 100
            null_df = pd.DataFrame({'Null Count': null_counts, 'Null %': null_pct})
            null_df = null_df[null_df['Null Count'] > 0].sort_values(by='Null Count', ascending=False).head(10)
            
            if null_df.empty:
                print("No null values found in sample.")
            else:
                print(null_df.to_string(formatters={'Null %': '{:.2f}%'.format}))
            
            print("\n--- Sample Data (Head 5) ---")
            pd.set_option('display.max_columns', None)
            pd.set_option('display.width', 1000)
            print(df.head(5))

    except Exception as e:
         print(f"An unexpected error occurred: {e}")


def main():
    import warnings
    warnings.warn(
        "scripts.inspect is deprecated and will be removed in a future release. "
        "Use 'python -m scripts.profiler' instead.",
        DeprecationWarning,
        stacklevel=1,
    )

    parser = argparse.ArgumentParser(description="Inspect a data source system before staging.")
    parser.add_argument("--type", choices=["duckdb", "bigquery"], required=True, 
                        help="The type of the source database system.")
    parser.add_argument("--conn", required=True, 
                        help="Connection string: path to .duckdb file or BigQuery project.dataset string.")
    parser.add_argument("--schema", required=False, 
                        help="Optional schema to filter by (for DuckDB).")
    parser.add_argument("--table", required=False, 
                        help="Optional table to deeply inspect.")
    
    args = parser.parse_args()
    
    if args.type == "duckdb":
        inspect_duckdb(args.conn, args.schema, args.table)
    elif args.type == "bigquery":
        inspect_bigquery(args.conn, args.schema, args.table)


if __name__ == "__main__":
    main()
