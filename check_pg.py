import os
from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine(os.getenv("DATABASE_URL"))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

from sqlalchemy import text

def check_pg():
    db = SessionLocal()
    
    print("--- POSTGRES FARMERS ---")
    farmers = db.execute(text("SELECT id, name, phone FROM farmers")).fetchall()
    for f in farmers:
        print(f)
        
    print("\n--- POSTGRES FARMS ---")
    farms = db.execute(text("SELECT id, farmer_id, name, area_hectares FROM farms")).fetchall()
    for f in farms:
        print(f)
        
    print("\n--- POSTGRES PLANTS ---")
    plants = db.execute(text("SELECT id, farmer_id, species, is_invasive FROM plant_detections")).fetchall()
    for p in plants:
        print(p)
        
    db.close()

if __name__ == "__main__":
    check_pg()
