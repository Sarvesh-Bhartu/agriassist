from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import json
from typing import List, Dict
from app.services.gemini_service import gemini_service
from app.models.farm import Farm
from app.models.crop import Crop, MarketPrice


class RecommendationService:
    """Crop recommendation using Gemini AI and historical data"""
    
    def __init__(self):
        self.model = gemini_service.get_pro_model()
    
    async def get_recommendations(
        self,
        db: Session,
        farmer_id: str,
        season: str,
        budget: float
    ) -> List[Dict]:
        """Generate AI-powered crop recommendations"""
        
        # Get farmer's farm profile
        farm = db.query(Farm).filter(Farm.farmer_id == farmer_id).first()
        
        if not farm:
            # Generate recommendations without farm profile
            return await self._get_generic_recommendations(season, budget)
        
        # Find similar successful farmers (same soil, similar size)
        similar_crops = db.query(
            Crop.name,
            Crop.variety,
            func.avg(Crop.total_profit_inr).label('avg_profit'),
            func.count(Crop.id).label('farmer_count')
        ).join(Farm).filter(
            and_(
                Farm.soil_type == farm.soil_type,
                Farm.area_hectares.between(
                    float(farm.area_hectares) * 0.7 if farm.area_hectares else 0,
                    float(farm.area_hectares) * 1.3 if farm.area_hectares else 999
                ),
                Crop.season == season,
                Crop.total_profit_inr.isnot(None)
            )
        ).group_by(Crop.name, Crop.variety).order_by(
            func.avg(Crop.total_profit_inr).desc()
        ).limit(10).all()
        
        # Get current market prices (last 7 days)
        market_prices = db.query(MarketPrice).filter(
            MarketPrice.price_date >= func.date(func.current_date(), '-7 days')
        ).order_by(MarketPrice.price_date.desc()).limit(20).all()
        
        # Build context for Gemini
        context = f"""
        You are an agricultural expert providing crop recommendations for an Indian farmer.
        
        Farmer Profile:
        - Farm Size: {farm.area_hectares} hectares ({farm.area_acres} acres)
        - Soil Type: {farm.soil_type}
        - Location: {farm.farmer.district}, {farm.farmer.state if farm.farmer else ''}
        - Budget: ₹{budget:,.2f}
        - Season: {season}
        - Water Source: {farm.water_source or 'Not specified'}
        - Irrigation: {farm.irrigation_type or 'Not specified'}
        
        Historical Success Data (from farmers with similar conditions):
        {json.dumps([{
            'crop': c.name,
            'variety': c.variety,
            'avg_profit': float(c.avg_profit) if c.avg_profit else 0,
            'farmers_count': c.farmer_count
        } for c in similar_crops], indent=2) if similar_crops else 'No historical data available'}
        
        Recent Market Prices:
        {json.dumps([{
            'crop': p.crop_name,
            'price_per_kg': float(p.price_per_kg),
            'trend': p.trend,
            'date': str(p.price_date)
        } for p in market_prices[:10]], indent=2) if market_prices else 'No market data available'}
        
        Task:
        Provide the TOP 3 crop recommendations that:
        1. Fit within the budget
        2. Are suitable for {farm.soil_type} soil
        3. Are appropriate for {season} season
        4. Have good market potential
        5. Match the farmer's resources (water, irrigation)
        
        Respond in JSON format as an array of objects:
        [
            {{
                "crop": "crop name",
                "variety": "recommended variety",
                "expected_profit_min": 50000,
                "expected_profit_max": 80000,
                "investment_breakdown": {{
                    "seeds": 10000,
                    "fertilizer": 15000,
                    "irrigation": 8000,
                    "labor": 12000,
                    "total": 45000
                }},
                "risk_factors": ["drought risk", "pest vulnerability"],
                "timeline": "4-5 months from planting to harvest",
                "advice": "Detailed growing advice and tips"
            }}
        ]
        
        Provide realistic numbers based on Indian agricultural conditions and current market rates.
        """
        
        try:
            # Generate response
            response = self.model.generate_content(context)
            result_text = response.text.strip()
            
            # Handle markdown code blocks
            if result_text.startswith("```json"):
                result_text = result_text.replace("```json", "").replace("```", "").strip()
            elif result_text.startswith("```"):
                result_text = result_text.replace("```", "").strip()
            
            recommendations = json.loads(result_text)
            
            return recommendations if isinstance(recommendations, list) else [recommendations]
            
        except Exception as e:
            # Return fallback recommendations
            return await self._get_generic_recommendations(season, budget)
    
    async def _get_generic_recommendations(self, season: str, budget: float) -> List[Dict]:
        """Fallback generic recommendations"""
        return [
            {
                "crop": "Mixed Vegetables",
                "variety": "Tomato, Onion, Potato",
                "expected_profit_min": budget * 0.3,
                "expected_profit_max": budget * 0.8,
                "investment_breakdown": {
                    "seeds": budget * 0.15,
                    "fertilizer": budget * 0.25,
                    "irrigation": budget * 0.20,
                    "labor": budget * 0.30,
                    "total": budget * 0.9
                },
                "risk_factors": ["Market price volatility", "Weather dependency"],
                "timeline": "3-4 months",
                "advice": "Start with a small test area. Mixed cropping reduces risk."
            }
        ]


# Create singleton instance
recommendation_service = RecommendationService()
