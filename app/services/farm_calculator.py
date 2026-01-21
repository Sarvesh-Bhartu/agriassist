from shapely.geometry import Polygon
from shapely.ops import transform
import pyproj
from typing import List, Dict


class FarmCalculator:
    """Calculate farm area from GPS coordinates"""
    
    def __init__(self):
        self.wgs84 = pyproj.CRS('EPSG:4326')
        self.utm = pyproj.CRS('EPSG:32643')  # UTM Zone 43N for India
    
    def calculate_area(self, coordinates: List[Dict]) -> Dict:
        """
        Calculate farm area from GPS coordinates
        
        Args:
            coordinates: List of dicts with 'lat' and 'lon' keys
            
        Returns:
            Dictionary with area calculations and centroid
        """
        
        if not coordinates or len(coordinates) < 3:
            raise ValueError("At least 3 coordinates required to form a polygon")
        
        try:
            # Convert to (lon, lat) tuples for Shapely
            points = [(c['lon'], c['lat']) for c in coordinates]
            
            # Create polygon in WGS84 (lat/lon)
            polygon_wgs84 = Polygon(points)
            
            # Transform to projected coordinates (UTM) for accurate area calculation
            project = pyproj.Transformer.from_crs(
                self.wgs84, self.utm, always_xy=True
            ).transform
            polygon_utm = transform(project, polygon_wgs84)
            
            # Calculate area
            area_sq_meters = polygon_utm.area
            area_hectares = area_sq_meters / 10000
            area_acres = area_hectares * 2.471
            
            # Get centroid
            centroid = polygon_wgs84.centroid
            
            return {
                'area_hectares': round(area_hectares, 2),
                'area_acres': round(area_acres, 2),
                'area_sq_meters': round(area_sq_meters, 2),
                'perimeter_meters': round(polygon_utm.length, 2),
                'centroid': {
                    'lat': round(centroid.y, 6),
                    'lon': round(centroid.x, 6)
                }
            }
        except Exception as e:
            raise ValueError(f"Area calculation failed: {str(e)}")


# Create singleton instance
farm_calculator = FarmCalculator()
