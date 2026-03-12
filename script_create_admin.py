import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import ALL models so SQLAlchemy can resolve cross-model relationships
from app.models import farm, crop, plant, alert, gamification  # noqa: F401
from app.models.user import Farmer, Admin  # noqa: F401
from app.core.database import SessionLocal, init_db
from app.core.security import get_password_hash
import uuid

# ─── Credentials ───────────────────────────────────
ADMIN_ID = "T12478"
ADMIN_NAME = "Ram"
ADMIN_PASSWORD = "Offcial@12897"
# ───────────────────────────────────────────────────

def create_admin():
    init_db()  # Ensure all tables exist (including 'admins')
    db = SessionLocal()

    try:
        existing = db.query(Admin).filter(Admin.admin_id == ADMIN_ID).first()
        if existing:
            print(f"✅ Admin '{ADMIN_ID}' already exists. No changes made.")
            return

        admin = Admin(
            id=str(uuid.uuid4()),
            admin_id=ADMIN_ID,
            name=ADMIN_NAME,
            password_hash=get_password_hash(ADMIN_PASSWORD),
            is_active=True
        )
        db.add(admin)
        db.commit()
        print(f"✅ Admin created successfully!")
        print(f"   Admin ID  : {ADMIN_ID}")
        print(f"   Name      : {ADMIN_NAME}")
        print(f"   Password  : {ADMIN_PASSWORD}")
        print(f"   Login URL : http://localhost:8000/admin")
    except Exception as e:
        db.rollback()
        print(f"❌ Error creating admin: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    create_admin()
