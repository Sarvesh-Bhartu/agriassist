import sys
import os
sys.path.append(r'd:\agriassist-a9759e7e6d5a4d10620dd880a973ce02a5c80086\agriassist-a9759e7e6d5a4d10620dd880a973ce02a5c80086')

from sqlalchemy import create_engine, text
from app.core.config import settings

def get_farm_coords():
    try:
        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT name, polygon_coordinates FROM farms LIMIT 1"))
            row = result.fetchone()
            if row:
                print(f"Farm: {row[0]}, Coords: {row[1]}")
            else:
                print("No farms found.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    get_farm_coords()
