from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from app.db.supabase_client import get_supabase
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/visits", tags=["visits"])

IST = timedelta(hours=5, minutes=30)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _ist_day_bounds(date_str: Optional[str] = None):
    """Return (start_utc_iso, end_utc_iso) for a given IST date (today if None)."""
    if date_str:
        ist_midnight = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        start_utc = ist_midnight - IST
    else:
        now_ist = _now_utc() + IST
        ist_midnight = now_ist.replace(hour=0, minute=0, second=0, microsecond=0)
        start_utc = (ist_midnight - IST).replace(tzinfo=timezone.utc)
    end_utc = start_utc + timedelta(days=1)
    return start_utc.isoformat(), end_utc.isoformat()


class CheckinRequest(BaseModel):
    customer_id: str
    checkin_lat: Optional[float] = None
    checkin_lng: Optional[float] = None
    # Allow mobile to sync a past checkin time (offline support)
    checked_in_at: Optional[str] = None
    # Allow mobile to pass its local visit ID for idempotency
    visit_id: Optional[str] = None


class CheckoutRequest(BaseModel):
    visit_id: str
    notes: Optional[str] = None
    checkout_lat: Optional[float] = None
    checkout_lng: Optional[float] = None
    # Allow mobile to pass exact checkout time (offline sync)
    checked_out_at: Optional[str] = None
    duration_minutes: Optional[int] = None


@router.post("/checkin", status_code=status.HTTP_201_CREATED)
async def checkin(body: CheckinRequest, current_user: dict = Depends(get_current_user)):
    """Field officer checks in at a customer location."""
    sb = get_supabase()
    try:
        now = body.checked_in_at or _now_utc().isoformat()
        payload: dict = {
            "user_id": current_user["user_id"],
            "customer_id": body.customer_id,
            "checked_in_at": now,
            "sync_status": "synced",
        }
        if body.checkin_lat is not None:
            payload["checkin_lat"] = body.checkin_lat
        if body.checkin_lng is not None:
            payload["checkin_lng"] = body.checkin_lng
        # Support idempotent upsert if visit_id provided
        if body.visit_id:
            payload["id"] = body.visit_id

        res = sb.table("customer_visits").insert(payload).execute()
        if not res.data:
            raise HTTPException(status_code=500, detail="Checkin insert returned no data")
        return res.data[0]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Checkin failed: {exc}") from exc


