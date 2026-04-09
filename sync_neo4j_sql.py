import os
from dotenv import load_dotenv
import psycopg2

load_dotenv(override=True)

from neo4j import GraphDatabase

uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
user = os.getenv('NEO4J_USER', 'neo4j')
password = os.getenv('NEO4J_PASSWORD', 'password123')
db_url = os.getenv('DATABASE_URL')

def clean_neo4j():
    if not db_url or not db_url.startswith("postgres"):
        print("DATABASE_URL is not pointing to Postgres. Cannot sync with Supabase.")
        return

    print("Connecting to Supabase...")
    # Convert sqlalchemy syntax exactly as needed, or just let psycopg2 parse it
    # psycopg2 needs it like: postgresql://user:pass@host:port/dbname
    conn_str = db_url.replace("postgresql+psycopg2", "postgresql")
    
    conn = psycopg2.connect(conn_str)
    cur = conn.cursor()
    
    cur.execute("SELECT id FROM farmers")
    sql_farmer_ids = [row[0] for row in cur.fetchall()]
    
    cur.execute("SELECT id FROM farms")
    sql_farm_ids = [row[0] for row in cur.fetchall()]
    
    conn.close()
    
    print(f"SQL valid farmers: {len(sql_farmer_ids)}, valid farms: {len(sql_farm_ids)}")
    
    print("Connecting to Neo4j...")
    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver.session() as session:
        # Fetch Neo4j farmers
        res = session.run("MATCH (f:Farmer) RETURN f.id AS id")
        neo4j_farmer_ids = [r['id'] for r in res]
        
        deleted_farmers = 0
        for nid in neo4j_farmer_ids:
            if nid not in sql_farmer_ids:
                print(f"Deleting orphaned farmer Node: {nid}")
                session.run("MATCH (f:Farmer {id: $id}) DETACH DELETE f", id=nid)
                deleted_farmers += 1
                
        # Fetch Neo4j farms
        res = session.run("MATCH (f:Farm) RETURN f.id AS id")
        neo4j_farm_ids = [r['id'] for r in res]
        
        deleted_farms = 0
        for nid in neo4j_farm_ids:
            if str(nid) not in sql_farm_ids: # farm id might be uuid string
                print(f"Deleting orphaned farm Node: {nid}")
                session.run("MATCH (f:Farm {id: $id}) DETACH DELETE f", id=str(nid))
                deleted_farms += 1
                
        print(f"Done! Deleted {deleted_farmers} ghost farmers and {deleted_farms} ghost farms.")

if __name__ == "__main__":
    clean_neo4j()
