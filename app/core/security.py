from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db

# Password hashing - using argon2 which is more reliable than bcrypt
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# HTTP Bearer for JWT
security = HTTPBearer(auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRATION_HOURS)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> dict:
    """Decode and validate JWT token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    request: Request,
    security_scopes: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Get current authenticated user from JWT token (supports both Cookie and Bearer header)"""
    from app.models.user import Farmer
    
    # 1. First try to get token from HTTPOnly cookie
    token = request.cookies.get("access_token")
    
    # 2. If not found, try to get from Authorization header (Bearer token)
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
        
    payload = decode_token(token)
    
    user_id: str = payload.get("sub")
    role: str = payload.get("role", "")
    
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
        
    # Strictly block urban farmers from accessing rural farmer routes
    if role == "urban_farmer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Urban Farmers cannot access Rural dashboards"
        )
    
    user = db.query(Farmer).filter(Farmer.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return user


async def get_current_admin(
    request: Request,
    security_scopes: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Get current authenticated admin from JWT token"""
    from app.models.user import Admin

    token = request.cookies.get("admin_access_token")

    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin not authenticated"
        )

    payload = decode_token(token)

    # Admin tokens carry "admin_id" in the "sub" claim
    admin_db_id: str = payload.get("sub")
    role: str = payload.get("role", "")

    if admin_db_id is None or role != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials"
        )

    admin = db.query(Admin).filter(Admin.id == admin_db_id, Admin.is_active == True).first()
    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin account not found or inactive"
        )

    return admin


async def get_current_urban_farmer(
    request: Request,
    security_scopes: HTTPAuthorizationCredentials = Depends(security)
):
    """Get current authenticated Urban Farmer from JWT token"""
    from app.core.neo4j_driver import neo4j_driver
    
    token = request.cookies.get("urban_access_token")
    
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Urban Farmer not authenticated"
        )
        
    payload = decode_token(token)
    
    user_id: str = payload.get("sub")
    role: str = payload.get("role", "")
    
    if user_id is None or role != "urban_farmer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Not an Urban Farmer"
        )
    
    # Verify the user actually exists in Neo4j
    session = neo4j_driver.get_session()
    try:
        result = session.run("MATCH (u:UrbanFarmer {id: $id}) RETURN u", id=user_id)
        record = result.single()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Urban Farmer account not found"
            )
        # Using dict instead of Pydantic model for internal dependency usage
        # to remain flexible with Neo4j driver records
        user_node = record["u"]
        return {
            "id": user_node["id"],
            "name": user_node["name"],
            "phone": user_node["phone"],
            "city": user_node["city"],
            "ward": user_node["ward"],
            "housing_society": user_node.get("housing_society", "N/A")
        }
    finally:
        session.close()
