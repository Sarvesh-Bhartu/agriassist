from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import Farmer
from app.models.schemas import LeaderboardEntry
from app.services.gamification_service import gamification_service

router = APIRouter(prefix="/api/gamification", tags=["Gamification"])


@router.get("/leaderboard", response_model=List[LeaderboardEntry])
async def get_leaderboard(
    db: Session = Depends(get_db),
    limit: int = 50
):
    """Get gamification leaderboard"""
    
    leaderboard = await gamification_service.get_leaderboard(db=db, limit=limit)
    return leaderboard


@router.get("/badges")
async def get_available_badges():
    """Get all available badges"""
    
    badges = gamification_service.get_all_badges()
    return {
        "badges": [
            {
                "id": badge_id,
                **badge_info
            }
            for badge_id, badge_info in badges.items()
        ]
    }


@router.get("/my-stats")
async def get_my_stats(
    db: Session = Depends(get_db),
    current_user: Farmer = Depends(get_current_user)
):
    """Get current user's gamification stats"""
    
    # Get user's rank
    from app.models.user import Farmer as FarmerModel
    
    rank = db.query(FarmerModel).filter(
        FarmerModel.total_points > current_user.total_points
    ).count() + 1
    
    # Get badges info
    badges_info = [
        gamification_service.get_badge_info(badge_id)
        for badge_id in (current_user.badges or [])
        if badge_id in gamification_service.BADGES
    ]
    
    level_data = gamification_service.get_user_level(current_user.total_points)
    
    return {
        "rank": rank,
        "total_points": current_user.total_points,
        "badges": badges_info,
        "badges_count": len(badges_info),
        "level": level_data
    }
