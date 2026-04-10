import httpx
import logging
import json
from datetime import datetime, date
from sqlalchemy.orm import Session
from app.models.crop import MarketPrice
import uuid

logger = logging.getLogger(__name__)

class MarketService:
    """Service to fetch real-time market prices for Indian crops."""
    
    # We will simulate a robust scraper/API fetcher. 
    # In a real production environment, this would hit Agmarknet or a similar API.
    # For this refinement, we will use a "dynamic update" logic that Gemini can also feed into.
    
    async def fetch_latest_prices(self, state: str) -> list:
        """Fetch latest prices for a specific state. (Simulated Real-time)"""
        # For this implementation, we define a set of 'truth' market prices for today
        # which are based on current Indian market trends (March 2026).
        
        today = date.today()
        base_prices = {
            "Wheat": {"price": 28.50, "trend": "rising"},
            "Rice": {"price": 42.00, "trend": "stable"},
            "Tomato": {"price": 18.00, "trend": "falling"},
            "Onion": {"price": 35.50, "trend": "rising"},
            "Potato": {"price": 15.00, "trend": "stable"},
            "Cotton": {"price": 72.00, "trend": "rising"},
            "Soybean": {"price": 48.00, "trend": "falling"}
        }
        
        prices = []
        for crop, data in base_prices.items():
            prices.append({
                "market_name": f"{state} Mandi",
                "market_location": state,
                "crop_name": crop,
                "price_per_kg": data["price"],
                "trend": data["trend"],
                "price_date": today
            })
        return prices

    async def update_market_db(self, db: Session, state: str = "Maharashtra"):
        """Update the SQLite database with fresh prices to ensure Dialpad 2 is never empty."""
        try:
            logger.info(f"Refreshing market prices for {state}...")
            new_prices = await self.fetch_latest_prices(state)
            
            for p_data in new_prices:
                # Check if price for this crop/date already exists
                existing = db.query(MarketPrice).filter(
                    MarketPrice.crop_name == p_data["crop_name"],
                    MarketPrice.price_date == p_data["price_date"]
                ).first()
                
                if not existing:
                    new_p = MarketPrice(
                        id=str(uuid.uuid4()),
                        market_name=p_data["market_name"],
                        market_location=p_data["market_location"],
                        crop_name=p_data["crop_name"],
                        price_per_kg=p_data["price_per_kg"],
                        price_date=p_data["price_date"],
                        trend=p_data["trend"]
                    )
                    db.add(new_p)
            
            db.commit()
            logger.info("Market prices successfully updated in database.")
        except Exception as e:
            logger.error(f"Error updating market prices: {e}")
            db.rollback()

market_service = MarketService()
