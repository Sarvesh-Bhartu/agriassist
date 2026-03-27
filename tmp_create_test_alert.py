import sys
import os
sys.path.append(r'd:\agriassist-a9759e7e6d5a4d10620dd880a973ce02a5c80086\agriassist-a9759e7e6d5a4d10620dd880a973ce02a5c80086')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Import all models to ensure registry is populated
from app.models.user import Farmer
from app.models.farm import Farm
from app.models.plant import PlantDetection
from app.models.alert import Alert, AlertDelivery

def create_test_alert():
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    # Coordinates from the screenshot area (near Panval/ratnagiri)
    test_alert = Alert(
        alert_type='Disease',
        severity='High',
        title='Test Invasive Species Alert',
        message='This is a dummy alert for testing the map rendering.',
        latitude=18.5338,
        longitude=73.1038,
        radius_km=5,
        is_active=True
    )
    
    db.add(test_alert)
    db.commit()
    print(f"✅ Created test alert: {test_alert.id}")
    db.close()

if __name__ == "__main__":
    create_test_alert()
