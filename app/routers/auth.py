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

    access_token = create_access_token(
        data={"sub": str(new_farmer.id)},
        expires_delta=timedelta(hours=24),
    )

    return {"access_token": access_token, "token_type": "bearer"}


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

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: Farmer = Depends(get_current_user),
):
    """Get current authenticated user"""
    return current_user
