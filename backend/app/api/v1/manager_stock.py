"""
Manager Stock & Sample Requisitions API
Matches AURA Field Manager Console & Admin Portal Specification.

Endpoints:
- GET  /api/v1/manager/stock-requests
- GET  /api/v1/manager/stock-requests/{request_id}
- PATCH /api/v1/manager/stock-requests/{request_id}
"""

from fastapi import APIRouter, HTTPException, Header, Query, Path
from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from datetime import datetime, timezone
from app.db.supabase_client import get_supabase

router = APIRouter(prefix="/manager/stock-requests", tags=["Manager Stock Requests"])


class StockRequestItem(BaseModel):
    product_id: Optional[str] = None
    product_name: Optional[str] = None
    qty_requested: Optional[int] = None
    qty_approved: Optional[int] = None
    quantity: Optional[int] = None


class UpdateStockRequestPayload(BaseModel):
    status: str = Field(..., description="Target status: approved, fulfilled, dispatched, rejected")
    approved_qty: Optional[int] = Field(None, description="Approved unit count")
    manager_notes: Optional[str] = Field(None, description="Manager review remarks or rejection reason")
    approved_by: Optional[str] = Field(None, description="Manager email address")


class UpdateStockResponse(BaseModel):
    success: bool
    request_id: str
    status: str
    approved_qty: Optional[int] = None
    approved_at: Optional[str] = None


@router.get("", response_model=List[Dict[str, Any]])
async def list_stock_requests(
    status: Optional[str] = Query(None, description="Filter by status: pending, approved, fulfilled, dispatched, rejected"),
    field_officer_email: Optional[str] = Query(None, description="Filter by officer email"),
    limit: int = Query(50, ge=1, le=200),
    authorization: Optional[str] = Header(None),
    x_aura_api_key: Optional[str] = Header(None, alias="X-Aura-Api-Key"),
):
    """
    Fetch list of field officer stock requisitions for Field Manager console.
    """
    supabase = get_supabase()
    query = supabase.table("fo_stock_requests").select("*").order("created_at", desc=True).limit(limit)

    if status:
        query = query.eq("status", status.lower())
    if field_officer_email:
        query = query.eq("field_officer_email", field_officer_email)

    result = query.execute()
    return result.data or []


@router.get("/{request_id}", response_model=Dict[str, Any])
async def get_stock_request(
    request_id: str = Path(..., description="Stock request UUID"),
    authorization: Optional[str] = Header(None),
    x_aura_api_key: Optional[str] = Header(None, alias="X-Aura-Api-Key"),
):
    """
    Get a single stock request record by UUID.
    """
    supabase = get_supabase()
    result = supabase.table("fo_stock_requests").select("*").eq("id", request_id).limit(1).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Stock request record not found")
    return result.data[0]


@router.patch("/{request_id}", response_model=UpdateStockResponse)
async def update_stock_request(
    request_id: str = Path(..., description="Stock request UUID in fo_stock_requests"),
    payload: UpdateStockRequestPayload = ...,
    authorization: Optional[str] = Header(None),
    x_aura_api_key: Optional[str] = Header(None, alias="X-Aura-Api-Key"),
):
    """
    Approve, modify quantity, reject, or dispatch a stock requisition.
    Updates fo_stock_requests in Supabase and triggers status reflection in AURA Mobile.
    """
    supabase = get_supabase()

    # 1. Fetch existing record
    existing = supabase.table("fo_stock_requests").select("*").eq("id", request_id).limit(1).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Stock request record not found")

    current = existing.data[0]
    now_iso = datetime.now(timezone.utc).isoformat()
    new_status = payload.status.lower().strip()

    valid_statuses = {"pending", "approved", "fulfilled", "dispatched", "rejected"}
    if new_status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{payload.status}'. Allowed: {', '.join(valid_statuses)}"
        )

    # 2. Build updates dictionary
    updates: Dict[str, Any] = {
        "status": new_status,
        "updated_at": now_iso,
    }

    approved_at_val: Optional[str] = None
    if new_status in ("approved", "dispatched", "fulfilled"):
        approved_at_val = now_iso
        updates["approved_at"] = approved_at_val

    if payload.approved_by:
        updates["approved_by"] = payload.approved_by

    # Update notes / manager_notes
    if payload.manager_notes:
        existing_notes = current.get("notes") or ""
        if existing_notes and payload.manager_notes not in existing_notes:
            updates["notes"] = f"{existing_notes} | {payload.manager_notes}".strip(" |")
        else:
            updates["notes"] = payload.manager_notes

    # Update requested_items array with approved quantity
    final_approved_qty = payload.approved_qty
    raw_items = current.get("requested_items")
    if isinstance(raw_items, list) and len(raw_items) > 0:
        items = list(raw_items)
        if final_approved_qty is not None:
            items[0]["qty_approved"] = final_approved_qty
            items[0]["approved_qty"] = final_approved_qty
        elif new_status == "approved" and "qty_approved" not in items[0]:
            # Default approved quantity to requested quantity if full approval
            fallback_qty = items[0].get("qty_requested") or items[0].get("quantity") or 0
            items[0]["qty_approved"] = fallback_qty
            items[0]["approved_qty"] = fallback_qty
            final_approved_qty = fallback_qty
        updates["requested_items"] = items

    # 3. Commit update to Supabase
    res = supabase.table("fo_stock_requests").update(updates).eq("id", request_id).execute()
    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to update stock request in database")

    # 4. Return exact response format specified in Admin Console API doc
    return UpdateStockResponse(
        success=True,
        request_id=request_id,
        status=new_status,
        approved_qty=final_approved_qty,
        approved_at=approved_at_val,
    )
