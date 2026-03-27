import sys
import os
import uuid
from datetime import datetime, timedelta
sys.path.append(r'd:\agriassist-a9759e7e6d5a4d10620dd880a973ce02a5c80086\agriassist-a9759e7e6d5a4d10620dd880a973ce02a5c80086')

from sqlalchemy import create_engine, text
from app.core.config import settings

def create_test_alert_raw():
    try:
        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as conn:
            # Create a UUID for the alert
            alert_id = str(uuid.uuid4())
            now = datetime.utcnow()
            expires = now + timedelta(days=7)
            
            # Use raw SQL to insert
            query = text("""
                INSERT INTO alerts (id, alert_type, severity, title, message, latitude, longitude, radius_km, created_at, expires_at, is_active)
                VALUES (:id, :type, :severity, :title, :msg, :lat, :lon, :radius, :created, :expires, :active)
            """)
            
            conn.execute(query, {
                "id": alert_id,
                "type": "Invasive Species",
                "severity": "High",
                "title": "TEST: Parthenium Hysterophorus Detected",
                "msg": "Invasive species detected near Chran farms east. 5km alert zone active.",
                "lat": 18.8943,
                "lon": 73.1752,
                "radius": 5,
                "created": now,
                "expires": expires,
                "active": True
            })
            conn.commit()
            print(f"✅ Successfully created test alert: {alert_id}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    create_test_alert_raw()
