from sqlalchemy import Column, String, Boolean, DECIMAL, DateTime, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.core.database import Base


class Alert(Base):
    """Alert/notification model"""
    __tablename__ = "alerts"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    alert_type = Column(String(50), nullable=False)  # 'Disease', 'Price', 'General'
    severity = Column(String(20), nullable=False)  # 'Low', 'Medium', 'High', 'Critical'
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    district = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    latitude = Column(DECIMAL(10, 8), nullable=True)
    longitude = Column(DECIMAL(11, 8), nullable=True)
    radius_km = Column(Integer, nullable=True)  # Alert radius
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    deliveries = relationship("AlertDelivery", back_populates="alert", cascade="all, delete-orphan")


class AlertDelivery(Base):
    """Alert delivery tracking"""
    __tablename__ = "alert_deliveries"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    alert_id = Column(String(36), ForeignKey('alerts.id', ondelete='CASCADE'), nullable=False)
    farmer_id = Column(String(36), ForeignKey('farmers.id', ondelete='CASCADE'), nullable=False)
    delivery_method = Column(String(20), default='Web')  # 'Web' only (no SMS/WhatsApp)
    delivered_at = Column(DateTime, default=datetime.utcnow)
    read_at = Column(DateTime, nullable=True)
    status = Column(String(20), default='sent')  # 'sent', 'read'
    
    # Relationships
    alert = relationship("Alert", back_populates="deliveries")
    farmer = relationship("Farmer", back_populates="alert_deliveries")
