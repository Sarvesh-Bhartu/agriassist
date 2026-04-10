"""
Agent 3: Personalized Retention Agent
Identifies at-risk farmers (low engagement, unverified documents, no activity)
and generates breakthrough area-level retention strategies from the database.
"""
import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.user import Farmer
from app.models.farm import Farm
from app.models.gamification import GamificationEvent
import google.generativeai as genai
from app.core.config import settings

genai.configure(api_key=settings.GEMINI_API_KEY)
_model = genai.GenerativeModel("gemini-2.5-flash")

# A farmer is "at risk" if no activity in last 14 days or low points
AT_RISK_DAYS = 14
AT_RISK_POINTS_THRESHOLD = 50


def _classify_farmer(farmer: Farmer, farms: list, events: list, now: datetime) -> dict:
    last_active = farmer.last_active or farmer.created_at
    days_inactive = (now - last_active).days if last_active else 9999
    has_farm = len(farms) > 0
    has_verified = any(f.verification_status == "approved" for f in farms)
    has_doc = any(f.document_url for f in farms)
    recent_events = [e for e in events if e.created_at and (now - e.created_at).days <= 30]

    risk_score = 0
    risk_reasons = []

    if days_inactive > AT_RISK_DAYS:
        risk_score += 40
        risk_reasons.append(f"Inactive for {days_inactive} days")
    if farmer.total_points < AT_RISK_POINTS_THRESHOLD:
        risk_score += 25
        risk_reasons.append("Low engagement points")
    if not has_farm:
        risk_score += 20
        risk_reasons.append("No farm mapped yet")
    elif not has_verified:
        risk_score += 10
        risk_reasons.append("Farm document not verified")
    if len(recent_events) == 0:
        risk_score += 5
        risk_reasons.append("No activity in last 30 days")

    risk_level = "critical" if risk_score >= 60 else "high" if risk_score >= 35 else "medium" if risk_score >= 15 else "low"

    return {
        "farmer_id": farmer.id,
        "name": farmer.name,
        "district": farmer.district,
        "state": farmer.state,
        "days_inactive": days_inactive,
        "total_points": farmer.total_points,
        "has_farm": has_farm,
        "has_verified_document": has_verified,
        "has_document": has_doc,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "risk_reasons": risk_reasons,
        "recent_activity_count": len(recent_events),
    }


def _area_breakdown(at_risk: list) -> dict:
    """Group at-risk farmers by district/state for area-level insights."""
    by_district: dict = {}
    by_state: dict = {}
    for f in at_risk:
        d = f.get("district") or "Unknown"
        s = f.get("state") or "Unknown"
        by_district.setdefault(d, []).append(f["name"])
        by_state.setdefault(s, {"count": 0, "farmers": []})
        by_state[s]["count"] += 1
        by_state[s]["farmers"].append(f["name"])
    return {"by_district": by_district, "by_state": by_state}


def run_retention_agent(db: Session) -> dict:
    """
    Retention Agent:
    Identifies at-risk farmers, groups by area,
    and suggests breakthrough retention strategies per region.
    """
    farmers = db.query(Farmer).all()
    now = datetime.utcnow()
    classified = []

    for farmer in farmers:
        farms = db.query(Farm).filter(Farm.farmer_id == farmer.id).all()
        events = db.query(GamificationEvent).filter(GamificationEvent.farmer_id == farmer.id).all()
        profile = _classify_farmer(farmer, farms, events, now)
        classified.append(profile)

    at_risk = [f for f in classified if f["risk_level"] in ("critical", "high")]
    medium_risk = [f for f in classified if f["risk_level"] == "medium"]
    low_risk = [f for f in classified if f["risk_level"] == "low"]
    area_data = _area_breakdown(at_risk)

    prompt = f"""
You are a Farmer Retention Specialist AI for the 'AgriAssist' agricultural platform in India.

RETENTION RISK OVERVIEW:
- Total Farmers: {len(classified)}
- Critical/High Risk (need immediate action): {len(at_risk)}
- Medium Risk: {len(medium_risk)}
- Low Risk (healthy): {len(low_risk)}

AT-RISK FARMERS (Critical & High):
{json.dumps(at_risk[:15], indent=2)}

AREA BREAKDOWN OF AT-RISK FARMERS:
{json.dumps(area_data, indent=2)}

Analyze this data and:
1. Identify patterns in why farmers are churning or becoming inactive
2. Identify breakthrough areas (districts/states) with the highest concentration of at-risk farmers
3. Suggest targeted retention strategies for each breakthrough area
4. Suggest immediate actions for critical-risk individual farmers

Return ONLY valid JSON:
{{
  "churn_patterns": [
    "Pattern 1 observed",
    "Pattern 2 observed"
  ],
  "breakthrough_areas": [
    {{
      "area": "District/State name",
      "at_risk_count": 3,
      "dominant_risk_reason": "...",
      "retention_strategy": "Specific action to take in this area",
      "urgency": "immediate/this_week/this_month"
    }}
  ],
  "individual_actions": [
    {{
      "farmer_name": "...",
      "risk_level": "critical",
      "suggested_action": "Send SMS reminder about...",
      "message_template": "Short personalized message text"
    }}
  ],
  "platform_retention_initiatives": [
    {{
      "initiative": "...",
      "target_segment": "...",
      "expected_impact": "..."
    }}
  ],
  "overall_retention_health": "good/fair/poor",
  "summary": "2-3 sentence summary of platform retention health"
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
            "churn_patterns": [],
            "breakthrough_areas": [],
            "individual_actions": [],
            "platform_retention_initiatives": [],
            "overall_retention_health": "unknown",
            "summary": f"AI unavailable: {str(e)}"
        }

    return {
        "risk_summary": {
            "total": len(classified),
            "critical_high": len(at_risk),
            "medium": len(medium_risk),
            "low": len(low_risk)
        },
        "area_breakdown": area_data,
        "at_risk_farmers": at_risk,
        "retention_plan": ai_result
    }
