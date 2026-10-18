from datetime import datetime, timezone, date
from uuid import UUID
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status
from app.db.supabase_client import get_supabase

router = APIRouter(prefix="/admin", tags=["admin"])


def _get_user_display_name(user_id: str, users_map: dict) -> str:
    user = users_map.get(user_id)
    if user:
        meta = getattr(user, "user_metadata", {}) or {}
        email = getattr(user, "email", "") or ""
        return meta.get("full_name") or meta.get("name") or (email.split("@")[0] if email else f"Officer {user_id[:6]}")
    return f"Officer {user_id[:6]}"


def _get_user_email(user_id: str, users_map: dict) -> str:
    user = users_map.get(user_id)
    if user:
        return getattr(user, "email", "") or ""
    return ""


@router.get("/overview")
async def get_admin_overview():
    """
    Overview statistics for team leads and admins:
    Total officers, active officers today, total km travelled today, total sessions today.
    """
    sb = get_supabase()
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

    # Query all sessions
    all_sessions_res = sb.table("tracking_sessions").select("user_id, status, total_distance_km, started_at").execute()
    all_sessions = all_sessions_res.data or []

    # Filter for today
    today_sessions = [s for s in all_sessions if s.get("started_at", "") >= today_start]

    all_officer_ids = set(s.get("user_id") for s in all_sessions if s.get("user_id"))
    active_officers_today = set(
        s.get("user_id") for s in today_sessions if s.get("status") == "active"
    )

    total_km_today = sum(float(s.get("total_distance_km") or 0) for s in today_sessions)
    total_km_all_time = sum(float(s.get("total_distance_km") or 0) for s in all_sessions)

    return {
        "total_officers": len(all_officer_ids),
        "active_officers_today": len(active_officers_today),
        "total_distance_km_today": round(total_km_today, 2),
        "total_distance_km_all_time": round(total_km_all_time, 2),
        "total_sessions_today": len(today_sessions),
        "total_sessions_all_time": len(all_sessions),
        "report_date": datetime.now(timezone.utc).date().isoformat(),
    }


@router.get("/officers")
async def list_officers(filter_date: Optional[str] = Query(None, description="YYYY-MM-DD filter")):
    """
    List all field officers with their daily distance, status, session count, and last known location.
    """
    sb = get_supabase()

    # 1. Fetch user accounts map from Supabase Auth admin
    users_map = {}
    try:
        auth_users = sb.auth.admin.list_users()
        if hasattr(auth_users, "users"):
            users_map = {str(u.id): u for u in auth_users.users}
    except Exception as e:
        print("[Admin API] Note: auth.admin.list_users() not available:", e)

    # 2. Fetch all sessions
    sessions_res = (
        sb.table("tracking_sessions")
        .select("*")
        .order("started_at", desc=True)
        .execute()
    )
    all_sessions = sessions_res.data or []

    target_date_str = filter_date or datetime.now(timezone.utc).date().isoformat()

    # Group sessions by officer (user_id)
    officers_dict = {}
    for s in all_sessions:
        uid = str(s.get("user_id"))
        if not uid:
            continue
        if uid not in officers_dict:
            officers_dict[uid] = {
                "user_id": uid,
                "name": _get_user_display_name(uid, users_map),
                "email": _get_user_email(uid, users_map),
                "status": "idle",
                "today_distance_km": 0.0,
                "total_distance_km": 0.0,
                "sessions_count_today": 0,
                "total_sessions_count": 0,
                "last_active_at": None,
                "latest_session_id": None,
            }

        rec = officers_dict[uid]
        dist = float(s.get("total_distance_km") or 0)
        rec["total_distance_km"] += dist
        rec["total_sessions_count"] += 1

        # Check if started on target date
        started_at_str = s.get("started_at") or ""
        if started_at_str.startswith(target_date_str):
            rec["today_distance_km"] += dist
            rec["sessions_count_today"] += 1
            if s.get("status") == "active":
                rec["status"] = "active"

        # Update last active timestamp
        if not rec["last_active_at"] or (started_at_str > rec["last_active_at"]):
            rec["last_active_at"] = started_at_str
            rec["latest_session_id"] = s.get("id")

    # Round distance values
    officers_list = list(officers_dict.values())
    for off in officers_list:
        off["today_distance_km"] = round(off["today_distance_km"], 2)
        off["total_distance_km"] = round(off["total_distance_km"], 2)

    # 3. Fetch latest location point for each officer
    for off in officers_list:
        if off["latest_session_id"]:
            pt_res = (
                sb.table("location_points")
                .select("latitude, longitude, recorded_at, accuracy_m, speed_mps")
                .eq("session_id", off["latest_session_id"])
                .order("recorded_at", desc=True)
                .limit(1)
                .execute()
            )
            if pt_res.data and len(pt_res.data) > 0:
                off["last_location"] = pt_res.data[0]
            else:
                off["last_location"] = None
        else:
            off["last_location"] = None

    # Sort: active first, then highest distance today
    officers_list.sort(key=lambda o: (1 if o["status"] == "active" else 0, o["today_distance_km"]), reverse=True)
    return officers_list


@router.get("/officers/{user_id}/sessions")
async def get_officer_sessions(user_id: UUID):
    """
    Get all sessions for a specific field officer (Session 1, Session 2, etc.)
    with start time, end time, duration, and distance.
    """
    sb = get_supabase()

    sessions_res = (
        sb.table("tracking_sessions")
        .select("*")
        .eq("user_id", str(user_id))
        .order("started_at", desc=False)
        .execute()
    )
    sessions = sessions_res.data or []

    # Number the sessions in chronological order: Session 1, Session 2...
    result = []
    for idx, s in enumerate(sessions, 1):
        started_at = s.get("started_at")
        ended_at = s.get("ended_at")
        duration_s = None
        if started_at:
            try:
                start_dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                end_dt = datetime.fromisoformat(ended_at.replace("Z", "+00:00")) if ended_at else datetime.now(timezone.utc)
                duration_s = max(0, int((end_dt - start_dt).total_seconds()))
            except Exception:
                duration_s = None

        result.append({
            "id": s.get("id"),
            "session_number": idx,
            "session_label": f"Session {idx}",
            "started_at": started_at,
            "ended_at": ended_at,
            "duration_seconds": duration_s,
            "total_distance_km": round(float(s.get("total_distance_km") or 0), 2),
            "status": s.get("status"),
        })

    # Return reverse chronological (newest session first)
    result.reverse()
    return result


@router.get("/sessions/{session_id}/route")
async def get_session_route(session_id: UUID):
    """
    Retrieve full GPS route coordinates and metrics for an individual session
    to render on the admin interactive map.
    """
    sb = get_supabase()

    # Verify session details
    session_res = (
        sb.table("tracking_sessions")
        .select("*")
        .eq("id", str(session_id))
        .single()
        .execute()
    )
    if not session_res.data:
        raise HTTPException(status_code=404, detail="Session not found")

    session = session_res.data

    # Fetch location points
    points_res = (
        sb.table("location_points")
        .select("id, latitude, longitude, recorded_at, accuracy_m, speed_mps, altitude_m")
        .eq("session_id", str(session_id))
        .order("recorded_at", desc=False)
        .execute()
    )
    points = points_res.data or []

    return {
        "session_id": str(session_id),
        "started_at": session.get("started_at"),
        "ended_at": session.get("ended_at"),
        "total_distance_km": round(float(session.get("total_distance_km") or 0), 2),
        "status": session.get("status"),
        "point_count": len(points),
        "points": points,
    }
