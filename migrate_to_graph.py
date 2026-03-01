import sys
import os

# Ensure the app directory is in the path so we can import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.models.user import Farmer
from app.models.farm import Farm
import app.models.crop
import app.models.plant
import app.models.alert
import app.models.gamification
from app.services.graph_service import graph_service
from app.core.neo4j_driver import neo4j_driver

def migrate_data():
    print("🚀 Starting Data Migration: SQLite -> Neo4j...")
    
    # 1. Connect to both databases
    try:
        neo4j_driver.connect()
    except Exception as e:
        print(f"❌ Could not connect to Neo4j. Is the graph database running? Error: {e}")
        return

    db = SessionLocal()
    
    try:
        # 2. Migrate Farmers (Circles)
        farmers = db.query(Farmer).all()
        print(f"📦 Found {len(farmers)} farmers in SQLite. Syncing to Neo4j Nodes...")
        for farmer in farmers:
            graph_service.create_farmer_node(
                farmer_id=farmer.id,
                phone=farmer.phone,
                name=farmer.name,
                district=farmer.district,
                state=farmer.state
            )
        
        # 3. Migrate Farms (Circles)
        farms = db.query(Farm).all()
        print(f"📦 Found {len(farms)} farms in SQLite. Syncing to Neo4j Nodes...")
        for farm in farms:
            # SQLAlchemy decimals conversion
            area = float(farm.area_hectares) if farm.area_hectares else None
            graph_service.create_farm_node(
                farm_id=farm.id,
                name=farm.name or "Unnamed Farm",
                area_hectares=area,
                soil_type=farm.soil_type
            )
            
            # 4. Link Farmers to Farms (Arrows)
            if farm.farmer_id:
                graph_service.link_farmer_to_farm(
                    farmer_id=farm.farmer_id,
                    farm_id=farm.id
                )
                
        print("✅ Graph Migration Completed Successfully!")
        
    except Exception as e:
        print(f"❌ Migration failed with error: {e}")
    finally:
        db.close()
        neo4j_driver.close()

if __name__ == "__main__":
    migrate_data()
