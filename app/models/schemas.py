from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal


# ============= Auth Schemas =============
class UserRegister(BaseModel):
    phone: str
    name: str
    email: Optional[EmailStr] = None
    password: str
    district: Optional[str] = None
    state: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class UserLogin(BaseModel):
    phone: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LevelData(BaseModel):
    current_level: str
    current_icon: str
    next_level: Optional[str]
    next_icon: Optional[str]
    progress_percentage: int
    points_to_next: int
    current_points: int
    next_tier_points: int


class UserResponse(BaseModel):
    id: str
    phone: str
    name: str
    email: Optional[str]
    total_points: int
    badges: List[str]
    district: Optional[str]
    state: Optional[str]
    level: Optional[LevelData] = None
    
    class Config:
        from_attributes = True


# ============= Plant Schemas =============
class PlantIdentificationResponse(BaseModel):
    species: str
    common_name: Optional[str]
    local_name: Optional[str]
    is_invasive: bool
    threat_level: Optional[str]
    confidence: Optional[float]
    removal_method: Optional[str]


class PlantDetectionResponse(BaseModel):
    id: str
    species: str
    common_name: Optional[str]
    is_invasive: bool
    threat_level: Optional[str]
    detection_date: datetime
    points_awarded: int
    image_path: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    destroyed: bool
    destruction_verified: bool
    
    class Config:
        from_attributes = True


# ============= Farm Schemas =============
class FarmCreate(BaseModel):
    name: Optional[str]
    soil_type: Optional[str]
    polygon_coordinates: Optional[List[dict]]  # [{"lat": 18.52, "lon": 73.85}]
    water_source: Optional[str]
    irrigation_type: Optional[str]


class FarmResponse(BaseModel):
    id: str
    name: Optional[str]
    area_hectares: Optional[Decimal]
    area_acres: Optional[Decimal]
    soil_type: Optional[str]
    polygon_coordinates: Optional[List[dict]]
    water_source: Optional[str]
    irrigation_type: Optional[str]
    carbon_credits_annual: Optional[Decimal]
    carbon_value_inr: Optional[Decimal]
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============= Crop Schemas =============
class CropRecommendationRequest(BaseModel):
    season: str
    budget: float


class CropRecommendationResponse(BaseModel):
    crop: str
    variety: Optional[str]
    expected_profit_min: float
    expected_profit_max: float
    investment_breakdown: dict
    risk_factors: List[str]
    timeline: str
    advice: str


# ============= Alert Schemas =============
class AlertResponse(BaseModel):
    id: str
    alert_type: str
    severity: str
    title: str
    message: str
    created_at: datetime
    is_active: bool
    
    class Config:
        from_attributes = True


# ============= Gamification Schemas =============
class GamificationResponse(BaseModel):
    points_added: int
    total_points: int
    new_badges: List[str]


class LeaderboardEntry(BaseModel):
    rank: int
    name: str
    points: int
    badges: List[str]
    badges_icons: List[str] = []
    district: Optional[str]
