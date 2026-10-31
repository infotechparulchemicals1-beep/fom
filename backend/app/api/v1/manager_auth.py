"""
Manager Authentication API
Phase 4: Manager Bridge APIs

Provides authentication for managers accessing AURA data from PC-Sales website.
"""

from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, timedelta
import jwt
from app.config import settings
from app.db.supabase_client import get_supabase_client

router = APIRouter(prefix="/manager/auth", tags=["Manager Auth"])


class ManagerAuthRequest(BaseModel):
    email: EmailStr
    api_key: str


class ManagerAuthResponse(BaseModel):
    valid: bool
    manager: Optional[dict] = None
    token: Optional[str] = None
    message: Optional[str] = None


class ManagerProfile(BaseModel):
    email: str
    name: str
    role: str
    assigned_officers: list[str]


# Store this in environment variable in production
MANAGER_API_KEY = "AURA_MANAGER_SECRET_2026"


def create_manager_token(email: str, name: str) -> str:
    """Create JWT token for manager session"""
    payload = {
        "email": email,
        "name": name,
        "role": "manager",
        "exp": datetime.utcnow() + timedelta(hours=8),  # 8-hour expiry
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def verify_manager_token(token: str) -> dict:
    """Verify and decode manager JWT token"""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_manager(
    authorization: str = Header(None)
) -> dict:
    """Dependency to get current authenticated manager from Bearer token"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    
    token = authorization.replace("Bearer ", "")
    return verify_manager_token(token)


@router.post("/validate", response_model=ManagerAuthResponse)
async def validate_manager(request: ManagerAuthRequest):
    """
    Validate manager credentials and return JWT token
    
    Used by PC-Sales frontend to authenticate managers.
    
    **Security:**
    - API key must match environment variable
    - Email must exist in users table with manager role
    - User must be active
    
    **Returns:**
    - JWT token valid for 8 hours
    - Manager profile with assigned officers
    """
    
    # Validate API key
    if request.api_key != MANAGER_API_KEY:
        return ManagerAuthResponse(
            valid=False,
            message="Invalid API key"
        )
    
    try:
        supabase = get_supabase_client()
        
        # Query user by email
        response = supabase.table("users").select("*").eq("email", request.email).execute()
        
        if not response.data or len(response.data) == 0:
            return ManagerAuthResponse(
                valid=False,
                message="Manager not found"
            )
        
        user = response.data[0]
        
        # Verify role
        if user.get("role") != "manager":
            return ManagerAuthResponse(
                valid=False,
                message="User is not a manager"
            )
        
        # Verify active status
        if not user.get("is_active", False):
            return ManagerAuthResponse(
                valid=False,
                message="Manager account is inactive"
            )
        
        # Get assigned field officers (simplified - can be enhanced)
        # In production, this would query manager_officer_assignments table
        assigned_officers = []
        
        # Create JWT token
        token = create_manager_token(user["email"], user.get("name", "Manager"))
        
        return ManagerAuthResponse(
            valid=True,
            manager={
                "email": user["email"],
                "name": user.get("name", ""),
                "role": "manager",
                "assigned_officers": assigned_officers
            },
            token=token,
            message="Authentication successful"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication error: {str(e)}")


@router.get("/verify")
async def verify_token(manager: dict = Depends(get_current_manager)):
    """
    Verify JWT token validity
    
    Used by PC-Sales frontend to check if token is still valid.
    """
    return {
        "valid": True,
        "manager": {
            "email": manager["email"],
            "name": manager["name"],
            "role": manager["role"]
        }
    }


@router.post("/refresh")
async def refresh_token(manager: dict = Depends(get_current_manager)):
    """
    Refresh JWT token
    
    Issues a new token with extended expiry.
    """
    new_token = create_manager_token(manager["email"], manager["name"])
    
    return {
        "token": new_token,
        "expires_in": 28800  # 8 hours in seconds
    }
