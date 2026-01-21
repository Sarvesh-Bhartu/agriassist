from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
import os
import uuid
from datetime import datetime
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import Farmer
from app.models.plant import PlantDetection
from app.models.schemas import PlantDetectionResponse
from app.services.vision_service import vision_service
from app.services.gamification_service import gamification_service
from app.utils.image_processing import ImageProcessor
from app.core.config import settings
from typing import List

router = APIRouter(prefix="/api/plants", tags=["Plant Identification"])


@router.post("/identify")
async def identify_plant(
    image: UploadFile = File(...),
    latitude: float = Form(None),
    longitude: float = Form(None),
    db: Session = Depends(get_db),
    current_user: Farmer = Depends(get_current_user)
):
    """Identify plant from uploaded image"""
    
    # Read image
    image_bytes = await image.read()
    
    # Validate size (10MB limit)
    max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(image_bytes) > max_size:
        raise HTTPException(400, f"Image too large. Maximum {settings.MAX_UPLOAD_SIZE_MB}MB allowed")
    
    # Validate and compress image
    is_valid, msg = ImageProcessor.validate_image(image_bytes)
    if not is_valid:
        raise HTTPException(400, msg)
    
    # Compress image
    compressed_bytes = ImageProcessor.compress_image(image_bytes)
    
    # Save image
    image_filename = f"{current_user.id}_{uuid.uuid4().hex}.jpg"
    image_path = os.path.join(settings.UPLOAD_DIR, "plants", image_filename)
    
    os.makedirs(os.path.dirname(image_path), exist_ok=True)
    
    with open(image_path, "wb") as f:
        f.write(compressed_bytes)
    
    # Identify plant using Gemini Vision
    try:
        result = await vision_service.identify_plant(compressed_bytes)
    except Exception as e:
        # Clean up uploaded file
        if os.path.exists(image_path):
            os.remove(image_path)
        raise HTTPException(500, f"Plant identification failed: {str(e)}")
    
    # Calculate points
    points = 100 if result['is_invasive'] else 50
    
    # Save detection
    detection = PlantDetection(
        farmer_id=current_user.id,
        species=result['species'],
        common_name=result.get('common_name', 'Unknown'),
        local_name=result.get('local_name', ''),
        is_invasive=result['is_invasive'],
        threat_level=result.get('threat_level', 'Low'),
        confidence=result.get('confidence', 0.0),
        latitude=latitude,
        longitude=longitude,
        image_path=image_path,
        removal_method=result.get('removal_method', ''),
        points_awarded=points
    )
    db.add(detection)
    db.commit()
    db.refresh(detection)
    
    # Award points
    gamification_result = await gamification_service.add_points(
        db=db,
        farmer_id=current_user.id,
        points=points,
        reason=f"Identified {result['species']}",
        event_type='plant_detected'
    )
    
    return {
        "detection": result,
        "gamification": gamification_result,
        "detection_id": str(detection.id)
    }


@router.get("/history", response_model=List[PlantDetectionResponse])
async def get_plant_history(
    db: Session = Depends(get_db),
    current_user: Farmer = Depends(get_current_user),
    limit: int = 20
):
    """Get plant detection history"""
    
    detections = db.query(PlantDetection).filter(
        PlantDetection.farmer_id == current_user.id
    ).order_by(
        PlantDetection.detection_date.desc()
    ).limit(limit).all()
    
    return detections


@router.post("/{detection_id}/mark-destroyed")
async def mark_plant_destroyed(
    detection_id: str,
    proof_image: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: Farmer = Depends(get_current_user)
):
    """Mark invasive plant as destroyed"""
    
    detection = db.query(PlantDetection).filter(
        PlantDetection.id == detection_id,
        PlantDetection.farmer_id == current_user.id
    ).first()
    
    if not detection:
        raise HTTPException(404, "Detection not found")
    
    if not detection.is_invasive:
        raise HTTPException(400, "This plant is not marked as invasive")
    
    if detection.destroyed:
        raise HTTPException(400, "Plant already marked as destroyed")
    
    # Save proof image if provided
    proof_path = None
    if proof_image:
        image_bytes = await proof_image.read()
        proof_filename = f"{current_user.id}_proof_{uuid.uuid4().hex}.jpg"
        proof_path = os.path.join(settings.UPLOAD_DIR, "plants", proof_filename)
        
        with open(proof_path, "wb") as f:
            f.write(image_bytes)
    
    # Update detection
    detection.destroyed = True
    detection.destruction_verified = True if proof_image else False
    detection.destruction_date = datetime.utcnow()
    detection.proof_image_path = proof_path
    
    db.commit()
    
    # Award bonus points
    bonus_points = 25
    gamification_result = await gamification_service.add_points(
        db=db,
        farmer_id=current_user.id,
        points=bonus_points,
        reason=f"Destroyed invasive plant: {detection.species}",
        event_type='plant_destroyed'
    )
    
    return {
        "message": "Plant marked as destroyed",
        "bonus_points": bonus_points,
        "gamification": gamification_result
    }
