from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from app.auth.dependencies import get_current_user
from app.db.supabase_client import get_supabase
from app.models.schemas import (
    CreateSessionRequest,
    SessionResponse,
    FinishSessionRequest,
)

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_session(
    body: CreateSessionRequest,
    current_user: dict = Depends(get_current_user),
):
    """Create or return an existing tracking session (idempotent by session_id)."""
    user_id = current_user["user_id"]
    sb = get_supabase()

    # Idempotent upsert — if session already exists it won't be duplicated
    result = (
        sb.table("tracking_sessions")
        .upsert(
            {
                "id": str(body.session_id),
                "user_id": user_id,
                "started_at": body.started_at.isoformat(),
                "status": "active",
                "total_distance_km": 0,
            },
            on_conflict="id",
            ignore_duplicates=True,
        )
        .execute()
    )

    # Fetch the record (upsert may not return on ignore)
    fetched = (
        sb.table("tracking_sessions")
        .select("*")
        .eq("id", str(body.session_id))
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    if not fetched.data:
        raise HTTPException(status_code=404, detail="Session not found")

    return fetched.data


@router.get("", response_model=list[SessionResponse])
async def list_sessions(current_user: dict = Depends(get_current_user)):
    """List all sessions for the authenticated user."""
    user_id = current_user["user_id"]
    sb = get_supabase()

    result = (
        sb.table("tracking_sessions")
        .select("*")
        .eq("user_id", user_id)
        .order("started_at", desc=True)
        .execute()
    )
    return result.data


@router.get("/{session_id}")
async def get_session(
    session_id: UUID,
    current_user: dict = Depends(get_current_user),
):
    """Get a single session by ID (ownership enforced)."""
    user_id = current_user["user_id"]
    sb = get_supabase()

    result = (
        sb.table("tracking_sessions")
        .select("*")
        .eq("id", str(session_id))
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Session not found")
    return result.data


@router.post("/{session_id}/finish")
async def finish_session(
    session_id: UUID,
    body: FinishSessionRequest,
    current_user: dict = Depends(get_current_user),
):
    """Mark a session as completed."""
    user_id = current_user["user_id"]
    sb = get_supabase()

    # Verify ownership
    existing = (
        sb.table("tracking_sessions")
        .select("id")
        .eq("id", str(session_id))
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Session not found")

    result = (
        sb.table("tracking_sessions")
        .update(
            {
                "ended_at": body.ended_at.isoformat(),
                "total_distance_km": body.total_distance_km,
                "status": "completed",
            }
        )
        .eq("id", str(session_id))
        .eq("user_id", user_id)
        .execute()
    )
    return result.data[0] if result.data else {"status": "updated"}
