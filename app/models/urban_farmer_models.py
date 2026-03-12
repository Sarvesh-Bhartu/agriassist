from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime

class UrbanFarmerBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    phone: str = Field(..., min_length=10, max_length=15)
    email: Optional[EmailStr] = None
    city: str
    ward: str
    housing_society: str
    floor_number: int
    preferred_language: str = "English"
    upi_id: str
    aadhaar_number: str = Field(..., min_length=12, max_length=12)

class UrbanFarmerCreate(UrbanFarmerBase):
    password: str = Field(..., min_length=6)

class UrbanFarmerLogin(BaseModel):
    phone: str
    password: str

class UrbanFarmerResponse(BaseModel):
    id: str
    name: str
    phone: str
    city: str
    ward: str
    housing_society: str
    role: str = "urban_farmer"

    class Config:
        from_attributes = True

class PolygonCoord(BaseModel):
    x: float  # 0.0 to 1.0 relative to width
    y: float  # 0.0 to 1.0 relative to height

class SpaceSubmission(BaseModel):
    name: str = Field(..., description="Name for this space (e.g. South Balcony)")
    space_type: str = Field(..., description="terrace, balcony, or window_sill")
    polygons: List[List[PolygonCoord]] = Field(..., description="List of polygons, one for each uploaded image")
    
class SpaceRecordResponse(BaseModel):
    id: str
    farmer_id: str
    name: str
    space_type: str
    status: str = "pending_analysis"
    created_at: datetime

    class Config:
        from_attributes = True

class CropRecommendation(BaseModel):
    name: str
    variety: Optional[str] = None
    monthly_yield_kg: Optional[float] = None
    difficulty: Optional[str] = None
    container_size_liters: Optional[int] = None
    days_to_harvest: Optional[int] = None

class SpaceAnalysisResult(BaseModel):
    space_id: str
    status: str = "analyzed"
    estimated_area_sqm: Optional[float] = None
    sunlight_level: Optional[str] = None
    sunlight_hours_per_day: Optional[int] = None
    recommended_crops: Optional[List[CropRecommendation]] = None
    estimated_carbon_credits_per_year: Optional[float] = None
    estimated_monthly_income_inr: Optional[float] = None
    soil_recommendation: Optional[str] = None
    key_tips: Optional[List[str]] = None
    overall_suitability: Optional[str] = None
    suitability_reason: Optional[str] = None
    error: Optional[str] = None

    class Config:
        from_attributes = True

class PlantingStep(BaseModel):
    crop_name: str
    action: str  # e.g., "Sow seeds", "Transplant", "Add organic fertilizer"
    week: int    # Week number from start
    description: str

class BudgetEntry(BaseModel):
    item: str
    estimated_cost_inr: float
    category: str # e.g., "Seeds", "Soil/Media", "Containers", "Tools"

class PlantingPlan(BaseModel):
    plan_id: str
    space_id: str
    name: str = Field(..., description="e.g. Winter Balcony Garden")
    total_budget_est: float
    expected_monthly_harvest_kg: float
    steps: List[PlantingStep]
    budget_breakdown: List[BudgetEntry]
    layout_diagram_svg: Optional[str] = None
    maintenance_tips: List[str]
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        from_attributes = True

class GrowthLogCreate(BaseModel):
    note: str = Field(..., description="Observations or notes about plant growth")
    image_data: Optional[str] = Field(None, description="Base64 encoded image string for the update")

class GrowthLogResponse(BaseModel):
    id: str
    plan_id: str
    timestamp: datetime
    note: str
    image_url: Optional[str] = None
    
    class Config:
        from_attributes = True
