"""
Agent 1: Portfolio Analysis Agent
Analyzes all farmer data from SQLite using statistical summaries and
Gemini AI to produce business intelligence insights.
"""
import json
from sqlalchemy.orm import Session
from app.models.user import Farmer
from app.models.farm import Farm
from app.models.crop import Crop
from app.models.gamification import GamificationEvent
import google.generativeai as genai
from app.core.config import settings

genai.configure(api_key=settings.GEMINI_API_KEY)
_model = genai.GenerativeModel("gemini-2.5-flash")


def _gather_portfolio_data(db: Session) -> dict:
    """Collect aggregated portfolio data from SQLite."""
    farmers = db.query(Farmer).all()
    farms = db.query(Farm).all()
    crops = db.query(Crop).all()

    total_area_ha = sum(float(f.area_hectares or 0) for f in farms)
    total_carbon = sum(float(f.carbon_credits_annual or 0) for f in farms)
    verified_farms = sum(1 for f in farms if f.verification_status == "approved")
    pending_farms = sum(1 for f in farms if f.verification_status == "pending")
    rejected_farms = sum(1 for f in farms if f.verification_status == "rejected")
    no_doc_farms = sum(1 for f in farms if not f.document_url)

    soil_dist: dict = {}
    for f in farms:
        if f.soil_type:
            soil_dist[f.soil_type] = soil_dist.get(f.soil_type, 0) + 1

    crop_dist: dict = {}
    for c in crops:
        crop_dist[c.name] = crop_dist.get(c.name, 0) + 1

    state_dist: dict = {}
    district_dist: dict = {}
    for farmer in farmers:
        if farmer.state:
            state_dist[farmer.state] = state_dist.get(farmer.state, 0) + 1
        if farmer.district:
            district_dist[farmer.district] = district_dist.get(farmer.district, 0) + 1

    top_farmers = sorted(farmers, key=lambda x: x.total_points, reverse=True)[:5]
    top_farmer_data = [{"name": f.name, "points": f.total_points, "district": f.district} for f in top_farmers]

    return {
        "total_farmers": len(farmers),
        "total_farms": len(farms),
        "total_area_hectares": round(total_area_ha, 2),
        "total_carbon_credits": round(total_carbon, 2),
        "verification": {
            "approved": verified_farms,
            "pending": pending_farms,
            "rejected": rejected_farms,
            "no_document": no_doc_farms
        },
        "soil_distribution": soil_dist,
        "crop_distribution": crop_dist,
        "state_distribution": state_dist,
        "district_distribution": district_dist,
        "top_farmers_by_points": top_farmer_data,
        "total_crops_recorded": len(crops),
    }


def run_portfolio_analysis_agent(db: Session) -> dict:
    """
    Portfolio Analysis Agent:
    Returns structured business intelligence report with AI narrative.
    """
    data = _gather_portfolio_data(db)

    prompt = f"""
You are a senior Agricultural Business Intelligence analyst for the 'AgriAssist' platform in India.

Here is the current platform portfolio data:

FARMER & FARM STATISTICS:
- Total Registered Farmers: {data['total_farmers']}
- Total Farms Mapped: {data['total_farms']}
- Total Land Under Management: {data['total_area_hectares']} Hectares
- Total Carbon Credits Generated: {data['total_carbon_credits']} credits

DOCUMENT VERIFICATION BREAKDOWN:
- Approved: {data['verification']['approved']}
- Pending: {data['verification']['pending']}
- Rejected: {data['verification']['rejected']}
- No Document Yet: {data['verification']['no_document']}

SOIL TYPE DISTRIBUTION: {json.dumps(data['soil_distribution'])}
CROP TYPE DISTRIBUTION: {json.dumps(data['crop_distribution'])}
STATE DISTRIBUTION: {json.dumps(data['state_distribution'])}
TOP 5 FARMERS BY ENGAGEMENT: {json.dumps(data['top_farmers_by_points'])}

Based on this real platform data, produce a structured Business Intelligence Report. Use Indian agricultural context.

Return ONLY a valid JSON object with this exact structure:
{{
  "executive_summary": "2-3 sentence overview of the platform health",
  "key_metrics": [
    {{"label": "Platform Coverage", "value": "...", "trend": "positive/negative/neutral", "insight": "..."}}
  ],
  "top_insights": [
    "Insight 1 about soil/crop distribution patterns",
    "Insight 2 about verification compliance",
    "Insight 3 about geographic concentration",
    "Insight 4 about carbon credit potential"
  ],
  "risks": [
    "Risk 1",
    "Risk 2"
  ],
  "recommendations": [
    "Action 1 for admin to take",
    "Action 2",
    "Action 3"
  ],
  "portfolio_health_score": 78
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
        ai_analysis = json.loads(text.strip())
    except Exception as e:
        ai_analysis = {
            "executive_summary": "AI analysis unavailable. Raw data shown below.",
            "key_metrics": [],
            "top_insights": [f"Error: {str(e)}"],
            "risks": [],
            "recommendations": [],
            "portfolio_health_score": 0
        }

    return {
        "raw_data": data,
        "analysis": ai_analysis
    }
