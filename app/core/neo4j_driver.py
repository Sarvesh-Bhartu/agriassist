from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()

class Neo4jDriver:
    """Manages the Neo4j database connection pool."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Neo4jDriver, cls).__new__(cls)
            cls._instance._driver = None
        return cls._instance
    
    def connect(self):
        """Build the driver if it doesn't exist."""
        if not self._driver:
            uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
            user = os.getenv("NEO4J_USER", "neo4j")
            password = os.getenv("NEO4J_PASSWORD", "password123")
            
            try:
                self._driver = GraphDatabase.driver(uri, auth=(user, password))
                # We will verify connectivity lazily or via a health check
                # instead of blocking the main thread here.
                print("🏁 Neo4j driver initialized")
            except Exception as e:
                print(f"❌ Failed to connect to Neo4j: {e}")
                raise e
    
    def close(self):
        """Close the driver."""
        if self._driver:
            self._driver.close()
            self._driver = None
            print("🚀 Neo4j connection closed")
            
    def get_session(self, database=None):
        """Get a new session."""
        if not self._driver:
            self.connect()
        return self._driver.session(database=database or os.getenv("NEO4J_DATABASE", "neo4j"))

# Global instance
neo4j_driver = Neo4jDriver()
