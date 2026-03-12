from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.core.neo4j_driver import neo4j_driver
from app.core.security import get_password_hash, verify_password, create_access_token, get_current_urban_farmer
from app.models.urban_farmer_models import UrbanFarmerCreate, UrbanFarmerResponse
import uuid
import datetime

import os
from fastapi.templating import Jinja2Templates

# Calculate templates directory relative to this file
# __file__ is app/routers/urban_farmer/auth.py
# dir(__file__) -> urban_farmer
# dir(dir) -> routers
# dir(dir) -> app
APP_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
templates = Jinja2Templates(directory=os.path.join(APP_DIR, "templates"))

router = APIRouter(prefix="/urban/auth", tags=["Urban Auth"])

@router.get("/login", response_class=HTMLResponse)
async def urban_login_page():
    """Redirect to unified login page (pre-select Urban Farmer tab via hash)"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/login#urban", status_code=302)

@router.get("/register", response_class=HTMLResponse)
async def urban_register_page():
    """Redirect to unified register page"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/register#urban", status_code=302)

@router.post("/register", response_model=UrbanFarmerResponse)
async def register_urban_farmer(farmer: UrbanFarmerCreate):
    """API endpoint to register a new Urban Farmer"""
    session = neo4j_driver.get_session()
    try:
        # Check if phone exists
        result = session.run("MATCH (u:UrbanFarmer {phone: $phone}) RETURN u", phone=farmer.phone)
        if result.single():
            raise HTTPException(status_code=400, detail="Phone number already registered")
            
        uf_id = str(uuid.uuid4())
        hashed_password = get_password_hash(farmer.password)
        
        # Mask Aadhaar
        masked_aadhaar = "XXXXXXXX" + farmer.aadhaar_number[-4:] if len(farmer.aadhaar_number) == 12 else farmer.aadhaar_number
        
        query = '''
        MERGE (r:Region {name: $city})
        CREATE (u:UrbanFarmer {
            id: $id,
            name: $name,
            phone: $phone,
            email: $email,
            city: $city,
            ward: $ward,
            housing_society: $housing_society,
            floor_number: $floor_number,
            preferred_language: $preferred_language,
            upi_id: $upi_id,
            aadhaar_masked: $aadhaar_masked,
            password_hash: $password_hash,
            created_at: datetime()
        })
        CREATE (u)-[:LIVES_IN]->(r)
        RETURN u
        '''
        
        result = session.run(
            query, 
            id=uf_id,
            name=farmer.name,
            phone=farmer.phone,
            email=farmer.email,
            city=farmer.city,
            ward=farmer.ward,
            housing_society=farmer.housing_society,
            floor_number=farmer.floor_number,
            preferred_language=farmer.preferred_language,
            upi_id=farmer.upi_id,
            aadhaar_masked=masked_aadhaar,
            password_hash=hashed_password
        )
        
        record = result.single()
        if not record:
            raise HTTPException(status_code=500, detail="Failed to create urban farmer")
            
        user_node = record["u"]
        return UrbanFarmerResponse(
            id=user_node["id"],
            name=user_node["name"],
            phone=user_node["phone"],
            city=user_node["city"],
            ward=user_node["ward"],
            housing_society=user_node["housing_society"],
            role="urban_farmer"
        )
    finally:
        session.close()

@router.post("/login")
async def login_urban_farmer(form_data: OAuth2PasswordRequestForm = Depends()):
    """API endpoint for Urban Farmer login"""
    session = neo4j_driver.get_session()
    try:
        result = session.run("MATCH (u:UrbanFarmer {phone: $phone}) RETURN u", phone=form_data.username)
        record = result.single()
        
        if not record:
            raise HTTPException(status_code=401, detail="Invalid phone or password")
            
        user_node = record["u"]
        if not verify_password(form_data.password, user_node["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid phone or password")
            
        access_token = create_access_token(
            data={"sub": user_node["id"], "role": "urban_farmer"}, 
            expires_delta=datetime.timedelta(hours=24)
        )
        
        from fastapi.responses import JSONResponse
        response = JSONResponse(content={"access_token": access_token, "token_type": "bearer", "role": "urban_farmer"})
        response.set_cookie(
            key="urban_access_token",
            value=access_token,
            httponly=True,
            max_age=24 * 3600,
            samesite="lax",
            secure=False # Set to True in production with HTTPS
        )
        return response
    finally:
        session.close()

@router.get("/me", response_model=UrbanFarmerResponse)
async def get_urban_farmer_me(current_user: dict = Depends(get_current_urban_farmer)):
    """Get current urban farmer profile info"""
    return UrbanFarmerResponse(
        id=current_user["id"],
        name=current_user["name"],
        phone=current_user["phone"],
        city=current_user["city"],
        ward=current_user["ward"],
        housing_society=current_user["housing_society"],
        role="urban_farmer"
    )
