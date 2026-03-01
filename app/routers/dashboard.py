from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import Farmer
from app.models.farm import Farm
from app.models.plant import PlantDetection
from app.models.crop import Crop
from sqlalchemy import func

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/stats")
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: Farmer = Depends(get_current_user)
):
    """Get dashboard statistics for current user"""
    
    # Get farm count and total area
    farms = db.query(Farm).filter(Farm.farmer_id == current_user.id).all()
    total_area = sum([float(f.area_hectares or 0) for f in farms])
    total_carbon_value = sum([float(f.carbon_value_inr or 0) for f in farms])
    
    # Get plant detection stats
    total_plants = db.query(func.count(PlantDetection.id)).filter(
        PlantDetection.farmer_id == current_user.id
    ).scalar()
    
    invasive_plants = db.query(func.count(PlantDetection.id)).filter(
        PlantDetection.farmer_id == current_user.id,
        PlantDetection.is_invasive == True
    ).scalar()
    
    destroyed_plants = db.query(func.count(PlantDetection.id)).filter(
        PlantDetection.farmer_id == current_user.id,
        PlantDetection.destroyed == True
    ).scalar()
    
    # Get crop stats
    total_crops = db.query(func.count(Crop.id)).filter(
        Crop.farmer_id == current_user.id
    ).scalar()
    
    # Recent activity
    recent_detections = db.query(PlantDetection).filter(
        PlantDetection.farmer_id == current_user.id
    ).order_by(PlantDetection.detection_date.desc()).limit(5).all()
    
    from app.services.gamification_service import gamification_service
    level_data = gamification_service.get_user_level(current_user.total_points)

    return {
        "user": {
            "name": current_user.name,
            "phone": current_user.phone,
            "total_points": current_user.total_points,
            "badges": current_user.badges or [],
            "district": current_user.district,
            "state": current_user.state,
            "level": level_data
        },
        "farms": {
            "count": len(farms),
            "total_area_hectares": round(total_area, 2),
            "total_carbon_value_inr": round(total_carbon_value, 2)
        },
        "plants": {
            "total_detected": total_plants,
            "invasive_found": invasive_plants,
            "destroyed": destroyed_plants
        },
        "crops": {
            "total": total_crops
        },
        "recent_activity": [
            {
                "id": str(d.id),
                "species": d.species,
                "common_name": d.common_name,
                "is_invasive": d.is_invasive,
                "date": d.detection_date.isoformat()
            }
            for d in recent_detections
        ]
    }
