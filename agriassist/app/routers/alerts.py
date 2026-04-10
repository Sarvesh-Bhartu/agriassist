from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import Farmer
from app.models.schemas import AlertResponse
from app.services.alert_service import alert_service

router = APIRouter(prefix="/api/alerts", tags=["Alerts"])


@router.get("/", response_model=List[AlertResponse])
async def get_alerts(
    db: Session = Depends(get_db),
    current_user: Farmer = Depends(get_current_user),
    limit: int = 20
):
    """Get alerts for current farmer"""
    
    alerts = await alert_service.get_alerts_for_farmer(
        db=db,
        farmer_id=current_user.id,
        limit=limit
    )
    
    return alerts


@router.post("/{alert_id}/mark-read")
async def mark_alert_read(
    alert_id: str,
    db: Session = Depends(get_db),
    current_user: Farmer = Depends(get_current_user)
):
    """Mark an alert as read"""
    
    await alert_service.mark_alert_as_read(
        db=db,
        alert_id=alert_id,
        farmer_id=current_user.id
    )
    
    return {"message": "Alert marked as read"}
