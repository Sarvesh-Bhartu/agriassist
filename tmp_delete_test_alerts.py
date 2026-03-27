import sys
import os
sys.path.append(r'd:\agriassist-a9759e7e6d5a4d10620dd880a973ce02a5c80086\agriassist-a9759e7e6d5a4d10620dd880a973ce02a5c80086')

from sqlalchemy import create_engine, text
from app.core.config import settings

def delete_test_alerts():
    try:
        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as conn:
            # Delete alerts with "TEST:" in title or just all alerts if this is a clean dev env
            # The user said the table was empty before, so deleting all is probably safe, 
            # but I'll be specific to my test alert.
            query = text("DELETE FROM alerts WHERE title LIKE 'TEST:%'")
            result = conn.execute(query)
            conn.commit()
            print(f"✅ Deleted {result.rowcount} test alerts.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    delete_test_alerts()
