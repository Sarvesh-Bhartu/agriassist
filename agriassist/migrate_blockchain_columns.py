"""
migrate_blockchain_columns.py
Adds blockchain verification columns to the existing 'farms' table.
Safe to run multiple times — uses IF NOT EXISTS for each column.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import engine
from sqlalchemy import text

COLUMNS = [
    ("land_hash",               "VARCHAR(66)"),
    ("blockchain_tx_hash",      "VARCHAR(66)"),
    ("blockchain_block_number", "VARCHAR(20)"),
    ("blockchain_status",       "VARCHAR(20)"),
    ("blockchain_verified_at",  "TIMESTAMP"),
    ("blockchain_error",        "VARCHAR(500)"),
]

def run_migration():
    print("Running blockchain columns migration on farms table...")
    with engine.connect() as conn:
        for col_name, col_type in COLUMNS:
            sql = text(f"""
                ALTER TABLE farms
                ADD COLUMN IF NOT EXISTS {col_name} {col_type};
            """)
            conn.execute(sql)
            print(f"   OK: Column '{col_name}' ({col_type}) -- added or already exists")
        conn.commit()
    print("\nMigration complete! All blockchain columns are now on the farms table.")

if __name__ == "__main__":
    run_migration()
