#!/usr/bin/env python3
"""
Export mart model data to CSV and/or Parquet formats.

This script connects to the DuckDB target database and exports all mart model
tables to the output/ directory. Supports selective export via --select flag.

Usage:
    python scripts/export_mart_data.py [--format csv|parquet|both] [--select model_name]
"""

import argparse
import sys
from pathlib import Path

import duckdb


def export_mart_data(db_path, format="both", select=None):
    """
    Export mart model data to CSV and/or Parquet.

    Args:
        db_path: Path to the DuckDB database file
        format: 'csv', 'parquet', or 'both'
        select: Optional model name to export (if None, export all marts)
    """
    # Connect to DuckDB
    conn = duckdb.connect(db_path)

    # Discover mart model names from the models/marts/ directory
    marts_dir = Path("models/marts")
    if not marts_dir.exists():
        print("❌ models/marts/ directory not found")
        return False

    all_mart_names = {p.stem for p in marts_dir.rglob("*.sql")}

    # Filter to those that exist as tables in the database
    existing = {
        row[0]
        for row in conn.execute(
            "select table_name from information_schema.tables where table_schema = 'main'"
        ).fetchall()
    }
    mart_tables = sorted(all_mart_names & existing)

    if not mart_tables:
        print("❌ No mart tables found in database (run 'dbt build' first)")
        return False

    if select:
        mart_tables = [t for t in mart_tables if t == select]
        if not mart_tables:
            print(f"❌ Mart model '{select}' not found in database")
            return False

    # Create output directory
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    # Export each mart table
    success_count = 0
    for table_name in mart_tables:
        try:
            df = conn.execute(f"select * from {table_name}").df()
            model_name = table_name.replace("main_marts_", "")

            if format in ("csv", "both"):
                csv_path = output_dir / f"{model_name}.csv"
                df.to_csv(csv_path, index=False)
                print(f"✓ {model_name}: {len(df)} rows → {csv_path}")

            if format in ("parquet", "both"):
                parquet_path = output_dir / f"{model_name}.parquet"
                df.to_parquet(parquet_path, index=False)
                if format == "both":
                    print(f"                     → {parquet_path}")

            success_count += 1

        except Exception as e:
            print(f"✗ {table_name}: {e}")

    conn.close()

    print(f"\n✓ Exported {success_count}/{len(mart_tables)} mart models to {output_dir}/")
    return success_count > 0


def main():
    parser = argparse.ArgumentParser(
        description="Export dbt mart model data to CSV and/or Parquet"
    )
    parser.add_argument(
        "--format",
        choices=["csv", "parquet", "both"],
        default="both",
        help="Output format (default: both)",
    )
    parser.add_argument(
        "--select",
        help="Export specific mart model (default: all)",
    )

    args = parser.parse_args()

    db_path = Path("target") / "dcr_analytics.duckdb"
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        print("   Run 'dbt build' first to create the database")
        return 1

    success = export_mart_data(str(db_path), format=args.format, select=args.select)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
