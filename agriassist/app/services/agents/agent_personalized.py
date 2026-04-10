"""
Agent 2: Personalized Cross-Sell/Upsell Agent
Predicts cross-sell and upsell opportunities for each farmer based
on their current crops, farm size, and engagement level.
"""
import json
from sqlalchemy.orm import Session
from app.models.user import Farmer
from app.models.farm import Farm
from app.models.crop import Crop, MarketPrice
from app.models.gamification import GamificationEvent
import google.generativeai as genai
from app.core.config import settings

genai.configure(api_key=settings.GEMINI_API_KEY)
_model = genai.GenerativeModel("gemini-2.5-flash")


def _score_farmer(farmer: Farmer, farms: list, crops: list, events: list) -> dict:
    """Calculate engagement & opportunity score for a single farmer."""
    total_area = sum(float(f.area_hectares or 0) for f in farms)
    carbon_credits = sum(float(f.carbon_credits_annual or 0) for f in farms)
    has_document = any(f.document_url for f in farms)
    verified = any(f.verification_status == "approved" for f in farms)
    crop_count = len(crops)
    crop_diversity = len(set(c.name for c in crops))
    event_count = len(events)

    # Simple rule-based scoring
    engagement_score = min(100, (farmer.total_points // 10) + (crop_count * 5) + (event_count * 2))
    opportunity = "high" if engagement_score > 60 else "medium" if engagement_score > 30 else "low"

    return {
        "farmer_id": farmer.id,
        "name": farmer.name,
        "district": farmer.district,
        "state": farmer.state,
        "total_points": farmer.total_points,
        "total_area_ha": round(total_area, 2),
        "carbon_credits": round(carbon_credits, 2),
        "has_verified_document": verified,
        "has_document": has_document,
        "crop_count": crop_count,
        "crop_diversity": crop_diversity,
        "engagement_score": engagement_score,
        "opportunity_tier": opportunity,
        "crops": list(set(c.name for c in crops))[:5],
    }


def run_personalized_agent(db: Session, top_n: int = 10) -> dict:
    """
    Personalized Cross-Sell/Upsell Agent.
    Returns targeted campaign suggestions for top opportunity farmers.
    """
    farmers = db.query(Farmer).all()
    scored = []

    for farmer in farmers:
        farms = db.query(Farm).filter(Farm.farmer_id == farmer.id).all()
        crops = db.query(Crop).filter(Crop.farmer_id == farmer.id).all()
        events = db.query(GamificationEvent).filter(GamificationEvent.farmer_id == farmer.id).all()
        profile = _score_farmer(farmer, farms, crops, events)
        scored.append(profile)

    scored.sort(key=lambda x: x["engagement_score"], reverse=True)
    top_farmers = scored[:top_n]

    # Get market context
    market_prices = db.query(MarketPrice).order_by(MarketPrice.price_date.desc()).limit(20).all()
    market_snapshot = [
        {"crop": mp.crop_name, "price_per_kg": float(mp.price_per_kg), "trend": mp.trend}
        for mp in market_prices
    ]

    prompt = f"""
You are a Precision Agriculture Marketing AI for the 'AgriAssist' platform in India.

Here are the top {len(top_farmers)} farmer profiles ranked by engagement score:
{json.dumps(top_farmers, indent=2)}

Current market price snapshot:
{json.dumps(market_snapshot, indent=2)}

For each farmer, recommend:
1. A cross-sell opportunity (e.g., new crop, service, or tool they are not using)
2. An upsell opportunity (e.g., expand existing activity or premium service)
3. A personalized campaign message (in simple language, 1-2 sentences)

Also suggest 3 platform-wide campaign ideas based on patterns across these farmers.

Return ONLY valid JSON:
{{
  "farmer_campaigns": [
    {{
      "farmer_name": "...",
      "engagement_score": 0,
      "opportunity_tier": "high/medium/low",
      "cross_sell": "...",
      "upsell": "...",
      "campaign_message": "...",
      "priority": "immediate/next_week/next_month"
    }}
  ],
  "platform_campaigns": [
    {{
      "campaign_name": "...",
      "target_segment": "...",
      "objective": "...",
      "suggested_channel": "SMS/App Notification/Voice Call"
    }}
  ],
  "summary": "2-sentence summary of cross-sell/upsell opportunity landscape"
}}
"""

    try:
        response = _model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        ai_result = json.loads(text.strip())
    except Exception as e:
        ai_result = {
            "farmer_campaigns": [],
            "platform_campaigns": [],
            "summary": f"AI unavailable: {str(e)}"
        }

    return {
        "scored_farmers": scored,
        "campaigns": ai_result
    }
