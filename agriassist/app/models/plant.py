from sqlalchemy import Column, String, Boolean, DECIMAL, DateTime, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.core.database import Base


class PlantDetection(Base):
    """Plant detection/identification model"""
    __tablename__ = "plant_detections"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    farmer_id = Column(String(36), ForeignKey('farmers.id', ondelete='CASCADE'), nullable=False)
    species = Column(String(100), nullable=False)
    common_name = Column(String(100), nullable=True)
    local_name = Column(String(100), nullable=True)
    is_invasive = Column(Boolean, default=False)
    threat_level = Column(String(20), nullable=True)  # 'High', 'Medium', 'Low'
    confidence = Column(DECIMAL(5, 2), nullable=True)  # 0.00 to 1.00
    detection_date = Column(DateTime, default=datetime.utcnow, index=True)
    latitude = Column(DECIMAL(10, 8), nullable=True)
    longitude = Column(DECIMAL(11, 8), nullable=True)
    image_path = Column(String(255), nullable=True)
    removal_method = Column(Text, nullable=True)
    destroyed = Column(Boolean, default=False)
    destruction_verified = Column(Boolean, default=False)
    destruction_date = Column(DateTime, nullable=True)
    proof_image_path = Column(String(255), nullable=True)
    points_awarded = Column(Integer, default=0)
    
    # Relationships
    farmer = relationship("Farmer", back_populates="plant_detections")
