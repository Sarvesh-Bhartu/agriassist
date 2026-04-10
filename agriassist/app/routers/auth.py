from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta, datetime

from app.core.database import get_db
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user,
)
from app.models.user import Farmer
from app.models.schemas import UserRegister, UserLogin, Token, UserResponse
from app.utils.validators import Validators
from app.services.graph_service import graph_service

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=Token)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """Register a new farmer"""

    # Validate phone
    is_valid, phone_clean = Validators.validate_phone(user_data.phone)
    if not is_valid:
        raise HTTPException(status_code=400, detail=phone_clean)

    # Check phone uniqueness
    if db.query(Farmer).filter(Farmer.phone == phone_clean).first():
        raise HTTPException(status_code=400, detail="Phone number already registered")

    # Validate email if provided
    email_clean = None
    if user_data.email:
        is_valid_email, email_clean = Validators.validate_email(user_data.email)
        if not is_valid_email:
            raise HTTPException(status_code=400, detail=email_clean)

        if db.query(Farmer).filter(Farmer.email == email_clean).first():
            raise HTTPException(status_code=400, detail="Email already registered")

    # Validate coordinates if provided
    if user_data.latitude and user_data.longitude:
        is_valid_coords, msg = Validators.validate_coordinates(
            user_data.latitude, user_data.longitude
        )
        if not is_valid_coords:
            raise HTTPException(status_code=400, detail=msg)

    # Create farmer
    new_farmer = Farmer(
        phone=phone_clean,
        name=user_data.name,
        email=email_clean,
        password_hash=get_password_hash(user_data.password),
        district=user_data.district,
        state=user_data.state,
        latitude=user_data.latitude,
        longitude=user_data.longitude,
        badges=["early_adopter"],
    )

    db.add(new_farmer)
    db.commit()
    db.refresh(new_farmer)

    # Sync with Neo4j Graph
    try:
        graph_service.create_farmer_node(
            farmer_id=new_farmer.id,
            phone=new_farmer.phone,
            name=new_farmer.name,
            district=new_farmer.district,
            state=new_farmer.state
        )
    except Exception as e:
        print(f"Warning: Failed to sync farmer to Neo4j: {e}")

    access_token = create_access_token(
        data={"sub": str(new_farmer.id)},
        expires_delta=timedelta(hours=24),
    )

    from fastapi.responses import JSONResponse
    response = JSONResponse(content={"access_token": access_token, "token_type": "bearer"})
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=24 * 3600,
        samesite="lax",
        secure=False
    )
    return response


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """Login farmer"""

    is_valid, phone_clean = Validators.validate_phone(credentials.phone)
    if not is_valid:
        raise HTTPException(status_code=400, detail=phone_clean)

    farmer = db.query(Farmer).filter(Farmer.phone == phone_clean).first()

    if not farmer or not verify_password(credentials.password, farmer.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect phone number or password",
        )

    if not farmer.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    farmer.last_active = datetime.utcnow()
    db.commit()

    access_token = create_access_token(
        data={"sub": str(farmer.id)},
        expires_delta=timedelta(hours=24),
    )

    from fastapi.responses import JSONResponse
    response = JSONResponse(content={"access_token": access_token, "token_type": "bearer"})
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=24 * 3600,
        samesite="lax",
        secure=False
    )
    return response


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: Farmer = Depends(get_current_user),
):
    """Get current authenticated user"""
    from app.services.gamification_service import gamification_service
    
    level_data = gamification_service.get_user_level(current_user.total_points)
    
    return {
        "id": current_user.id,
        "phone": current_user.phone,
        "name": current_user.name,
        "email": current_user.email,
        "total_points": current_user.total_points,
        "badges": current_user.badges or [],
        "district": current_user.district,
        "state": current_user.state,
        "level": level_data
    }
