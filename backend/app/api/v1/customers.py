from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from app.db.supabase_client import get_supabase
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/customers", tags=["customers"])


class CustomerCreate(BaseModel):
    name: str
    village: Optional[str] = None
    taluka: Optional[str] = None
    district: Optional[str] = None
    pincode: Optional[str] = None
    contact_no: Optional[str] = None


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    village: Optional[str] = None
    taluka: Optional[str] = None
    district: Optional[str] = None
    pincode: Optional[str] = None
    contact_no: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("")
async def list_customers(
    search: Optional[str] = Query(None, description="Search by name or village (case-insensitive)"),
    current_user: dict = Depends(get_current_user),
):
    """List all active customers. Supports fuzzy search on name."""
    sb = get_supabase()
    try:
        query = sb.table("customers").select("*").eq("is_active", True)
        if search:
            # ilike on name — PostgREST supports ilike filter
            query = query.ilike("name", f"%{search}%")
        res = query.order("name").execute()
        return res.data or []
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to list customers: {exc}") from exc


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_customer(body: CustomerCreate, current_user: dict = Depends(get_current_user)):
    """Create a new customer/farmer."""
    sb = get_supabase()
    try:
        payload = body.model_dump(exclude_none=True)
        payload["created_by"] = current_user["user_id"]
        res = sb.table("customers").insert(payload).execute()
        if not res.data:
            raise HTTPException(status_code=500, detail="Insert returned no data")
        return res.data[0]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to create customer: {exc}") from exc


@router.get("/{customer_id}")
async def get_customer(customer_id: str, current_user: dict = Depends(get_current_user)):
    """Get a single customer by ID."""
    sb = get_supabase()
    try:
        res = sb.table("customers").select("*").eq("id", customer_id).single().execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Customer not found")
        return res.data
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to get customer: {exc}") from exc


@router.put("/{customer_id}")
async def update_customer(
    customer_id: str,
    body: CustomerUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Update an existing customer."""
    sb = get_supabase()
    try:
        updates = body.model_dump(exclude_none=True)
        if not updates:
            raise HTTPException(status_code=400, detail="No fields provided for update")
        res = (
            sb.table("customers")
            .update(updates)
            .eq("id", customer_id)
            .execute()
        )
        if not res.data:
            raise HTTPException(status_code=404, detail="Customer not found")
        return res.data[0]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to update customer: {exc}") from exc

