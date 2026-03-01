import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from app.core.neo4j_driver import neo4j_driver

def check():
    session = neo4j_driver.get_session()
    
    print("--- FARMS ---")
    res = session.run("MATCH (f:Farm) RETURN f.id AS id, f.name AS name, f.location AS loc")
    for r in res:
        print(dict(r))
        
    print("\n--- FARMERS ---")
    res = session.run("MATCH (f:Farmer) RETURN f.id AS id, f.name AS name, f.phone AS phone")
    for r in res:
        print(dict(r))
        
    print("\n--- PLANTS ---")
    res = session.run("MATCH (p:Plant) RETURN p.id AS id, p.species AS spp, p.location AS loc")
    for r in res:
        print(dict(r))

    print("\n--- DISTANCES ---")
    # All distance pairs
    res = session.run("MATCH (n:Farm), (m:Farm) WHERE id(n) > id(m) AND n.location IS NOT NULL AND m.location IS NOT NULL RETURN n.id, m.id, point.distance(n.location, m.location)")
    for r in res:
        print(dict(r))
        
    session.close()

if __name__ == "__main__":
    check()
