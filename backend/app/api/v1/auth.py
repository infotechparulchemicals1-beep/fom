from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from jose import jwt
from datetime import datetime, timedelta, timezone
from app.config import settings
from app.db.supabase_client import get_supabase

router = APIRouter(prefix="/auth", tags=["auth"])

# Pre-provisioned designated officers (built-in roster)
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
    "yashdave182@gmail.com": {
        "user_id": "f01c52f3-87c4-4d0d-b47b-20cd8af22732",
        "name": "Yash Dave",
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

class CreateUserRequest(BaseModel):
    email: str
    password: str
    name: str
    role: str = "Field Officer"

@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    email_clean = req.email.strip().lower()
    pass_clean = req.password.strip()

    officer_info = None

    # 1. Check pre-provisioned roster
    if email_clean in DESIGNATED_OFFICERS:
        candidate = DESIGNATED_OFFICERS[email_clean]
        if candidate["password"] == pass_clean:
            officer_info = candidate

    # 2. Check Supabase Auth for users created via Dashboard or Admin API
    if not officer_info:
        try:
            sb = get_supabase()
            auth_res = sb.auth.sign_in_with_password({
                "email": email_clean,
                "password": pass_clean,
            })
            if auth_res and auth_res.user:
                user = auth_res.user
                meta = getattr(user, "user_metadata", {}) or {}
                name = meta.get("full_name") or meta.get("name") or email_clean.split("@")[0].title()
                role = meta.get("role") or "Field Officer"
                officer_info = {
                    "user_id": str(user.id),
                    "name": name,
                    "role": role,
                }
        except Exception:
            pass

    if not officer_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access Denied: Invalid email or password. Only authorized personnel may sign in.",
        )

    # Issue JWT token (30 days validity)
    exp = datetime.now(timezone.utc) + timedelta(days=30)
    claims = {
        "sub": officer_info["user_id"],
        "email": email_clean,
        "name": officer_info["name"],
        "role": officer_info["role"],
        "exp": exp,
    }
    token = jwt.encode(claims, settings.jwt_secret, algorithm="HS256")

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user_id=officer_info["user_id"],
        name=officer_info["name"],
        email=email_clean,
        role=officer_info["role"],
    )

@router.post("/create-user", status_code=status.HTTP_201_CREATED)
async def create_user(req: CreateUserRequest):
    """
    Admin endpoint to provision a new field officer account in Supabase.
    """
    sb = get_supabase()
    try:
        res = sb.auth.admin.create_user({
            "email": req.email.strip().lower(),
            "password": req.password.strip(),
            "email_confirm": True,
            "user_metadata": {
                "full_name": req.name.strip(),
                "role": req.role.strip(),
            },
        })
        return {
            "success": True,
            "user_id": str(res.user.id),
            "email": res.user.email,
            "name": req.name,
            "role": req.role,
            "message": "Officer account created successfully. They can now log in via the mobile app.",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create user: {str(e)}",
        )

