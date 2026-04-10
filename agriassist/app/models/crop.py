from sqlalchemy import Column, String, DECIMAL, DateTime, Date, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.core.database import Base


class Crop(Base):
    """Crop planting record model"""
    __tablename__ = "crops"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    farmer_id = Column(String(36), ForeignKey('farmers.id', ondelete='CASCADE'), nullable=False)
    farm_id = Column(String(36), ForeignKey('farms.id', ondelete='CASCADE'), nullable=True)
    name = Column(String(100), nullable=False)
    variety = Column(String(100), nullable=True)
    category = Column(String(50), nullable=True)  # 'Vegetable', 'Grain', 'Cash Crop'
    season = Column(String(50), nullable=True)  # 'Kharif 2025', 'Rabi 2025-26'
    planting_date = Column(Date, nullable=True)
    expected_harvest_date = Column(Date, nullable=True)
    actual_harvest_date = Column(Date, nullable=True)
    area_planted_hectares = Column(DECIMAL(10, 2), nullable=True)
    seed_cost_inr = Column(DECIMAL(12, 2), nullable=True)
    fertilizer_cost_inr = Column(DECIMAL(12, 2), nullable=True)
    total_investment_inr = Column(DECIMAL(12, 2), nullable=True)
    yield_kg = Column(DECIMAL(12, 2), nullable=True)
    sale_price_per_kg = Column(DECIMAL(10, 2), nullable=True)
    total_profit_inr = Column(DECIMAL(12, 2), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    farmer = relationship("Farmer", back_populates="crops")
    farm = relationship("Farm", back_populates="crops")


class MarketPrice(Base):
    """Market price tracking model"""
    __tablename__ = "market_prices"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    market_name = Column(String(100), nullable=False)
    market_location = Column(String(100), nullable=True)
    crop_name = Column(String(100), nullable=False, index=True)
    price_per_kg = Column(DECIMAL(10, 2), nullable=False)
    currency = Column(String(10), default='INR')
    price_date = Column(Date, nullable=False, index=True)
    trend = Column(String(20), nullable=True)  # 'rising', 'falling', 'stable'
    change_percent = Column(DECIMAL(5, 2), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
