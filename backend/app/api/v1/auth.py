from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from jose import jwt
from datetime import datetime, timedelta, timezone
from app.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])

# Pre-provisioned designated officers
DESIGNATED_OFFICERS = {
    "rajesh.sharma@fscdairy.in": {
        "user_id": "off-01",
        "name": "Rajesh Sharma",
        "role": "Senior Field Officer",
        "password": "aura2026",
    },
    "suresh.patel@fscdairy.in": {
        "user_id": "off-02",
        "name": "Suresh Patel",
        "role": "Field Officer",
        "password": "aura2026",
    },
    "anil.d@fscdairy.in": {
        "user_id": "off-03",
        "name": "Anil Deshmukh",
        "role": "Route Specialist",
        "password": "aura2026",
    },
    "vikram.j@fscdairy.in": {
        "user_id": "off-04",
        "name": "Vikram Joshi",
        "role": "Field Officer",
        "password": "aura2026",
    },
    "admin@aura.io": {
        "user_id": "admin-01",
        "name": "Fleet Administrator",
        "role": "Administrator",
        "password": "aura2026",
    },
}

class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    name: str
    email: str
    role: str

@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    email_clean = req.email.strip().lower()
    officer = DESIGNATED_OFFICERS.get(email_clean)

    if not officer or officer["password"] != req.password.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access Denied: Only designated field officers authorized by administration may sign in.",
        )

    # Issue JWT token
    exp = datetime.now(timezone.utc) + timedelta(days=30)
    claims = {
        "sub": officer["user_id"],
        "email": email_clean,
        "name": officer["name"],
        "role": officer["role"],
        "exp": exp,
    }
    token = jwt.encode(claims, settings.jwt_secret, algorithm="HS256")

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user_id=officer["user_id"],
        name=officer["name"],
        email=email_clean,
        role=officer["role"],
    )
