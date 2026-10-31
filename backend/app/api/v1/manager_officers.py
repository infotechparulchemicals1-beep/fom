"""
Manager Field Officers API
Phase 4: Manager Bridge APIs

Provides field officer management and target setting.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime
from app.api.v1.manager_auth import get_current_manager
from app.db.supabase_client import get_supabase

router = APIRouter(prefix="/manager/officers", tags=["Manager Officers"])


class FieldOfficerDetail(BaseModel):
    email: str
    name: str
    phone: Optional[str]
    territory: Optional[str]
    status: str
    assigned_date: Optional[str]
    current_month_stats: dict


class AssignOfficersRequest(BaseModel):
    manager_email: EmailStr
    officer_emails: List[EmailStr]


class SetTargetRequest(BaseModel):
    user_email: EmailStr
    month_year: str  # YYYY-MM
    target_amount: float
    target_liters: float
    target_visits: int
    set_by_manager_email: EmailStr


class SetTargetResponse(BaseModel):
    success: bool
    target_id: str
    notification_sent: bool


class TargetAchievementResponse(BaseModel):
    target: dict
    achievement: dict


@router.get("/list", response_model=List[FieldOfficerDetail])
async def list_field_officers(
    status: str = Query("active", description="active, inactive, or all"),
    manager: dict = Depends(get_current_manager)
):
    """
    List all field officers assigned to manager
    
    **Query Parameters:**
    - status: Filter by status (active, inactive, all)
    
    **Returns:**
    - Officer details
    - Current month performance stats
    - Territory assignment
    
    **Future Enhancement:**
    - Filter by manager's assigned officers from manager_officer_assignments table
    - For now, returns all active field officers (simplified)
    """
    
    try:
        supabase = get_supabase()
        
        # Build query
        query = supabase.table("users")\
            .select("*")\
            .eq("role", "field_officer")
        
        if status != "all":
            is_active = (status == "active")
            query = query.eq("is_active", is_active)
        
        officers_response = query.execute()
        officers = officers_response.data
        
        # Get current month stats for each officer
        current_month = datetime.now().strftime("%Y-%m")
        month_start = f"{current_month}-01"
        
        year, month = map(int, current_month.split("-"))
        if month == 12:
            next_month = f"{year+1}-01-01"
        else:
            next_month = f"{year}-{month+1:02d}-01"
        
        officer_details = []
        for officer in officers:
            # Get visits count
            visits_response = supabase.table("customer_visits")\
                .select("id", count="exact")\
                .gte("checked_in_at", f"{month_start}T00:00:00")\
                .lt("checked_in_at", f"{next_month}T00:00:00")\
                .execute()
            
            visits_count = visits_response.count or 0
            
            # Get orders
            orders_response = supabase.table("fo_sales_orders")\
                .select("net_amount")\
                .eq("user_id", officer["id"])\
                .gte("order_date", month_start)\
                .lt("order_date", next_month)\
                .execute()
            
            orders_count = len(orders_response.data)
            sales_amount = sum(o["net_amount"] for o in orders_response.data if o.get("net_amount"))
            
            # Get target
            target_response = supabase.table("fo_monthly_targets")\
                .select("target_amount")\
                .eq("user_id", officer["id"])\
                .eq("month_year", current_month)\
                .execute()
            
            target_amount = target_response.data[0]["target_amount"] if target_response.data else 0
            achievement_percent = (sales_amount / target_amount * 100) if target_amount > 0 else 0
            
            officer_details.append(FieldOfficerDetail(
                email=officer["email"],
                name=officer.get("name", ""),
                phone=officer.get("phone"),
                territory=officer.get("territory"),
                status="active" if officer.get("is_active") else "inactive",
                assigned_date=officer.get("created_at"),
                current_month_stats={
                    "visits": visits_count,
                    "orders": orders_count,
                    "sales_amount": round(sales_amount, 2),
                    "target_amount": target_amount,
                    "achievement_percent": round(achievement_percent, 1)
                }
            ))
        
        return officer_details
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"List officers error: {str(e)}")


@router.post("/assign")
async def assign_officers(
    request: AssignOfficersRequest,
    manager: dict = Depends(get_current_manager)
):
    """
    Assign field officers to manager
    
    **Request Body:**
    - manager_email: Manager's email
    - officer_emails: List of FO emails to assign
    
    **Future Enhancement:**
    - Create entries in manager_officer_assignments table
    - For now, returns success (simplified)
    
    **Returns:**
    - Success status
    - Assigned count
    """
    
    try:
        # Validate all officers exist
        supabase = get_supabase()
        
        officers_response = supabase.table("users")\
            .select("email")\
            .eq("role", "field_officer")\
            .in_("email", request.officer_emails)\
            .execute()
        
        found_emails = [o["email"] for o in officers_response.data]
        missing_emails = set(request.officer_emails) - set(found_emails)
        
        if missing_emails:
            return {
                "success": False,
                "assigned_count": 0,
                "message": f"Officers not found: {', '.join(missing_emails)}"
            }
        
        # TODO: Insert into manager_officer_assignments table
        # For now, just return success
        
        return {
            "success": True,
            "assigned_count": len(request.officer_emails),
            "message": f"{len(request.officer_emails)} officers assigned successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Assign officers error: {str(e)}")


@router.post("/targets/set", response_model=SetTargetResponse)
async def set_monthly_target(
    request: SetTargetRequest,
    manager: dict = Depends(get_current_manager)
):
    """
    Set monthly targets for field officer
    
    **Request Body:**
    - user_email: Field officer's email
    - month_year: Month (YYYY-MM)
    - target_amount: Sales target in rupees
    - target_liters: Volume target in liters
    - target_visits: Visit count target
    - set_by_manager_email: Manager's email
    
    **Side Effects:**
    - Creates/updates fo_monthly_targets record
    - Sends notification to field officer
    - Syncs to mobile during next sync cycle
    
    **Returns:**
    - Success status
    - Target ID
    - Notification sent confirmation
    """
    
    try:
        supabase = get_supabase()
        
        # Get user ID from email
        user_response = supabase.table("users")\
            .select("id, name")\
            .eq("email", request.user_email)\
            .execute()
        
        if not user_response.data:
            raise HTTPException(status_code=404, detail="Field officer not found")
        
        user = user_response.data[0]
        
        # Check if target already exists
        existing_target = supabase.table("fo_monthly_targets")\
            .select("id")\
            .eq("user_id", user["id"])\
            .eq("month_year", request.month_year)\
            .execute()
        
        now = datetime.utcnow().isoformat()
        
        if existing_target.data:
            # Update existing target
            target_id = existing_target.data[0]["id"]
            
            supabase.table("fo_monthly_targets")\
                .update({
                    "target_amount": request.target_amount,
                    "target_liters": request.target_liters,
                    "target_visits": request.target_visits,
                    "set_by_manager_email": request.set_by_manager_email,
                    "updated_at": now,
                    "sync_status": "pending"
                })\
                .eq("id", target_id)\
                .execute()
        else:
            # Create new target
            target_id = f"target-{datetime.utcnow().timestamp()}"
            
            supabase.table("fo_monthly_targets")\
                .insert({
                    "id": target_id,
                    "user_id": user["id"],
                    "month_year": request.month_year,
                    "target_amount": request.target_amount,
                    "target_liters": request.target_liters,
                    "target_visits": request.target_visits,
                    "set_by_manager_email": request.set_by_manager_email,
                    "created_at": now,
                    "updated_at": now,
                    "sync_status": "pending"
                })\
                .execute()
        
        # Create notification
        notification_data = {
            "id": f"notif-{datetime.utcnow().timestamp()}",
            "recipient_user_id": user["id"],
            "title": "Monthly Target Updated",
            "body": f"Your target for {request.month_year} has been set: ₹{request.target_amount:,.0f} sales, {request.target_visits} visits",
            "type": "target_updated",
            "metadata": f'{{"target_id": "{target_id}", "month_year": "{request.month_year}"}}',
            "is_read": 0,
            "created_at": now
        }
        
        supabase.table("fo_notifications")\
            .insert(notification_data)\
            .execute()
        
        notification_sent = True
        
        return SetTargetResponse(
            success=True,
            target_id=target_id,
            notification_sent=notification_sent
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Set target error: {str(e)}")


@router.get("/targets/{user_email}/{month_year}", response_model=TargetAchievementResponse)
async def get_target_and_achievement(
    user_email: str,
    month_year: str,
    manager: dict = Depends(get_current_manager)
):
    """
    Get target and achievement for specific month
    
    **Path Parameters:**
    - user_email: Field officer's email
    - month_year: Month (YYYY-MM)
    
    **Returns:**
    - Target details
    - Achievement metrics
    - Shortfall calculation
    - Achievement percentage
    """
    
    try:
        supabase = get_supabase()
        
        # Get user ID
        user_response = supabase.table("users")\
            .select("id")\
            .eq("email", user_email)\
            .execute()
        
        if not user_response.data:
            raise HTTPException(status_code=404, detail="Field officer not found")
        
        user_id = user_response.data[0]["id"]
        
        # Get target
        target_response = supabase.table("fo_monthly_targets")\
            .select("*")\
            .eq("user_id", user_id)\
            .eq("month_year", month_year)\
            .execute()
        
        if not target_response.data:
            raise HTTPException(status_code=404, detail="Target not found for this month")
        
        target = target_response.data[0]
        
        # Get date range
        month_start = f"{month_year}-01"
        year, month = map(int, month_year.split("-"))
        if month == 12:
            next_month = f"{year+1}-01-01"
        else:
            next_month = f"{year}-{month+1:02d}-01"
        
        # Get achievements
        # Orders
        orders_response = supabase.table("fo_sales_orders")\
            .select("net_amount, total_liters")\
            .eq("user_id", user_id)\
            .gte("order_date", month_start)\
            .lt("order_date", next_month)\
            .execute()
        
        actual_amount = sum(o.get("net_amount", 0) for o in orders_response.data)
        actual_liters = sum(o.get("total_liters", 0) for o in orders_response.data)
        
        # Visits
        visits_response = supabase.table("customer_visits")\
            .select("id", count="exact")\
            .gte("checked_in_at", f"{month_start}T00:00:00")\
            .lt("checked_in_at", f"{next_month}T00:00:00")\
            .execute()
        
        actual_visits = visits_response.count or 0
        
        # Calculate shortfall
        shortfall_amount = target["target_amount"] - actual_amount
        shortfall_percent = (shortfall_amount / target["target_amount"] * 100) if target["target_amount"] > 0 else 0
        achievement_percent = (actual_amount / target["target_amount"] * 100) if target["target_amount"] > 0 else 0
        
        return TargetAchievementResponse(
            target={
                "month_year": target["month_year"],
                "target_amount": target["target_amount"],
                "target_liters": target["target_liters"],
                "target_visits": target["target_visits"],
                "set_by_manager_email": target.get("set_by_manager_email"),
                "set_at": target["created_at"]
            },
            achievement={
                "actual_amount": round(actual_amount, 2),
                "actual_liters": round(actual_liters, 1),
                "actual_visits": actual_visits,
                "shortfall_amount": round(shortfall_amount, 2),
                "shortfall_percent": round(abs(shortfall_percent), 1),
                "achievement_percent": round(achievement_percent, 1)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Target achievement error: {str(e)}")

