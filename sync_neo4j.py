import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import logging

from app.core.neo4j_driver import neo4j_driver
from app.services.graph_service import graph_service

# Quick sync script
def sync_all():
    engine = create_engine(os.getenv("DATABASE_URL"))
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    # 1. Sync Farmers
    farmers = db.execute(text("SELECT id, name, phone, district, state FROM farmers")).fetchall()
    for f in farmers:
        print(f"Syncing Farmer: {f.name}")
        graph_service.create_farmer_node(
            farmer_id=f.id,
            phone=f.phone,
            name=f.name,
            district=f.district,
            state=f.state
        )
        
    # 2. Sync Farms
    farms = db.execute(text("SELECT id, farmer_id, name, area_hectares, soil_type, polygon_coordinates FROM farms")).fetchall()
    for f in farms:
        print(f"Syncing Farm: {f.name}")
        
        gps_lat = None
        gps_lon = None
        if f.polygon_coordinates and len(f.polygon_coordinates) > 0:
            gps_lat = f.polygon_coordinates[0].get('lat')
            gps_lon = f.polygon_coordinates[0].get('lon') or f.polygon_coordinates[0].get('lng')
            
        graph_service.create_farm_node(
            farm_id=f.id,
            name=f.name or "Unnamed Farm",
            area_hectares=float(f.area_hectares) if f.area_hectares else None,
            soil_type=f.soil_type,
            gps_lat=gps_lat,
            gps_lon=gps_lon
        )
        
        graph_service.link_farmer_to_farm(
            farmer_id=f.farmer_id,
            farm_id=f.id
        )
        
    # 3. Sync Plants
    plants = db.execute(text("SELECT id, farmer_id, species, confidence, latitude, longitude FROM plant_detections")).fetchall()
    for p in plants:
        print(f"Syncing Plant: {p.species}")
        graph_service.create_detection_record(
            farmer_id=p.farmer_id,
            detection_id=p.id,
            species=p.species,
            confidence=float(p.confidence) if p.confidence else 0.9,
            gps_lat=float(p.latitude) if p.latitude else None,
            gps_lon=float(p.longitude) if p.longitude else None
        )
        
    db.close()
    neo4j_driver.close()
    print("Sync complete!")

if __name__ == "__main__":
    sync_all()
