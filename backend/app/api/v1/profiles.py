from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.db.supabase_client import get_supabase
from app.auth.dependencies import get_current_user

router = APIRouter(tags=["profiles"])

ALLOWED_ROLES = {"admin", "caller", "field_officer"}


def _get_profile(sb, user_id: str) -> dict:
    res = (
        sb.table("profiles")
        .select("id, full_name, role, caller_id, created_at")
        .eq("id", user_id)
        .single()
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=404, detail="Profile not found")
    return res.data


def _require_admin(sb, user_id: str) -> dict:
    profile = _get_profile(sb, user_id)
    if profile.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return profile


class AssignRequest(BaseModel):
    field_officer_id: str
    caller_id: str


class RoleUpdateRequest(BaseModel):
    role: str


@router.get("/profiles/me")
async def get_my_profile(current_user: dict = Depends(get_current_user)):
    sb = get_supabase()
    try:
        return _get_profile(sb, current_user["user_id"])
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch profile: {exc}") from exc


@router.get("/profiles/team")
async def get_team(current_user: dict = Depends(get_current_user)):
    """Caller: list all field officers assigned to me."""
    sb = get_supabase()
    try:
        res = (
            sb.table("profiles")
            .select("id, full_name, role, caller_id, created_at")
            .eq("caller_id", current_user["user_id"])
            .execute()
        )
        return res.data or []
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch team: {exc}") from exc


@router.get("/admin/callers")
async def list_callers(current_user: dict = Depends(get_current_user)):
    """Admin: list all users with role='caller'."""
    sb = get_supabase()
    try:
        _require_admin(sb, current_user["user_id"])
        res = (
            sb.table("profiles")
            .select("id, full_name, role, caller_id, created_at")
            .eq("role", "caller")
            .execute()
        )
        return res.data or []
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch callers: {exc}") from exc


@router.get("/admin/field-officers")
async def list_field_officers(current_user: dict = Depends(get_current_user)):
    """Admin: list all field officers with their assigned caller info."""
    sb = get_supabase()
    try:
        _require_admin(sb, current_user["user_id"])
        res = (
            sb.table("profiles")
            .select("id, full_name, role, caller_id, created_at")
            .eq("role", "field_officer")
            .execute()
        )
        officers = res.data or []
        # Enrich with caller names
        caller_ids = list({o["caller_id"] for o in officers if o.get("caller_id")})
        caller_map = {}
        if caller_ids:
            c_res = (
                sb.table("profiles")
                .select("id, full_name")
                .in_("id", caller_ids)
                .execute()
            )
            caller_map = {c["id"]: c["full_name"] for c in (c_res.data or [])}
        for o in officers:
            o["caller_name"] = caller_map.get(o.get("caller_id"), None)
        return officers
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch field officers: {exc}") from exc


@router.get("/admin/callers/{caller_id}/officers")
async def get_officers_for_caller(caller_id: str, current_user: dict = Depends(get_current_user)):
    """Admin: list field officers under a specific caller."""
    sb = get_supabase()
    try:
        _require_admin(sb, current_user["user_id"])
        res = (
            sb.table("profiles")
            .select("id, full_name, role, caller_id, created_at")
            .eq("caller_id", caller_id)
            .execute()
        )
        return res.data or []
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch officers: {exc}") from exc


@router.post("/admin/profiles/assign", status_code=status.HTTP_200_OK)
async def assign_officer_to_caller(body: AssignRequest, current_user: dict = Depends(get_current_user)):
    """Admin: permanently assign a field officer to a caller."""
    sb = get_supabase()
    try:
        _require_admin(sb, current_user["user_id"])
        res = (
            sb.table("profiles")
            .update({"caller_id": body.caller_id})
            .eq("id", body.field_officer_id)
            .execute()
        )
        if not res.data:
            raise HTTPException(status_code=404, detail="Field officer profile not found")
        return {"success": True, "updated": res.data[0]}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to assign officer: {exc}") from exc


@router.put("/admin/profiles/{user_id}/role")
async def update_user_role(
    user_id: str,
    body: RoleUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    """Admin: change a user's role."""
    if body.role not in ALLOWED_ROLES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid role. Allowed: {sorted(ALLOWED_ROLES)}",
        )
    sb = get_supabase()
    try:
        _require_admin(sb, current_user["user_id"])
        res = (
            sb.table("profiles")
            .update({"role": body.role})
            .eq("id", user_id)
            .execute()
        )
        if not res.data:
            raise HTTPException(status_code=404, detail="Profile not found")
        return {"success": True, "updated": res.data[0]}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to update role: {exc}") from exc


@router.get("/admin/all-users")
async def get_all_users_with_roles(current_user: dict = Depends(get_current_user)):
    """Admin: list all users with their roles (for Team Management UI)."""
    sb = get_supabase()
    try:
        _require_admin(sb, current_user["user_id"])

        # Get all profiles
        profiles_res = sb.table("profiles").select("id, full_name, role, caller_id, created_at").execute()
        profiles = profiles_res.data or []

        # Get auth user emails
        users_map = {}
        try:
            auth_users = sb.auth.admin.list_users()
            user_list = auth_users.users if hasattr(auth_users, "users") else (auth_users if isinstance(auth_users, list) else [])
            users_map = {str(u.id): getattr(u, "email", "") for u in user_list}
        except Exception:
            pass

        for p in profiles:
            p["email"] = users_map.get(p["id"], "")

        return profiles
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch all users: {exc}") from exc

