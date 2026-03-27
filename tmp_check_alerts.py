import sys
import os

# Add the project root to sys.path
sys.path.append(r'd:\agriassist-a9759e7e6d5a4d10620dd880a973ce02a5c80086\agriassist-a9759e7e6d5a4d10620dd880a973ce02a5c80086')

from sqlalchemy import create_engine
from app.core.config import settings
from app.models.alert import Alert
from sqlalchemy.orm import sessionmaker

def check_alerts():
    from sqlalchemy import create_engine
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    alerts = db.query(Alert).all()
    print(f"Total alerts: {len(alerts)}")
    for a in alerts:
        print(f"ID: {a.id}, Title: {a.title}, Lat: {a.latitude}, Lon: {a.longitude}, Type: {a.alert_type}")
    
    db.close()

if __name__ == "__main__":
    check_alerts()
