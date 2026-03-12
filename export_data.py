import sqlite3
import json
import os
from neo4j import GraphDatabase

# Configuration (from your .env)
SQLITE_DB = "agritech.db"
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password123"
UPLOADS_DIR = "uploads"
EXPORT_FILE = "neo4j_export.cypher"

class Neo4jEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, "to_native"):
            return str(obj.to_native())
        return str(obj)

def export_neo4j():
    print("🚀 Exporting Neo4j data to Cypher...")
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        with driver.session() as session:
            result = session.run("MATCH (n) RETURN n")
            with open(EXPORT_FILE, "w", encoding="utf-8") as f:
                for record in result:
                    node = record["n"]
                    labels = ":".join(node.labels)
                    props = json.dumps(dict(node), cls=Neo4jEncoder)
                    f.write(f"MERGE (n:{labels} {{id: '{node.get('id')}'}}) SET n = {props};\n")
            
            # Export relationships
            result = session.run("MATCH (a)-[r]->(b) RETURN a.id as aid, b.id as bid, type(r) as relType, r")
            with open(EXPORT_FILE, "a", encoding="utf-8") as f:
                for record in result:
                    f.write(f"MATCH (a {{id: '{record['aid']}'}}), (b {{id: '{record['bid']}'}}) "
                            f"MERGE (a)-[:{record['relType']}]->(b);\n")
        driver.close()
        print(f"✅ Neo4j data exported to {EXPORT_FILE}")
    except Exception as e:
        print(f"❌ Neo4j Export Error: {e}")
        print("💡 Tip: Make sure Neo4j is running.")

if __name__ == "__main__":
    print("📦 AgriAssist Data Packer")
    print("-" * 30)
    
    # Check SQLite
    if os.path.exists(SQLITE_DB):
        print(f"✅ Found SQLite DB: {SQLITE_DB}")
    else:
        print(f"❌ SQLite DB {SQLITE_DB} not found!")

    # Check Uploads
    if os.path.exists(UPLOADS_DIR):
        print(f"✅ Found Uploads folder: {UPLOADS_DIR}")
    else:
        print(f"❌ Uploads folder not found!")

    # Export Neo4j
    export_neo4j()

    print("-" * 30)
    print("📂 SUCCESS! Now send these 3 items to your friend:")
    print(f"1. {SQLITE_DB}")
    print(f"2. {EXPORT_FILE}")
    print(f"3. {UPLOADS_DIR} (the whole folder)")
    print("\n📝 Your friend should:")
    print(f"1. Place {SQLITE_DB} and {UPLOADS_DIR} in their project folder.")
    print(f"2. Open Neo4j Browser and run the contents of {EXPORT_FILE} to restore graph data.")
