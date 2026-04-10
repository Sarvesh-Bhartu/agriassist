from sqlalchemy import Column, String, Integer, Boolean, DECIMAL, DateTime, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.core.database import Base


class Farmer(Base):
    """User/Farmer model"""
    __tablename__ = "farmers"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    phone = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=True)
    password_hash = Column(String(255), nullable=False)
    language_preference = Column(String(10), default='en')  # en, hi, mr, ta
    district = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    latitude = Column(DECIMAL(10, 8), nullable=True)
    longitude = Column(DECIMAL(11, 8), nullable=True)
    total_points = Column(Integer, default=0)
    badges = Column(JSON, default=list)  # ["Plant Guardian", "Carbon Champion"]
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    farms = relationship("Farm", back_populates="farmer", cascade="all, delete-orphan")
    plant_detections = relationship("PlantDetection", back_populates="farmer", cascade="all, delete-orphan")
    crops = relationship("Crop", back_populates="farmer", cascade="all, delete-orphan")
    alert_deliveries = relationship("AlertDelivery", back_populates="farmer", cascade="all, delete-orphan")
    gamification_events = relationship("GamificationEvent", back_populates="farmer", cascade="all, delete-orphan")


class Admin(Base):
    """Admin model — managed manually, credentials set by superuser"""
    __tablename__ = "admins"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    admin_id = Column(String(20), unique=True, nullable=False, index=True)  # e.g. "T12478"
    name = Column(String(100), nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
