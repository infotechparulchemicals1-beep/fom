"""
Manager Stock Requisition API
Handles reviewing, approving, and rejecting field officer stock requisitions.
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Path
from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime, timezone
from app.db.supabase_client import get_supabase

router = APIRouter(prefix="/manager/stock-requests", tags=["Manager Stock Requests"])


class StockItem(BaseModel):
    product_id: Optional[str] = None
    product_name: Optional[str] = None
    qty_requested: int
    qty_approved: Optional[int] = None


class StockRequestResponse(BaseModel):
    id: str
    request_number: Optional[str] = None
    field_officer_email: str
    request_date: str
    status: str
    requested_items: List[Any] = []
    notes: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    created_at: str
    updated_at: str


class ApproveRejectStockRequest(BaseModel):
    status: str  # "approved", "rejected", "dispatched"
    approved_by: Optional[str] = None
    notes: Optional[str] = None
    qty_approved: Optional[int] = None


@router.get("", response_model=List[StockRequestResponse])
async def list_stock_requests(
    status: Optional[str] = Query(None, description="Filter by status (pending, approved, rejected, dispatched)"),
    field_officer_email: Optional[str] = Query(None, description="Filter by officer email"),
    limit: int = Query(50, ge=1, le=200),
):
    """
    List stock requisitions submitted by field officers.
    """
    supabase = get_supabase()
    query = supabase.table("fo_stock_requests").select("*").order("created_at", desc=True).limit(limit)

    if status:
        query = query.eq("status", status)
    if field_officer_email:
        query = query.eq("field_officer_email", field_officer_email)

    result = query.execute()
    return result.data or []


@router.get("/{id}", response_model=StockRequestResponse)
async def get_stock_request(
    id: str = Path(..., description="Stock request UUID"),
):
    """
    Get a specific stock requisition by ID.
    """
    supabase = get_supabase()
    result = supabase.table("fo_stock_requests").select("*").eq("id", id).limit(1).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Stock request not found")
    return result.data[0]


@router.patch("/{id}", response_model=StockRequestResponse)
async def update_stock_request_status(
    id: str = Path(..., description="Stock request UUID"),
    payload: ApproveRejectStockRequest = ...,
):
    """
    Approve, reject, or dispatch a stock requisition.
    Changes are reflected immediately in the mobile application.
    """
    supabase = get_supabase()

    # Verify exists
    existing = supabase.table("fo_stock_requests").select("*").eq("id", id).limit(1).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Stock request not found")

    current = existing.data[0]
    now_iso = datetime.now(timezone.utc).isoformat()

    updates = {
        "status": payload.status.lower(),
        "updated_at": now_iso,
    }

    if payload.approved_by:
        updates["approved_by"] = payload.approved_by
    if payload.status.lower() in ("approved", "dispatched"):
        updates["approved_at"] = now_iso

    if payload.notes:
        existing_notes = current.get("notes") or ""
        updates["notes"] = f"{existing_notes} | {payload.notes}".strip(" |")

    # If approved quantity provided, update inside requested_items JSON
    if payload.qty_approved is not None:
        items = current.get("requested_items") or []
        if items and isinstance(items, list):
            items[0]["qty_approved"] = payload.qty_approved
            updates["requested_items"] = items

    res = supabase.table("fo_stock_requests").update(updates).eq("id", id).execute()
    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to update stock request")

    return res.data[0]
