import sys
import os
sys.path.append(r'd:\agriassist-a9759e7e6d5a4d10620dd880a973ce02a5c80086\agriassist-a9759e7e6d5a4d10620dd880a973ce02a5c80086')

from sqlalchemy import create_engine, text
from app.core.config import settings

def check_new_alerts():
    try:
        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT id, title, latitude, longitude, created_at 
                FROM alerts 
                ORDER BY created_at DESC 
                LIMIT 5
            """))
            rows = result.fetchall()
            print(f"Recent alerts: {len(rows)}")
            for row in rows:
                print(row)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_new_alerts()
