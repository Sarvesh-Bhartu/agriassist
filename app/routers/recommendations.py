from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import Farmer
from app.models.schemas import CropRecommendationRequest, CropRecommendationResponse
from app.services.recommendation_service import recommendation_service
from app.services.gamification_service import gamification_service

router = APIRouter(prefix="/api/recommendations", tags=["Crop Recommendations"])


@router.post("/", response_model=List[CropRecommendationResponse])
async def get_crop_recommendations(
    request_data: CropRecommendationRequest,
    db: Session = Depends(get_db),
    current_user: Farmer = Depends(get_current_user)
):
    """Get AI-powered crop recommendations"""
    
    # Get recommendations from AI
    recommendations = await recommendation_service.get_recommendations(
        db=db,
        farmer_id=current_user.id,
        season=request_data.season,
        budget=request_data.budget
    )
    
    # Award points for using recommendations
    await gamification_service.add_points(
        db=db,
        farmer_id=current_user.id,
        points=20,
        reason=f"Used crop recommendations for {request_data.season}",
        event_type='crop_recommendation'
    )
    
    return recommendations
