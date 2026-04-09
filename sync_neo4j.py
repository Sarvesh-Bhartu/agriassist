import os
import sys


from dotenv import load_dotenv
load_dotenv(override=True)

from app.core.database import SessionLocal
from app.models.user import Farmer
from app.models.farm import Farm
from app.core.neo4j_driver import neo4j_driver
from app.services.graph_service import graph_service

def sync_sql_to_neo4j():
    db = SessionLocal()
    session = neo4j_driver.get_session()
    
    print("Fetching SQL Farmers...")
    sql_farmers = db.query(Farmer).all()
    sql_farmer_ids = {str(f.id): f for f in sql_farmers}
    
    print("Fetching Neo4j Farmers...")
    res = session.run("MATCH (f:Farmer) RETURN f.id AS id")
    neo4j_farmer_ids = [r['id'] for r in res]
    
    # Delete orphan farmers in Neo4j
    deleted_farmers = 0
    for nid in neo4j_farmer_ids:
        if nid not in sql_farmer_ids:
            # Delete this farmer and their farms
            print(f"Deleting orphaned farmer Node: {nid}")
            session.run("MATCH (f:Farmer {id: $id}) DETACH DELETE f", id=nid)
            deleted_farmers += 1
            
    # Do the same for Farms
    print("Fetching SQL Farms...")
    sql_farms = db.query(Farm).all()
    sql_farm_ids = {str(f.id): f for f in sql_farms}
    
    print("Fetching Neo4j Farms...")
    res_farm = session.run("MATCH (f:Farm) RETURN f.id AS id")
    neo4j_farm_ids = [r['id'] for r in res_farm]
    
    deleted_farms = 0
    for nid in neo4j_farm_ids:
        if nid not in sql_farm_ids:
            print(f"Deleting orphaned farm Node: {nid}")
            session.run("MATCH (f:Farm {id: $id}) DETACH DELETE f", id=nid)
            deleted_farms += 1
            
    print(f"Finished sync. Deleted {deleted_farmers} orphaned farmers and {deleted_farms} orphaned farms.")
            
    # Now lets also ensure all SQL nodes ARE in Neo4j 
    for fid, f in sql_farmer_ids.items():
        graph_service.create_farmer_node(
            farmer_id=fid,
            phone=f.phone,
            name=f.name,
            district=f.district,
            state=f.state
        )
        
    for fid, f in sql_farm_ids.items():
        area = float(f.area_hectares) if f.area_hectares else None
        gps_lat = None
        gps_lon = None
        if f.polygon_coordinates and len(f.polygon_coordinates) > 0:
            gps_lat = f.polygon_coordinates[0].get('lat')
            gps_lon = f.polygon_coordinates[0].get('lon')
            
        graph_service.create_farm_node(
            farm_id=fid,
            name=f.name or "Unnamed Farm",
            area_hectares=area,
            soil_type=f.soil_type,
            gps_lat=gps_lat,
            gps_lon=gps_lon
        )
        if f.farmer_id:
            graph_service.link_farmer_to_farm(
                farmer_id=str(f.farmer_id),
                farm_id=fid
            )
            
    print("SQL nodes synced to Neo4j successfully!")

    db.close()
    session.close()

if __name__ == "__main__":
    sync_sql_to_neo4j()
