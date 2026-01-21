import re
from typing import Tuple


class Validators:
    """Input validation utilities"""
    
    @staticmethod
    def validate_phone(phone: str) -> Tuple[bool, str]:
        """Validate Indian phone number"""
        
        # Remove spaces and special characters
        phone_clean = re.sub(r'[^\d+]', '', phone)
        
        # Check for Indian phone format
        # Supports: +91XXXXXXXXXX, 91XXXXXXXXXX, XXXXXXXXXX
        pattern = r'^(\+91|91)?[6-9]\d{9}$'
        
        if re.match(pattern, phone_clean):
            return True, phone_clean
        else:
            return False, "Invalid phone number. Use 10-digit Indian mobile number"
    
    @staticmethod
    def validate_coordinates(lat: float, lon: float) -> Tuple[bool, str]:
        """Validate GPS coordinates for India"""
        
        # India's approximate bounding box
        # Latitude: 8°N to 37°N
        # Longitude: 68°E to 97°E
        
        if not (8.0 <= lat <= 37.0):
            return False, "Latitude out of range for India (8°N to 37°N)"
        
        if not (68.0 <= lon <= 97.0):
            return False, "Longitude out of range for India (68°E to 97°E)"
        
        return True, "Valid coordinates"
    
    @staticmethod
    def validate_email(email: str) -> Tuple[bool, str]:
        """Validate email address"""
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if re.match(pattern, email):
            return True, email.lower()
        else:
            return False, "Invalid email address"
