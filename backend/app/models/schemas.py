from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


# ── Session Models ────────────────────────────────────────────────────────────

class CreateSessionRequest(BaseModel):
    session_id: UUID          # client-generated UUID (idempotent)
    started_at: datetime


class SessionResponse(BaseModel):
    id: UUID
    user_id: UUID
    started_at: datetime
    ended_at: datetime | None
    total_distance_km: float
    status: str               # active | paused | completed
    created_at: datetime


class FinishSessionRequest(BaseModel):
    ended_at: datetime
    total_distance_km: float


# ── Location Models ───────────────────────────────────────────────────────────

class LocationPoint(BaseModel):
    id: UUID                  # client-generated UUID (idempotent)
    latitude: float
    longitude: float
    recorded_at: datetime
    accuracy_m: float | None = None
    altitude_m: float | None = None
    speed_mps: float | None = None


class BatchLocationRequest(BaseModel):
    points: list[LocationPoint]


class LocationPointResponse(BaseModel):
    id: UUID
    session_id: UUID
    user_id: UUID
    latitude: float
    longitude: float
    recorded_at: datetime
    accuracy_m: float | None
    altitude_m: float | None
    speed_mps: float | None
    synced_at: datetime | None
