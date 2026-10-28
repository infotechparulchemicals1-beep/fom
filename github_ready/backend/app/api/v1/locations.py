from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from app.auth.dependencies import get_current_user
from app.db.supabase_client import get_supabase
from app.models.schemas import BatchLocationRequest

router = APIRouter(prefix="/sessions", tags=["locations"])


@router.post("/{session_id}/locations/batch", status_code=status.HTTP_201_CREATED)
async def batch_upload_locations(
    session_id: UUID,
    body: BatchLocationRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Batch-upload location points for a session.
    Idempotent: uses ON CONFLICT DO NOTHING on the point's UUID.
    """
    user_id = current_user["user_id"]
    sb = get_supabase()

    # Verify session ownership
    session = (
        sb.table("tracking_sessions")
        .select("id")
        .eq("id", str(session_id))
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    if not session.data:
        raise HTTPException(status_code=404, detail="Session not found")

    if not body.points:
        return {"inserted": 0}

    now_iso = datetime.now(timezone.utc).isoformat()
    rows = [
        {
            "id": str(p.id),
            "session_id": str(session_id),
            "user_id": user_id,
            "latitude": p.latitude,
            "longitude": p.longitude,
            "recorded_at": p.recorded_at.isoformat(),
            "accuracy_m": p.accuracy_m,
            "altitude_m": p.altitude_m,
            "speed_mps": p.speed_mps,
            "synced_at": now_iso,
        }
        for p in body.points
    ]

    # Idempotent: ignore conflicts on primary key
    result = (
        sb.table("location_points")
        .upsert(rows, on_conflict="id", ignore_duplicates=True)
        .execute()
    )

    return {"inserted": len(rows), "session_id": str(session_id)}


@router.get("/{session_id}/locations")
async def get_session_locations(
    session_id: UUID,
    current_user: dict = Depends(get_current_user),
):
    """Retrieve all location points for a session (ownership enforced)."""
    user_id = current_user["user_id"]
    sb = get_supabase()

    # Verify ownership
    session = (
        sb.table("tracking_sessions")
        .select("id")
        .eq("id", str(session_id))
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    if not session.data:
        raise HTTPException(status_code=404, detail="Session not found")

    result = (
        sb.table("location_points")
        .select("*")
        .eq("session_id", str(session_id))
        .eq("user_id", user_id)
        .order("recorded_at", desc=False)
        .execute()
    )
    return result.data
