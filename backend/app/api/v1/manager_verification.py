"""
Manager Verification API
Phase 4: Manager Bridge APIs

Provides visit verification workflow for managers.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.api.v1.manager_auth import get_current_manager
from app.db.supabase_client import get_supabase

router = APIRouter(prefix="/manager/verification", tags=["Manager Verification"])


class PendingVisit(BaseModel):
    visit_id: str
    field_officer: str
    customer_name: str
    customer_contact: Optional[str]
    visit_date: str
    checked_in_at: str
    checked_out_at: Optional[str]
    duration_minutes: Optional[int]
    notes: Optional[str]
    photos_count: int
    verification_status: str
    order_created: bool
    order_amount: Optional[float]


class VerifyVisitRequest(BaseModel):
    visit_id: str
    manager_email: str
    verified: bool
    call_notes: Optional[str] = None
    second_pitch_status: Optional[str] = None


class VerifyVisitResponse(BaseModel):
    success: bool
    visit_id: str
    verification_status: str
    notification_sent: bool


@router.get("/pending", response_model=List[PendingVisit])
async def get_pending_verifications(
    date_from: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    limit: int = Query(50, description="Max results"),
    manager: dict = Depends(get_current_manager)
):
    """
    List visits pending manager verification
    
    **Manager Calling Workflow:**
    1. Manager gets list of pending visits
    2. Manager calls customer to verify visit
    3. Manager marks visit as verified/disputed
    4. Manager adds call notes
    5. Manager optionally records second pitch status
    6. Field officer gets notification
    
    **Query Parameters:**
    - date_from: Filter from date (optional)
    - date_to: Filter to date (optional)
    - limit: Max results (default 50)
    
    **Returns:**
    - Visit details
    - Customer contact info
    - Visit notes and photos count
    - Associated order info
    """
    
    try:
        supabase = get_supabase()
        
        # Build query
        query = supabase.table("customer_visits")\
            .select("*, users!inner(name), customers!inner(name, contact_no)")\
            .eq("verification_status", "pending")\
            .order("checked_in_at", desc=True)\
            .limit(limit)
        
        if date_from:
            query = query.gte("checked_in_at", f"{date_from}T00:00:00")
        
        if date_to:
            query = query.lte("checked_in_at", f"{date_to}T23:59:59")
        
        visits_response = query.execute()
        visits = visits_response.data
        
        # Build response with additional data
        pending_visits = []
        for visit in visits:
            # Check if order was created during visit
            order_response = supabase.table("fo_sales_orders")\
                .select("net_amount")\
                .eq("visit_id", visit["id"])\
                .execute()
            
            order_created = len(order_response.data) > 0
            order_amount = order_response.data[0]["net_amount"] if order_created else None
            
            # Count photos
            photos_count = len(visit.get("photo_uris", "").split(",")) if visit.get("photo_uris") else 0
            
            # Extract date from timestamp
            visit_date = visit["checked_in_at"].split("T")[0]
            
            pending_visits.append(PendingVisit(
                visit_id=visit["id"],
                field_officer=visit["users"]["name"],
                customer_name=visit["customers"]["name"],
                customer_contact=visit["customers"].get("contact_no"),
                visit_date=visit_date,
                checked_in_at=visit["checked_in_at"],
                checked_out_at=visit.get("checked_out_at"),
                duration_minutes=visit.get("duration_minutes"),
                notes=visit.get("notes"),
                photos_count=photos_count,
                verification_status=visit.get("verification_status", "pending"),
                order_created=order_created,
                order_amount=order_amount
            ))
        
        return pending_visits
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pending verifications error: {str(e)}")


@router.post("/verify", response_model=VerifyVisitResponse)
async def verify_visit(
    request: VerifyVisitRequest,
    manager: dict = Depends(get_current_manager)
):
    """
    Manager verifies visit after calling customer
    
    **Workflow:**
    1. Validate visit exists
    2. Update verification status
    3. Save manager call notes
    4. Record second pitch status (if applicable)
    5. Create follow-up task if needed
    6. Send notification to field officer
    
    **Request Body:**
    - visit_id: UUID of visit
    - manager_email: Manager's email
    - verified: True/False
    - call_notes: Manager's notes from call (optional)
    - second_pitch_status: not_pitched, pitched_interested, pitched_follow_up, pitched_converted
    
    **Side Effects:**
    - Updates customer_visits table
    - Creates notification for FO
    - Auto-creates follow-up if status = pitched_interested
    
    **Returns:**
    - Success status
    - Updated verification status
    - Notification sent confirmation
    """
    
    try:
        supabase = get_supabase()
        
        # Verify visit exists
        visit_response = supabase.table("customer_visits")\
            .select("*, users!inner(id, email)")\
            .eq("id", request.visit_id)\
            .execute()
        
        if not visit_response.data:
            raise HTTPException(status_code=404, detail="Visit not found")
        
        visit = visit_response.data[0]
        
        # Prepare update
        update_data = {
            "verification_status": "verified" if request.verified else "disputed",
            "manager_verified_at": datetime.utcnow().isoformat(),
            "manager_verified_by": request.manager_email,
            "manager_call_notes": request.call_notes,
            "second_pitch_status": request.second_pitch_status
        }
        
        # Update visit
        supabase.table("customer_visits")\
            .update(update_data)\
            .eq("id", request.visit_id)\
            .execute()
        
        # Create notification for field officer
        notification_data = {
            "id": f"notif-{datetime.utcnow().timestamp()}",
            "recipient_user_id": visit["users"]["id"],
            "title": "Visit Verified" if request.verified else "Visit Disputed",
            "body": f"Manager {manager['name']} has {'verified' if request.verified else 'disputed'} your visit.",
            "type": "visit_verified" if request.verified else "visit_disputed",
            "metadata": f'{{"visit_id": "{request.visit_id}", "call_notes": "{request.call_notes or ''}"}}',
            "is_read": 0,
            "created_at": datetime.utcnow().isoformat()
        }
        
        supabase.table("fo_notifications")\
            .insert(notification_data)\
            .execute()
        
        notification_sent = True
        
        # Auto-create follow-up if second pitch interested
        if request.second_pitch_status in ["pitched_interested", "pitched_follow_up"]:
            # TODO: Create follow-up task in route plan
            pass
        
        return VerifyVisitResponse(
            success=True,
            visit_id=request.visit_id,
            verification_status="verified" if request.verified else "disputed",
            notification_sent=notification_sent
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Verify visit error: {str(e)}")


@router.get("/visit-details/{visit_id}")
async def get_visit_details(
    visit_id: str,
    manager: dict = Depends(get_current_manager)
):
    """
    Get complete details of a specific visit for verification
    
    **Returns:**
    - Visit details with timestamps
    - Customer information
    - Field officer details
    - GPS coordinates
    - Photos
    - Notes
    - Associated orders
    - Associated receipts
    """
    
    try:
        supabase = get_supabase()
        
        # Get visit with joins
        visit_response = supabase.table("customer_visits")\
            .select("*, users!inner(name, email), customers!inner(*)")\
            .eq("id", visit_id)\
            .execute()
        
        if not visit_response.data:
            raise HTTPException(status_code=404, detail="Visit not found")
        
        visit = visit_response.data[0]
        
        # Get orders created during visit
        orders_response = supabase.table("fo_sales_orders")\
            .select("*")\
            .eq("visit_id", visit_id)\
            .execute()
        
        # Get receipts
        receipts_response = supabase.table("fo_payment_receipts")\
            .select("*")\
            .eq("visit_id", visit_id)\
            .execute()
        
        # Build response
        return {
            "visit": {
                "id": visit["id"],
                "customer": {
                    "name": visit["customers"]["name"],
                    "village": visit["customers"].get("village"),
                    "contact_no": visit["customers"].get("contact_no")
                },
                "field_officer": {
                    "name": visit["users"]["name"],
                    "email": visit["users"]["email"]
                },
                "checked_in_at": visit["checked_in_at"],
                "checked_out_at": visit.get("checked_out_at"),
                "duration_minutes": visit.get("duration_minutes"),
                "checkin_location": {
                    "lat": visit.get("checkin_lat"),
                    "lng": visit.get("checkin_lng")
                },
                "checkout_location": {
                    "lat": visit.get("checkout_lat"),
                    "lng": visit.get("checkout_lng")
                },
                "notes": visit.get("notes"),
                "photo_uris": visit.get("photo_uris", "").split(",") if visit.get("photo_uris") else [],
                "verification_status": visit.get("verification_status", "pending"),
                "manager_verified_at": visit.get("manager_verified_at"),
                "manager_verified_by": visit.get("manager_verified_by"),
                "manager_call_notes": visit.get("manager_call_notes"),
                "second_pitch_status": visit.get("second_pitch_status")
            },
            "orders": orders_response.data,
            "receipts": receipts_response.data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Visit details error: {str(e)}")


@router.get("/verification-summary")
async def get_verification_summary(
    month_year: str = Query(..., description="Format: YYYY-MM"),
    manager: dict = Depends(get_current_manager)
):
    """
    Get verification summary for the month
    
    **Returns:**
    - Total visits
    - Verified count
    - Pending count
    - Disputed count
    - Verification rate
    - Average verification time
    """
    
    try:
        supabase = get_supabase()
        
        # Get date range
        month_start = f"{month_year}-01T00:00:00"
        year, month = map(int, month_year.split("-"))
        if month == 12:
            next_month = f"{year+1}-01-01T00:00:00"
        else:
            next_month = f"{year}-{month+1:02d}-01T00:00:00"
        
        # Get all visits for month
        visits_response = supabase.table("customer_visits")\
            .select("*")\
            .gte("checked_in_at", month_start)\
            .lt("checked_in_at", next_month)\
            .execute()
        
        visits = visits_response.data
        
        total_visits = len(visits)
        verified_count = sum(1 for v in visits if v.get("verification_status") == "verified")
        pending_count = sum(1 for v in visits if v.get("verification_status") == "pending")
        disputed_count = sum(1 for v in visits if v.get("verification_status") == "disputed")
        
        verification_rate = (verified_count / total_visits * 100) if total_visits > 0 else 0
        
        # Calculate average verification time
        verified_visits = [v for v in visits if v.get("manager_verified_at") and v.get("checked_out_at")]
        
        total_verification_hours = 0
        for v in verified_visits:
            checked_out = datetime.fromisoformat(v["checked_out_at"].replace("Z", "+00:00"))
            verified_at = datetime.fromisoformat(v["manager_verified_at"].replace("Z", "+00:00"))
            hours = (verified_at - checked_out).total_seconds() / 3600
            total_verification_hours += hours
        
        avg_verification_hours = (total_verification_hours / len(verified_visits)) if verified_visits else 0
        
        return {
            "month_year": month_year,
            "summary": {
                "total_visits": total_visits,
                "verified_count": verified_count,
                "pending_count": pending_count,
                "disputed_count": disputed_count,
                "verification_rate": round(verification_rate, 1),
                "average_verification_hours": round(avg_verification_hours, 1)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Verification summary error: {str(e)}")

