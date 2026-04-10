from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv(override=True)

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
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "password123")
        
        if not self._driver:
            # Mask URI for safety but show the protocol and host
            masked_uri = uri.split('@')[-1] if '@' in uri else uri
            print(f"📡 Initializing Neo4j driver: {masked_uri}")
            try:
                self._driver = GraphDatabase.driver(uri, auth=(user, password))
                print("🏁 Neo4j driver created")
            except Exception as e:
                print(f"❌ Failed to create Neo4j driver at {uri}: {e}")
                raise e
        else:
            print(f"📡 Neo4j driver already exists (Connecting to: {uri.split('@')[-1] if '@' in uri else uri})")
    
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
        # If database is not provided, use the env var. If the env var is not set, 
        # let Neo4j choose the default by passing None.
        db_name = database or os.getenv("NEO4J_DATABASE")
        if not db_name or db_name.lower() == "neo4j":
            # Many Aura instances don't like 'neo4j' being explicitly named 
            # if it's the default, so we'll pass None to use the default server database.
            return self._driver.session()
        return self._driver.session(database=db_name)

# Global instance
neo4j_driver = Neo4jDriver()
