from sqlalchemy.orm import Session
from app.models.alert import Alert, AlertDelivery
from datetime import datetime
from typing import List


class AlertService:
    """Web-based alert management (no SMS/WhatsApp)"""
    
    async def create_alert(
        self,
        db: Session,
        alert_type: str,
        severity: str,
        title: str,
        message: str,
        district: str = None,
        state: str = None
    ) -> Alert:
        """Create a new alert"""
        
        alert = Alert(
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            district=district,
            state=state,
            is_active=True
        )
        
        db.add(alert)
        db.commit()
        db.refresh(alert)
        
        return alert
    
    async def get_alerts_for_farmer(
        self,
        db: Session,
        farmer_id: str,
        limit: int = 20
    ) -> List[Alert]:
        """Get alerts relevant to a farmer"""
        
        from app.models.user import Farmer
        
        farmer = db.query(Farmer).filter(Farmer.id == farmer_id).first()
        
        if not farmer:
            return []
        
        # Get alerts for farmer's district/state or general alerts
        alerts = db.query(Alert).filter(
            Alert.is_active == True
        ).filter(
            (Alert.district == farmer.district) | 
            (Alert.state == farmer.state) |
            (Alert.district.is_(None))
        ).order_by(
            Alert.created_at.desc()
        ).limit(limit).all()
        
        return alerts
    
    async def mark_alert_as_read(
        self,
        db: Session,
        alert_id: str,
        farmer_id: str
    ):
        """Mark alert as read by farmer"""
        
        delivery = db.query(AlertDelivery).filter(
            AlertDelivery.alert_id == alert_id,
            AlertDelivery.farmer_id == farmer_id
        ).first()
        
        if delivery:
            delivery.read_at = datetime.utcnow()
            delivery.status = 'read'
        else:
            # Create delivery record
            delivery = AlertDelivery(
                alert_id=alert_id,
                farmer_id=farmer_id,
                delivery_method='Web',
                status='read',
                read_at=datetime.utcnow()
            )
            db.add(delivery)
        
        db.commit()


# Create singleton instance
alert_service = AlertService()
