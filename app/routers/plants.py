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
    
    # Dual Engine: 1. Offline YOLO for bounding boxes
    try:
        output_dir = os.path.dirname(image_path)
        yolo_result = vision_service.scan_plant(image_path, output_dir)
        annotated_filename = yolo_result.get("annotated_image_path") if yolo_result.get("success") else None
        
        # Dual Engine: 2. Cloud Gemini for precise botanical identification
        from app.services.gemini_service import gemini_service
        gemini_data = await gemini_service.identify_plant(image_bytes)
        
        if gemini_data:
            species_name = gemini_data.get("species", "Unknown")
            common_name = gemini_data.get("common_name", species_name)
            local_name = gemini_data.get("local_name", "")
            is_invasive = bool(gemini_data.get("is_invasive", False))
            threat_level = gemini_data.get("threat_level", "High" if is_invasive else "Low")
            confidence = float(gemini_data.get("confidence", 0.95))
            removal_method = gemini_data.get("removal_method", "")
            status = threat_level
        else:
            # Fallback to YOLO if Gemini fails/network error
            predictions = yolo_result.get("predictions", [])
            if predictions:
                best_pred = max(predictions, key=lambda x: x["confidence"])
                species_name = best_pred["class"]
                common_name = species_name
                confidence = best_pred["confidence"]
                status = best_pred["status"]
            else:
                species_name = "Unknown"
                common_name = "Unknown"
                confidence = 0.0
                status = "Unknown"
                
            local_name = ""
            is_invasive = ("blight" in status.lower() or "disease" in status.lower())
            threat_level = "High" if is_invasive else "Low"
            removal_method = "Please consult recommended treatment." if is_invasive else ""
        
        # Point the saved image path to the annotated image from YOLO
        if annotated_filename:
            image_path = os.path.join("uploads/plants", annotated_filename)
            
    except Exception as e:
        # Clean up uploaded file
        if os.path.exists(image_path):
            os.remove(image_path)
        raise HTTPException(500, f"Plant identification failed: {str(e)}")
    
    # Calculate points
    points = 100 if is_invasive else 50
    
    # Save detection
    detection = PlantDetection(
        farmer_id=current_user.id,
        species=species_name,
        common_name=common_name,
        local_name=local_name,
        is_invasive=is_invasive,
        threat_level=threat_level,
        confidence=confidence,
        latitude=latitude,
        longitude=longitude,
        image_path=image_path,
        removal_method=removal_method,
        points_awarded=points
    )
    db.add(detection)
    db.commit()
    db.refresh(detection)
    
    # Update gamification
    gamification_result = await gamification_service.add_points(
        db=db,
        farmer_id=current_user.id,
        points=points,
        reason=f"Scanned {species_name}",
        event_type="plant_detected"
    )
    
    # --- Neo4j Graph Integration & Alerts (Journey A) ---
    neighbors = []
    try:
        from app.services.graph_service import graph_service
        g_lat = float(latitude) if latitude and str(latitude).strip() else None
        g_lon = float(longitude) if longitude and str(longitude).strip() else None
        
        # 1. Record detection in Graph
        graph_service.create_detection_record(
            farmer_id=str(current_user.id),
            detection_id=str(detection.id),
            species=species_name,
            gps_lat=g_lat,
            gps_lon=g_lon,
            confidence=confidence
        )
        
        # 2. Find neighbors within 5km and alert
        if is_invasive and g_lat and g_lon:
            neighbors = graph_service.find_nearby_farmers(
                plant_id=str(detection.id),
                farmer_id=str(current_user.id),
                max_distance_meters=5000
            )
            
            # Real Twilio SMS Alert
            if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN and settings.TWILIO_PHONE_NUMBER:
                from twilio.rest import Client
                try:
                    twilio_client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                    for neighbor in neighbors:
                        # Ensure the phone number has the +91 country code
                        target_phone = neighbor['phone']
                        if len(target_phone) == 10 and target_phone.isdigit():
                            target_phone = f"+91{target_phone}"
                        elif not target_phone.startswith('+'):
                            target_phone = f"+{target_phone}"
                            
                        msg_body = f"⚠️ AgriAssist Alert: {species_name} detected {neighbor['distance_km']}km near your farm! Please remain vigilant."
                        message = twilio_client.messages.create(
                            body=msg_body,
                            from_=settings.TWILIO_PHONE_NUMBER,
                            to=target_phone
                        )
                        print(f"✅ Real SMS sent to {target_phone}! Message ID: {message.sid}")
                except Exception as sms_error:
                    print(f"❌ Failed to send Twilio SMS: {sms_error}")
            else:
                # Fallback to simulation if keys are missing
                for neighbor in neighbors:
                    print(f"📱 WHATSAPP ALERT to {neighbor['phone']}: '⚠️ {species_name} detected {neighbor['distance_km']}km from your farm!'")
                
    except Exception as e:
        print(f"Warning: Graph integration failed: {e}")
    # --------------------------------------------------
    
    return {
        "status": "threat_detected" if is_invasive else "no_threats",
        "detection": {
            "species": species_name,
            "status": status,
            "confidence": confidence,
            "is_invasive": is_invasive,
            "threat_level": "High" if is_invasive else "Low",
            "image_url": f"/{image_path}"
        },
        "gamification": gamification_result,
        "detection_id": str(detection.id),
        "neighbors_alerted": len(neighbors)
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
