from datetime import datetime, timezone, date
from uuid import UUID
from typing import Optional
import math
from fastapi import APIRouter, HTTPException, Query, status
from app.db.supabase_client import get_supabase

router = APIRouter(prefix="/admin", tags=["admin"])


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance between two GPS coordinates in km."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _compute_distance_from_points(points: list) -> float:
    """Sum haversine distances across an ordered list of GPS point dicts."""
    total = 0.0
    for i in range(1, len(points)):
        try:
            total += _haversine_km(
                float(points[i - 1]["latitude"]), float(points[i - 1]["longitude"]),
                float(points[i]["latitude"]), float(points[i]["longitude"]),
            )
        except (KeyError, TypeError, ValueError):
            continue
    return round(total, 2)


def _get_user_display_name(user_id: str, users_map: dict) -> str:
    user = users_map.get(user_id)
    if user:
        meta = getattr(user, "user_metadata", {}) or {}
        email = getattr(user, "email", "") or ""
        # Prefer explicit full name, then email (full), then short ID fallback
        return meta.get("full_name") or meta.get("name") or email or f"Officer {user_id[:6]}"
    return f"Officer {user_id[:6]}"


def _get_user_email(user_id: str, users_map: dict) -> str:
    user = users_map.get(user_id)
    if user:
        return getattr(user, "email", "") or ""
    return ""


@router.get("/overview")
async def get_admin_overview():
    """
    Overview statistics for team leads and admins.
    Uses IST (UTC+5:30) for day boundaries since this is an India-based field app.
    """
    from datetime import timedelta
    sb = get_supabase()

    # Compute today's start and end in IST, converted to UTC for DB comparison
    IST = timedelta(hours=5, minutes=30)
    now_utc = datetime.now(timezone.utc)
    now_ist = now_utc + IST
    today_ist_midnight = now_ist.replace(hour=0, minute=0, second=0, microsecond=0)
    today_start_utc = (today_ist_midnight - IST).isoformat()
    tomorrow_start_utc = (today_ist_midnight + timedelta(days=1) - IST).isoformat()

    # Query all sessions
    all_sessions_res = sb.table("tracking_sessions").select("user_id, status, total_distance_km, started_at").execute()
    all_sessions = all_sessions_res.data or []

    # Filter for today using IST-aligned UTC boundaries
    today_sessions = [
        s for s in all_sessions
        if today_start_utc <= (s.get("started_at") or "") < tomorrow_start_utc
    ]

    all_officer_ids = set(s.get("user_id") for s in all_sessions if s.get("user_id"))
    active_officers_today = set(
        s.get("user_id") for s in all_sessions if s.get("status") == "active"
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
        "report_date": now_ist.date().isoformat(),
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
        # supabase-py v1 returns object with .users; v2 returns a plain list
        if hasattr(auth_users, "users"):
            user_list = auth_users.users
        elif isinstance(auth_users, list):
            user_list = auth_users
        else:
            user_list = []
        users_map = {str(u.id): u for u in user_list}
        print(f"[Admin API] Loaded {len(users_map)} users from auth")
    except Exception as e:
        print("[Admin API] auth.admin.list_users() failed:", e)

    # 2. Fetch all sessions
    sessions_res = (
        sb.table("tracking_sessions")
        .select("*")
        .order("started_at", desc=True)
        .execute()
    )
    all_sessions = sessions_res.data or []

    # If users_map is empty, fetch each unique user individually as fallback
    if not users_map:
        unique_uids = list(set(s.get("user_id") for s in all_sessions if s.get("user_id")))
        for uid in unique_uids:
            try:
                u = sb.auth.admin.get_user_by_id(uid)
                # get_user_by_id returns a UserResponse with .user
                user_obj = getattr(u, "user", u)
                if user_obj:
                    users_map[str(uid)] = user_obj
            except Exception:
                pass
        print(f"[Admin API] Fallback: loaded {len(users_map)} users individually")


    # Compute IST-based date boundaries for "today"
    from datetime import timedelta
    IST = timedelta(hours=5, minutes=30)
    now_ist = datetime.now(timezone.utc) + IST
    # If caller passes a date, interpret it as IST date; otherwise use today in IST
    if filter_date:
        target_ist_date = filter_date  # YYYY-MM-DD string in IST
        from datetime import date as date_type
        ist_midnight = datetime.strptime(filter_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        target_start_utc = (ist_midnight - IST).isoformat()
        target_end_utc = (ist_midnight + timedelta(days=1) - IST).isoformat()
    else:
        today_ist_midnight = now_ist.replace(hour=0, minute=0, second=0, microsecond=0)
        target_start_utc = (today_ist_midnight - IST).isoformat()
        target_end_utc = (today_ist_midnight + timedelta(days=1) - IST).isoformat()

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

        # Check if started within today's IST boundaries
        started_at_str = s.get("started_at") or ""
        if target_start_utc <= started_at_str < target_end_utc:
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
    Get all sessions for a specific field officer.
    Distance is computed from actual GPS points (Haversine) so active sessions
    show real distance instead of the stored 0 km.
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

    # Fetch ALL GPS points for this user's sessions in one query
    session_ids = [s["id"] for s in sessions if s.get("id")]
    points_by_session: dict = {sid: [] for sid in session_ids}
    if session_ids:
        pts_res = (
            sb.table("location_points")
            .select("session_id, latitude, longitude, recorded_at")
            .in_("session_id", session_ids)
            .order("recorded_at", desc=False)
            .execute()
        )
        for pt in (pts_res.data or []):
            sid = pt.get("session_id")
            if sid in points_by_session:
                points_by_session[sid].append(pt)

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

        # Use GPS-computed distance; fall back to stored value if no points yet
        pts = points_by_session.get(s.get("id"), [])
        stored_dist = round(float(s.get("total_distance_km") or 0), 2)
        computed_dist = _compute_distance_from_points(pts)
        distance_km = computed_dist if pts else stored_dist

        result.append({
            "id": s.get("id"),
            "session_number": idx,
            "session_label": f"Session {idx}",
            "started_at": started_at,
            "ended_at": ended_at,
            "duration_seconds": duration_s,
            "total_distance_km": distance_km,
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
    For active sessions the stored total_distance_km is 0 (updated only on finish),
    so we compute real distance from GPS points and return it as computed_distance_km.
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

    # Fetch location points ordered chronologically
    points_res = (
        sb.table("location_points")
        .select("id, latitude, longitude, recorded_at, accuracy_m, speed_mps, altitude_m")
        .eq("session_id", str(session_id))
        .order("recorded_at", desc=False)
        .execute()
    )
    points = points_res.data or []

    stored_distance = round(float(session.get("total_distance_km") or 0), 2)
    # Always compute from GPS points — this is accurate for both active and finished sessions
    computed_distance = _compute_distance_from_points(points)
    # Use computed distance as the authoritative value; fall back to stored only if no points
    best_distance = computed_distance if points else stored_distance

    return {
        "session_id": str(session_id),
        "started_at": session.get("started_at"),
        "ended_at": session.get("ended_at"),
        "total_distance_km": best_distance,
        "stored_distance_km": stored_distance,
        "computed_distance_km": computed_distance,
        "status": session.get("status"),
        "point_count": len(points),
        "points": points,
    }
