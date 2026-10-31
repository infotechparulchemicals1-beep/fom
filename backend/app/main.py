from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.v1 import (
    sessions, locations, admin, auth, profiles, customers, visits,
    manager_auth, manager_dashboard, manager_plans, manager_analytics,
    manager_verification, manager_officers
)

app = FastAPI(
    title="AURA Field Officer & Manager API",
    description="Backend for AURA Mobile v2.0 with Manager Bridge APIs",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount field officer routers (existing)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(sessions.router, prefix="/api/v1")
app.include_router(locations.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(profiles.router, prefix="/api/v1")
app.include_router(customers.router, prefix="/api/v1")
app.include_router(visits.router, prefix="/api/v1")

# Mount manager routers (Phase 4)
app.include_router(manager_auth.router, prefix="/api/v1")
app.include_router(manager_dashboard.router, prefix="/api/v1")
app.include_router(manager_plans.router, prefix="/api/v1")
app.include_router(manager_analytics.router, prefix="/api/v1")
app.include_router(manager_verification.router, prefix="/api/v1")
app.include_router(manager_officers.router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "2.0.0"}


@app.get("/")
async def root():
    return {
        "message": "AURA Field Officer & Manager API v2.0",
        "docs": "/docs",
        "health": "/health"
    }
