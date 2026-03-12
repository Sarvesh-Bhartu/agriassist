import logging
from app.core.neo4j_driver import neo4j_driver

logger = logging.getLogger(__name__)

class GraphService:
    """Service for interacting with the Neo4j Graph Database."""
    
    def __init__(self):
        self.driver = neo4j_driver
        
    def create_farmer_node(self, farmer_id: str, phone: str, name: str, district: str = None, state: str = None):
        """Create or update a Farmer node (a circle representing a user)."""
        # MERGE is like "CREATE IF NOT EXISTS". It finds the node by id, or makes a new one.
        query = """
        MERGE (f:Farmer {id: $farmer_id})
        SET f.phone = $phone,
            f.name = $name,
            f.district = $district,
            f.state = $state
        RETURN f
        """
        try:
            session = self.driver.get_session()
            result = session.run(query, farmer_id=farmer_id, phone=phone, name=name, district=district, state=state)
            record = result.single()
            session.close()
            if record:
                logger.info(f"✅ Created/Updated Graph Node for Farmer: {name}")
                return record["f"]
        except Exception as e:
            logger.error(f"❌ Failed to create farmer node: {e}")
        return None

    def create_farm_node(self, farm_id: str, name: str, area_hectares: float = None, soil_type: str = None, gps_lat: float = None, gps_lon: float = None):
        """Create or update a Farm node (a circle representing a farm)."""
        query = """
        MERGE (f:Farm {id: $farm_id})
        SET f.name = $name,
            f.area_hectares = $area_hectares,
            f.soil_type = $soil_type
        RETURN f
        """
        try:
            session = self.driver.get_session()
            result = session.run(query, farm_id=farm_id, name=name, area_hectares=area_hectares, soil_type=soil_type)
            record = result.single()
            
            if gps_lat is not None and gps_lon is not None:
                session.run("MATCH (f:Farm {id: $id}) SET f.location = point({latitude: $lat, longitude: $lon})", 
                            id=farm_id, lat=float(gps_lat), lon=float(gps_lon))
                            
            session.close()
            if record:
                logger.info(f"✅ Created/Updated Graph Node for Farm: {farm_id}")
                return record["f"]
        except Exception as e:
            logger.error(f"❌ Failed to create farm node: {e}")
        return None

    def link_farmer_to_farm(self, farmer_id: str, farm_id: str):
        """Create an OWNS relationship (an arrow) connecting a Farmer to a Farm."""
        query = """
        MATCH (u:Farmer {id: $farmer_id})
        MATCH (f:Farm {id: $farm_id})
        MERGE (u)-[r:OWNS]->(f)
        RETURN r
        """
        try:
            session = self.driver.get_session()
            result = session.run(query, farmer_id=farmer_id, farm_id=farm_id)
            record = result.single()
            session.close()
            if record:
                logger.info(f"✅ Created Graph Relationship: Farmer({farmer_id}) -[OWNS]-> Farm({farm_id})")
                return record["r"]
        except Exception as e:
            logger.error(f"❌ Failed to link farmer to farm: {e}")
        return None

    def create_detection_record(self, farmer_id: str, detection_id: str, species: str, gps_lat: float, gps_lon: float, confidence: float):
        """Create a Plant node and record the SCANNED relationship in Neo4j."""
        query = """
        MERGE (f:Farmer {id: $farmer_id})
        CREATE (p:Plant {id: $detection_id, species: $species, confidence: $confidence})
        MERGE (f)-[:SCANNED]->(p)
        WITH p
        // Use standard Cypher syntax to conditionally set location
        FOREACH (ignoreMe IN CASE WHEN $gps_lat IS NOT NULL AND $gps_lon IS NOT NULL THEN [1] ELSE [] END |
            SET p.location = point({latitude: $gps_lat, longitude: $gps_lon})
        )
        RETURN p
        """
        # Fallback query if apoc is not installed or just manual if check:
        # Instead of MATCHing the farmer (which fails if the Farmer node doesn't exist yet/was wiped), 
        # MERGE the farmer first to guarantee they exist, then CREATE the plant and link them.
        query_safe = """
        MERGE (f:Farmer {id: $farmer_id})
        CREATE (p:Plant {id: $detection_id, species: $species, confidence: $confidence})
        MERGE (f)-[:SCANNED]->(p)
        """
        try:
            session = self.driver.get_session()
            session.run(query_safe, farmer_id=farmer_id, detection_id=detection_id, species=species, confidence=confidence)
            
            if gps_lat and gps_lon:
                session.run("MATCH (p:Plant {id: $id}) SET p.location = point({latitude: $lat, longitude: $lon})", 
                            id=detection_id, lat=float(gps_lat), lon=float(gps_lon))
                            
            session.close()
            logger.info(f"✅ Created Graph Node for Plant Detection: {species}")
            return detection_id
        except Exception as e:
            logger.error(f"❌ Failed to create plant node: {e}")
        return None

    def find_nearby_farmers(self, plant_id: str, farmer_id: str, max_distance_meters: int = 5000):
        """Find other farmers within 5km of the detected plant."""
        query = """
        MATCH (plant:Plant {id: $plant_id})
        // Find farmers and their farms
        MATCH (neighbor:Farmer)-[:OWNS]->(farm:Farm)
        WHERE neighbor.id <> $farmer_id
          AND plant.location IS NOT NULL
          AND farm.location IS NOT NULL
          AND point.distance(plant.location, farm.location) < $max_distance
        RETURN neighbor.phone AS phone, 
               toInteger(point.distance(plant.location, farm.location)/1000) AS distance_km
        """
        try:
             session = self.driver.get_session()
             result = session.run(query, plant_id=plant_id, farmer_id=farmer_id, max_distance=max_distance_meters)
             neighbors = [{"phone": record["phone"], "distance_km": record["distance_km"]} for record in result]
             session.close()
             return neighbors
        except Exception as e:
             logger.error(f"❌ Failed to find nearby farmers: {e}")
             return []

    def get_farm_context_for_ai(self, farm_id: str, max_distance_meters: int = 10000):
        """Get contextual data about neighboring farms for AI recommendations."""
        query = """
        MATCH (target:Farm {id: $farm_id})
        MATCH (neighbor:Farm)
        WHERE target.id <> neighbor.id
          AND target.location IS NOT NULL
          AND neighbor.location IS NOT NULL
          AND point.distance(target.location, neighbor.location) < $max_distance
        RETURN neighbor.soil_type AS soil_type, 
               neighbor.area_hectares AS area_hectares,
               toInteger(point.distance(target.location, neighbor.location)/1000) AS distance_km
        """
        try:
            session = self.driver.get_session()
            result = session.run(query, farm_id=farm_id, max_distance=max_distance_meters)
            
            soil_counts = {}
            total_area = 0
            neighbor_count = 0
            
            for record in result:
                neighbor_count += 1
                soil = record["soil_type"] or "Unknown"
                soil_counts[soil] = soil_counts.get(soil, 0) + 1
                
                area = record["area_hectares"]
                if area:
                    total_area += float(area)
                    
            session.close()
            
            return {
                "neighbor_count": neighbor_count,
                "soil_distribution": soil_counts,
                "average_neighbor_farm_size_hectares": round(total_area / neighbor_count, 2) if neighbor_count > 0 else 0
            }
        except Exception as e:
             logger.error(f"❌ Failed to get farm context: {e}")
             return {
                 "neighbor_count": 0,
                 "soil_distribution": {},
                 "average_neighbor_farm_size_hectares": 0
             }

    def get_local_trends(self, farmer_id: str, radius_km: int = 10):
        """Find what crops neighboring farmers are planting."""
        query = """
        MATCH (f:Farmer {id: $farmer_id})-[:OWNS]->(target:Farm)
        MATCH (neighbor:Farmer)-[:OWNS]->(nFarm:Farm)
        MATCH (neighbor)-[:SCANNED|:PLANTED]->(p:Plant)
        WHERE f.id <> neighbor.id
          AND target.location IS NOT NULL
          AND nFarm.location IS NOT NULL
          AND point.distance(target.location, nFarm.location) < $radius * 1000
        RETURN p.species AS crop, count(*) AS count
        ORDER BY count DESC LIMIT 3
        """
        try:
            session = self.driver.get_session()
            result = session.run(query, farmer_id=farmer_id, radius=radius_km)
            crops = [record["crop"] for record in result]
            session.close()
            return {"popular_crops": crops}
        except Exception as e:
            logger.error(f"❌ Failed to get local trends: {e}")
            return {"popular_crops": []}

# Global instance
graph_service = GraphService()
