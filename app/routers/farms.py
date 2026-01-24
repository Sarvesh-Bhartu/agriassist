from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import Farmer
from app.models.farm import Farm
from app.models.schemas import FarmCreate, FarmResponse
from app.services.farm_calculator import farm_calculator
from app.services.carbon_service import carbon_service
from app.services.gamification_service import gamification_service

router = APIRouter(prefix="/api/farms", tags=["Farm Management"])


@router.post("/", response_model=FarmResponse)
async def create_farm(
    farm_data: FarmCreate,
    db: Session = Depends(get_db),
    current_user: Farmer = Depends(get_current_user)
):
    """Create a new farm"""
    
    # Check if user already has a farm - REMOVED strictly to allow multiple farms
    # existing = db.query(Farm).filter(Farm.farmer_id == current_user.id).first()
    # if existing:
    #     raise HTTPException(400, "Farmer already has a farm. Use update endpoint instead.")
    
    # Calculate area if coordinates provided
    area_hectares = None
    area_acres = None
    
    if farm_data.polygon_coordinates and len(farm_data.polygon_coordinates) >= 3:
        try:
            calc_result = farm_calculator.calculate_area(farm_data.polygon_coordinates)
            area_hectares = calc_result['area_hectares']
            area_acres = calc_result['area_acres']
        except Exception as e:
            raise HTTPException(400, f"Area calculation failed: {str(e)}")
    
    # Calculate carbon credits if we have area and soil type
    carbon_credits = None
    carbon_value = None
    
    if area_hectares and farm_data.soil_type:
        try:
            carbon_result = carbon_service.calculate_credits(
                area_hectares=float(area_hectares),
                soil_type=farm_data.soil_type
            )
            carbon_credits = carbon_result['annual_credits']
            carbon_value = carbon_result['annual_value_inr']
        except Exception as e:
            # Don't fail farm creation if carbon calculation fails
            pass
    
    # Create farm
    new_farm = Farm(
        farmer_id=current_user.id,
        name=farm_data.name,
        area_hectares=area_hectares,
        area_acres=area_acres,
        soil_type=farm_data.soil_type,
        polygon_coordinates=farm_data.polygon_coordinates,
        water_source=farm_data.water_source,
        irrigation_type=farm_data.irrigation_type,
        carbon_credits_annual=carbon_credits,
        carbon_value_inr=carbon_value
    )
    
    db.add(new_farm)
    db.commit()
    db.refresh(new_farm)
    
    # Award points for farm mapping
    await gamification_service.add_points(
        db=db,
        farmer_id=current_user.id,
        points=100,
        reason="Mapped farm and calculated carbon credits",
        event_type='farm_mapped'
    )
    
    return new_farm


@router.get("/", response_model=List[FarmResponse])
async def get_farms(
    db: Session = Depends(get_db),
    current_user: Farmer = Depends(get_current_user)
):
    """Get all farms for current user"""
    
    farms = db.query(Farm).filter(Farm.farmer_id == current_user.id).all()
    return farms


@router.get("/{farm_id}", response_model=FarmResponse)
async def get_farm(
    farm_id: str,
    db: Session = Depends(get_db),
    current_user: Farmer = Depends(get_current_user)
):
    """Get specific farm details"""
    
    farm = db.query(Farm).filter(
        Farm.id == farm_id,
        Farm.farmer_id == current_user.id
    ).first()
    
    if not farm:
        raise HTTPException(404, "Farm not found")
    
    return farm


@router.post("/{farm_id}/calculate-carbon")
async def calculate_carbon_credits(
    farm_id: str,
    crop_type: str = "mixed",
    db: Session = Depends(get_db),
    current_user: Farmer = Depends(get_current_user)
):
    """Calculate carbon credits for a farm"""
    
    farm = db.query(Farm).filter(
        Farm.id == farm_id,
        Farm.farmer_id == current_user.id
    ).first()
    
    if not farm:
        raise HTTPException(404, "Farm not found")
    
    if not farm.area_hectares or not farm.soil_type:
        raise HTTPException(400, "Farm must have area and soil type for carbon calculation")
    
    try:
        result = carbon_service.calculate_credits(
            area_hectares=float(farm.area_hectares),
            soil_type=farm.soil_type,
            crop_type=crop_type
        )
        
        # Update farm
        farm.carbon_credits_annual = result['annual_credits']
        farm.carbon_value_inr = result['annual_value_inr']
        db.commit()
        
        return result
        
    except Exception as e:
        raise HTTPException(400, f"Carbon calculation failed: {str(e)}")
