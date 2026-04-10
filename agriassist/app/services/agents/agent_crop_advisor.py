"""
Agent 4: AI Crop Advisor Audit Agent
Reviews all crop recommendations (from gamification events and crop records)
to understand what advice has been given to farmers and evaluates its quality.
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


def _collect_advisory_data(db: Session) -> dict:
    """Collect all crop activity data to audit advisory patterns."""
    crops = db.query(Crop).all()
    farmers = {f.id: f for f in db.query(Farmer).all()}
    farms = {f.id: f for f in db.query(Farm).all()}

    # Build crop_advice_log — what farmers are growing
    crop_log = []
    for c in crops:
        farmer = farmers.get(c.farmer_id)
        farm = farms.get(c.farm_id) if c.farm_id else None
        crop_log.append({
            "crop_name": c.name,
            "variety": c.variety,
            "category": c.category,
            "season": c.season,
            "area_ha": float(c.area_planted_hectares or 0),
            "yield_kg": float(c.yield_kg or 0),
            "total_investment_inr": float(c.total_investment_inr or 0),
            "total_profit_inr": float(c.total_profit_inr or 0),
            "soil_type": farm.soil_type if farm else "unknown",
            "farmer_district": farmer.district if farmer else "unknown",
            "farmer_state": farmer.state if farmer else "unknown",
        })

    # Market prices for comparison
    market_prices = db.query(MarketPrice).order_by(MarketPrice.price_date.desc()).limit(50).all()
    market_data = [
        {"crop": mp.crop_name, "price_per_kg": float(mp.price_per_kg), "trend": mp.trend, "market": mp.market_name}
        for mp in market_prices
    ]

    # Gamification events related to farm mapping (which triggers crop advice)
    farm_events = db.query(GamificationEvent).filter(
        GamificationEvent.event_type == "farm_mapped"
    ).count()

    # Aggregate performance
    profitable_crops = [c for c in crop_log if c["total_profit_inr"] > 0]
    loss_crops = [c for c in crop_log if c["total_profit_inr"] < 0]
    avg_profit = sum(c["total_profit_inr"] for c in profitable_crops) / len(profitable_crops) if profitable_crops else 0

    crop_success_by_name: dict = {}
    for c in crop_log:
        name = c["crop_name"]
        if name not in crop_success_by_name:
            crop_success_by_name[name] = {"count": 0, "total_profit": 0, "yields": []}
        crop_success_by_name[name]["count"] += 1
        crop_success_by_name[name]["total_profit"] += c["total_profit_inr"]
        if c["yield_kg"] > 0:
            crop_success_by_name[name]["yields"].append(c["yield_kg"])

    return {
        "total_crop_records": len(crops),
        "total_advice_triggers": farm_events,
        "profitable_count": len(profitable_crops),
        "loss_count": len(loss_crops),
        "average_profit_inr": round(avg_profit, 2),
        "crop_log_sample": crop_log[:20],
        "crop_success_by_name": crop_success_by_name,
        "market_data": market_data[:15],
    }


def run_crop_advisor_audit_agent(db: Session) -> dict:
    """
    AI Crop Advisor Audit Agent:
    Evaluates crop outcomes vs market prices and assesses the
    quality/relevance of recommendations given to farmers.
    """
    data = _collect_advisory_data(db)

    prompt = f"""
You are an Agricultural Advisory Quality Auditor AI for the 'AgriAssist' platform in India.

Your role is to audit the quality of crop recommendations given to farmers based on actual outcomes.

ADVISORY PERFORMANCE DATA:
- Total crop records: {data['total_crop_records']}
- Total farm advice triggers: {data['total_advice_triggers']}
- Profitable outcomes: {data['profitable_count']}
- Loss outcomes: {data['loss_count']}
- Average profit (profitable crops only): INR {data['average_profit_inr']}

CROP LOG (sample of up to 20 entries):
{json.dumps(data['crop_log_sample'], indent=2)}

CROP SUCCESS BY NAME:
{json.dumps(data['crop_success_by_name'], indent=2)}

CURRENT MARKET PRICES:
{json.dumps(data['market_data'], indent=2)}

Please evaluate:
1. Which crops are performing best vs worst based on actual profit data?
2. Are there mismatches between suggested crops and market trends?
3. What soil+crop combinations are most profitable?
4. What advice improvements should be made?

Return ONLY valid JSON:
{{
  "advisory_quality_score": 75,
  "top_performing_crops": [
    {{"crop": "...", "avg_profit_inr": 0, "insight": "..."}}
  ],
  "underperforming_crops": [
    {{"crop": "...", "issue": "...", "recommendation": "..."}}
  ],
  "soil_crop_insights": [
    {{"soil_type": "...", "best_crop": "...", "reason": "..."}}
  ],
  "market_alignment_issues": [
    "Issue 1 where advisory may not match market reality"
  ],
  "advisory_improvements": [
    "Improvement 1",
    "Improvement 2",
    "Improvement 3"
  ],
  "summary": "2-3 sentence executive summary of advisory quality"
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
            "advisory_quality_score": 0,
            "top_performing_crops": [],
            "underperforming_crops": [],
            "soil_crop_insights": [],
            "market_alignment_issues": [],
            "advisory_improvements": [],
            "summary": f"AI unavailable: {str(e)}"
        }

    return {
        "raw_data": {
            "total_crop_records": data["total_crop_records"],
            "profitable_count": data["profitable_count"],
            "loss_count": data["loss_count"],
            "average_profit_inr": data["average_profit_inr"],
            "crop_success_by_name": data["crop_success_by_name"],
        },
        "audit_report": ai_result
    }
