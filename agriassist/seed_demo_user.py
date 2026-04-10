"""
Script to seed demo user into the database
Demo credentials:
  Phone: +91 9876543210
  Password: Demo@123
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal, init_db
from app.core.security import get_password_hash
from app.models.user import Farmer
from app.models import farm, plant, crop, alert, gamification  # Import all models to avoid FK errors
from datetime import datetime

def seed_demo_user():
    """Create demo user in database"""
    # Initialize database tables
    init_db()
    
    db = SessionLocal()
    
    try:
        # Check if demo user already exists
        existing_user = db.query(Farmer).filter(Farmer.phone == "+919876543210").first()
        
        if existing_user:
            print("✅ Demo user already exists!")
            print(f"   Phone: +919876543210")
            print(f"   Password: Demo@123")
            return
        
        # Hash password using passlib (same as auth endpoint)
        password = "Demo@123"
        password_hash = get_password_hash(password)
        
        # Create demo farmer
        demo_farmer = Farmer(
            phone="+919876543210",
            name="Demo Farmer",
            email="demo@agrigravity.com",
            password_hash=password_hash,
            district="Demo District",
            state="Demo State",
            latitude=20.5937,  # India center coordinates
            longitude=78.9629,
            badges=["early_adopter", "soil_specialist"],
            is_active=True,
            total_points=150
        )
        
        db.add(demo_farmer)
        db.commit()
        db.refresh(demo_farmer)
        
        print("✅ Demo user created successfully!")
        print("\n📱 Login Credentials:")
        print("   Phone: +919876543210")
        print("   Password: Demo@123")
        print(f"\n👤 User ID: {demo_farmer.id}")
        print(f"   Name: {demo_farmer.name}")
        print(f"   Email: {demo_farmer.email}")
        print(f"   Location: {demo_farmer.district}, {demo_farmer.state}")
        print(f"   Points: {demo_farmer.total_points}")
        print(f"   Badges: {', '.join(demo_farmer.badges)}")
        
    except Exception as e:
        print(f"❌ Error creating demo user: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_user()
