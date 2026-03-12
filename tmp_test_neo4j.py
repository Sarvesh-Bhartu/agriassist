from neo4j import GraphDatabase
import os

def test_conn(uri, user, pwd):
    try:
        driver = GraphDatabase.driver(uri, auth=(user, pwd))
        with driver.session() as session:
            session.run("RETURN 1")
        print(f"✅ Success with {uri} / {pwd}")
        return True
    except Exception as e:
        print(f"❌ Failed with {pwd}: {e}")
        return False

# Test common local passwords
if __name__ == "__main__":
    pwds = ["password", "password123", "neo4j", "neo4j123", "admin", "admin123"]
    for p in pwds:
        if test_conn("bolt://localhost:7687", "neo4j", p):
            break