@router.post("/checkout")
async def checkout(body: CheckoutRequest, current_user: dict = Depends(get_current_user)):
    """Field officer checks out from a customer visit."""
    sb = get_supabase()
    try:
        # Fetch existing visit to compute duration if not provided
        visit_res = (
            sb.table("customer_visits")
            .select("id, checked_in_at, user_id")
            .eq("id", body.visit_id)
            .single()
            .execute()
        )
        if not visit_res.data:
            raise HTTPException(status_code=404, detail="Visit not found")
        visit = visit_res.data

        now = body.checked_out_at or _now_utc().isoformat()
        duration_minutes = body.duration_minutes
        if duration_minutes is None:
            checked_in_at_str = visit.get("checked_in_at", "")
            if checked_in_at_str:
                try:
                    checked_in_dt = datetime.fromisoformat(checked_in_at_str.replace("Z", "+00:00"))
                    out_dt = datetime.fromisoformat(now.replace("Z", "+00:00"))
                    duration_minutes = max(0, int((out_dt - checked_in_dt).total_seconds() // 60))
                except Exception:
                    duration_minutes = None

        updates: dict = {
            "checked_out_at": now,
            "duration_minutes": duration_minutes,
            "notes": body.notes,
            "sync_status": "synced",
        }
        if body.checkout_lat is not None:
            updates["checkout_lat"] = body.checkout_lat
        if body.checkout_lng is not None:
            updates["checkout_lng"] = body.checkout_lng

        res = (
            sb.table("customer_visits")
            .update(updates)
            .eq("id", body.visit_id)
            .execute()
        )
        if not res.data:
            raise HTTPException(status_code=404, detail="Visit not found or not updated")
        return res.data[0]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Checkout failed: {exc}") from exc


@router.get("/today")
async def get_today_visits(current_user: dict = Depends(get_current_user)):
    """Field officer: get today's visits (IST day boundaries)."""
    sb = get_supabase()
    try:
        start_utc, end_utc = _ist_day_bounds()
        res = (
            sb.table("customer_visits")
            .select("*, customers(name, village, taluka, district)")
            .eq("user_id", current_user["user_id"])
            .gte("checked_in_at", start_utc)
            .lt("checked_in_at", end_utc)
            .order("checked_in_at", desc=True)
            .execute()
        )
        return res.data or []
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch today's visits: {exc}") from exc


@router.get("/history")
async def get_visit_history(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    """Field officer: paginated visit history."""
    sb = get_supabase()
    try:
        offset = (page - 1) * limit
        res = (
            sb.table("customer_visits")
            .select("*, customers(name, village, taluka, district)")
            .eq("user_id", current_user["user_id"])
            .order("checked_in_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        return {"page": page, "limit": limit, "data": res.data or []}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch visit history: {exc}") from exc


@router.get("/officer/{user_id}")
async def get_officer_visits(
    user_id: str,
    date: Optional[str] = Query(None, description="YYYY-MM-DD filter in IST"),
    current_user: dict = Depends(get_current_user),
):
    """Caller/admin: get all visits for a specific field officer."""
    sb = get_supabase()
    try:
        query = (
            sb.table("customer_visits")
            .select("*, customers(name, village, taluka, district)")
            .eq("user_id", user_id)
        )
        if date:
            start_utc, end_utc = _ist_day_bounds(date)
            query = query.gte("checked_in_at", start_utc).lt("checked_in_at", end_utc)
        res = query.order("checked_in_at", desc=True).execute()
        return res.data or []
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch officer visits: {exc}") from exc


@router.get("/summary")
async def get_visit_summary(
    date: Optional[str] = Query(None, description="YYYY-MM-DD in IST; defaults to today"),
    current_user: dict = Depends(get_current_user),
):
    """Caller: returns visit stats for their assigned team for a given day."""
    sb = get_supabase()
    try:
        start_utc, end_utc = _ist_day_bounds(date)

        # Get team members (FOs assigned to this caller)
        team_res = (
            sb.table("profiles")
            .select("id, full_name")
            .eq("caller_id", current_user["user_id"])
            .execute()
        )
        team = team_res.data or []
        team_ids = [m["id"] for m in team]

        # Also get emails from auth for display
        email_map = {}
        try:
            auth_users = sb.auth.admin.list_users()
            user_list = auth_users.users if hasattr(auth_users, "users") else (auth_users if isinstance(auth_users, list) else [])
            email_map = {str(u.id): getattr(u, "email", "") for u in user_list}
        except Exception:
            pass

        if not team_ids:
            return {"total_meetings": 0, "total_minutes": 0, "officers": []}

        # Get visits for all team members in date range
        visits_res = (
            sb.table("customer_visits")
            .select("user_id, duration_minutes, checked_out_at")
            .in_("user_id", team_ids)
            .gte("checked_in_at", start_utc)
            .lt("checked_in_at", end_utc)
            .execute()
        )
        visits = visits_res.data or []

        # Aggregate per officer
        team_map = {m["id"]: m["full_name"] for m in team}
        stats: dict = {uid: {"meetings": 0, "minutes": 0} for uid in team_ids}
        for v in visits:
            uid = v.get("user_id")
            if uid in stats:
                # Count only completed visits (checked out)
                if v.get("checked_out_at"):
                    stats[uid]["meetings"] += 1
                    stats[uid]["minutes"] += int(v.get("duration_minutes") or 0)

        officers = [
            {
                "user_id": uid,
                "name": team_map.get(uid, uid),
                "email": email_map.get(uid, ""),
                "meetings_today": s["meetings"],
                "minutes_today": s["minutes"],
            }
            for uid, s in stats.items()
        ]

        total_meetings = sum(o["meetings_today"] for o in officers)
        total_minutes = sum(o["minutes_today"] for o in officers)

        return {"total_meetings": total_meetings, "total_minutes": total_minutes, "officers": officers}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch summary: {exc}") from exc


@router.get("/admin/timeline")
async def get_admin_visit_timeline(
    date: Optional[str] = Query(None, description="YYYY-MM-DD in IST; defaults to today"),
    current_user: dict = Depends(get_current_user),
):
    """Admin: all officers' visits for a given day, grouped by officer."""
    sb = get_supabase()
    try:
        start_utc, end_utc = _ist_day_bounds(date)

        visits_res = (
            sb.table("customer_visits")
            .select("*, customers(name, village, taluka, district)")
            .gte("checked_in_at", start_utc)
            .lt("checked_in_at", end_utc)
            .order("checked_in_at", desc=False)
            .execute()
        )
        visits = visits_res.data or []

        # Get user display names
        users_map = {}
        try:
            auth_users = sb.auth.admin.list_users()
            user_list = auth_users.users if hasattr(auth_users, "users") else (auth_users if isinstance(auth_users, list) else [])
            for u in user_list:
                meta = getattr(u, "user_metadata", {}) or {}
                email = getattr(u, "email", "") or ""
                name = meta.get("full_name") or meta.get("name") or email or str(u.id)[:8]
                users_map[str(u.id)] = {"name": name, "email": email}
        except Exception:
            pass

        # Group by officer
        grouped: dict = {}
        for v in visits:
            uid = v.get("user_id")
            if uid not in grouped:
                user_info = users_map.get(uid, {"name": f"Officer {uid[:6]}", "email": ""})
                grouped[uid] = {
                    "user_id": uid,
                    "name": user_info["name"],
                    "email": user_info["email"],
                    "total_meetings": 0,
                    "total_minutes": 0,
                    "visits": [],
                }
            entry = grouped[uid]
            if v.get("checked_out_at"):
                entry["total_meetings"] += 1
                entry["total_minutes"] += int(v.get("duration_minutes") or 0)
            entry["visits"].append(v)

        return list(grouped.values())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch admin timeline: {exc}") from exc

