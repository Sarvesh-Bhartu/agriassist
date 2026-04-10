from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.core.database import Base


class GamificationEvent(Base):
    """Gamification events for tracking points and badges"""
    __tablename__ = "gamification_events"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    farmer_id = Column(String(36), ForeignKey('farmers.id', ondelete='CASCADE'), nullable=False)
    event_type = Column(String(50), nullable=False)  # 'plant_detected', 'plant_destroyed', 'farm_mapped'
    points_awarded = Column(Integer, nullable=False)
    badge_awarded = Column(String(50), nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    farmer = relationship("Farmer", back_populates="gamification_events")
