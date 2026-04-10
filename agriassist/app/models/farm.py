from sqlalchemy import Column, String, DECIMAL, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.core.database import Base


class Farm(Base):
    """Farm model"""
    __tablename__ = "farms"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    farmer_id = Column(String(36), ForeignKey('farmers.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(100), nullable=True)
    area_hectares = Column(DECIMAL(10, 2), nullable=True)
    area_acres = Column(DECIMAL(10, 2), nullable=True)
    soil_type = Column(String(50), nullable=True)  # 'black', 'red', 'alluvial', 'laterite', 'sandy'
    polygon_coordinates = Column(JSON, nullable=True)  # [{"lat": 18.52, "lon": 73.85}, ...]
    water_source = Column(String(50), nullable=True)
    irrigation_type = Column(String(50), nullable=True)
    elevation_meters = Column(DECIMAL(10, 2), nullable=True)
    carbon_credits_annual = Column(DECIMAL(10, 2), nullable=True)
    carbon_value_inr = Column(DECIMAL(12, 2), nullable=True)
    
    # Document Verification
    document_url = Column(String(255), nullable=True)
    verification_status = Column(String(20), default="pending")  # 'pending', 'approved', 'rejected'
    verification_comments = Column(String(500), nullable=True)
    
    # ── Blockchain Verification (Polygon Amoy) ────────────────────────────────
    # land_hash     : SHA-256 fingerprint of farm data at time of approval
    # blockchain_tx_hash : Polygon Amoy transaction hash (0x...)
    # blockchain_block_number : Block number where tx was confirmed
    # blockchain_status : 'pending' | 'confirmed' | 'failed' | 'already_approved'
    # blockchain_verified_at : UTC timestamp of on-chain confirmation
    # blockchain_error : Human-readable error message if blockchain_status == 'failed'
    land_hash = Column(String(66), nullable=True)                # 0x + 64 hex chars
    blockchain_tx_hash = Column(String(66), nullable=True)
    blockchain_block_number = Column(String(20), nullable=True)
    blockchain_status = Column(String(20), nullable=True)
    blockchain_verified_at = Column(DateTime, nullable=True)
    blockchain_error = Column(String(500), nullable=True)
    # ─────────────────────────────────────────────────────────────────────────

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    farmer = relationship("Farmer", back_populates="farms")
    crops = relationship("Crop", back_populates="farm", cascade="all, delete-orphan")
