from typing import Dict


class CarbonService:
    """Calculate carbon credits for farms"""
    
    # Research-based coefficients (tonnes CO2 per hectare per year)
    SOIL_FACTORS = {
        'black': 2.8,
        'red': 2.3,
        'alluvial': 2.5,
        'laterite': 2.0,
        'sandy': 1.5
    }
    
    CROP_FACTORS = {
        'rice': 1.2,
        'wheat': 1.3,
        'sugarcane': 1.8,
        'cotton': 1.4,
        'vegetables': 1.5,
        'pulses': 1.6,
        'millets': 1.4,
        'mixed': 1.5
    }
    
    # Carbon credit price in INR (approximate market rate)
    CREDIT_PRICE_INR = 2200
    
    def calculate_credits(
        self,
        area_hectares: float,
        soil_type: str,
        crop_type: str = 'mixed'
    ) -> Dict:
        """
        Calculate annual carbon credits for a farm
        
        Args:
            area_hectares: Farm area in hectares
            soil_type: Type of soil
            crop_type: Type of crop being grown
            
        Returns:
            Dictionary with carbon credit calculations
        """
        
        if area_hectares <= 0:
            raise ValueError("Area must be greater than 0")
        
        # Get factors with defaults
        soil_factor = self.SOIL_FACTORS.get(soil_type.lower(), 2.0)
        crop_factor = self.CROP_FACTORS.get(crop_type.lower(), 1.5)
        
        # Formula: Credits = Area × Crop Factor × Soil Factor × Efficiency
        # Efficiency factor of 0.8 accounts for real-world variations
        annual_credits = area_hectares * crop_factor * soil_factor * 0.8
        annual_value = annual_credits * self.CREDIT_PRICE_INR
        
        return {
            'annual_credits': round(annual_credits, 2),
            'annual_value_inr': round(annual_value, 2),
            'credit_price_inr': self.CREDIT_PRICE_INR,
            'calculation_details': {
                'area_hectares': area_hectares,
                'crop_factor': crop_factor,
                'soil_factor': soil_factor,
                'efficiency': 0.8
            },
            'projected_5_year_value': round(annual_value * 5, 2),
            'projected_10_year_value': round(annual_value * 10, 2)
        }


# Create singleton instance
carbon_service = CarbonService()
