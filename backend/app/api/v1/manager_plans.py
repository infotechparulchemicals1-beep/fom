"""
Manager Plans API
Phase 4: Manager Bridge APIs

Provides plan vs actual comparison and analysis.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.api.v1.manager_auth import get_current_manager
from app.db.supabase_client import get_supabase_client

router = APIRouter(prefix="/manager/plans", tags=["Manager Plans"])


class PlanItemDetail(BaseModel):
    sequence: int
    customer_name: str
    task_type: str
    planned_time: Optional[str]
    status: str
    executed_visit_id: Optional[str]
    actual_time: Optional[str]
    deviation_minutes: Optional[int]


class ActualVisit(BaseModel):
    customer_name: str
    checked_in_at: str
    checked_out_at: Optional[str]
    duration_minutes: Optional[int]
    planned: bool


class EditHistoryItem(BaseModel):
    edited_at: str
    revision_number: int
    edit_reason: str
    changes: dict


class PlanVsActualResponse(BaseModel):
    date: str
    field_officer: dict
    plan: dict
    plan_items: List[PlanItemDetail]
    actual_visits: List[ActualVisit]
    summary: dict
    edit_history: List[EditHistoryItem]


@router.get("/vs-actual", response_model=PlanVsActualResponse)
async def get_plan_vs_actual(
    user_email: str = Query(..., description="Field officer email"),
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    manager: dict = Depends(get_current_manager)
):
    """
    Compare planned route vs actual visits for a specific date
    
    **Provides:**
    - Plan details with submission time
    - Plan items with sequence and status
    - Actual visits with timing
    - Deviation analysis
    - Edit history with reasons
    
    **Query Parameters:**
    - user_email: Field officer's email
    - date: Date to analyze (YYYY-MM-DD)
    
    **Metrics:**
    - Planned count
    - Completed count
    - Skipped count
    - Unplanned count
    - Completion rate
    - Plan adherence rate
    """
    
    try:
        supabase = get_supabase_client()
        
        # Get field officer
        officer_response = supabase.table("users")\
            .select("id, email, name")\
            .eq("email", user_email)\
            .execute()
        
        if not officer_response.data:
            raise HTTPException(status_code=404, detail="Field officer not found")
        
        officer = officer_response.data[0]
        
        # Get route plan for date
        plan_response = supabase.table("daily_route_plans")\
            .select("*")\
            .eq("user_id", officer["id"])\
            .eq("plan_date", date)\
            .execute()
        
        if not plan_response.data:
            raise HTTPException(status_code=404, detail="Route plan not found for this date")
        
        plan = plan_response.data[0]
        
        # Get plan items with customer details
        plan_items_response = supabase.table("route_plan_items")\
            .select("*, customers!inner(name)")\
            .eq("plan_id", plan["id"])\
            .order("sequence_order")\
            .execute()
        
        # Get actual visits for the day
        day_start = f"{date}T00:00:00"
        day_end = f"{date}T23:59:59"
        
        visits_response = supabase.table("customer_visits")\
            .select("*, customers!inner(name)")\
            .gte("checked_in_at", day_start)\
            .lte("checked_in_at", day_end)\
            .execute()
        
        visits = visits_response.data
        
        # Build plan items with actual execution data
        plan_items = []
        for item in plan_items_response.data:
            customer_name = item["customers"]["name"]
            
            # Find matching visit
            matching_visit = next(
                (v for v in visits if v["customer_id"] == item["customer_id"]),
                None
            )
            
            actual_time = None
            deviation_minutes = None
            
            if matching_visit:
                actual_time = matching_visit["checked_in_at"]
                
                # Calculate deviation if planned_time exists
                if item["planned_time"]:
                    try:
                        planned_dt = datetime.fromisoformat(f"{date}T{item['planned_time']}")
                        actual_dt = datetime.fromisoformat(matching_visit["checked_in_at"])
                        deviation_minutes = int((actual_dt - planned_dt).total_seconds() / 60)
                    except:
                        pass
            
            plan_items.append(PlanItemDetail(
                sequence=item["sequence_order"],
                customer_name=customer_name,
                task_type=item["task_type"],
                planned_time=item["planned_time"],
                status=item["status"],
                executed_visit_id=item["executed_visit_id"],
                actual_time=actual_time,
                deviation_minutes=deviation_minutes
            ))
        
        # Build actual visits list
        planned_customer_ids = [item["customer_id"] for item in plan_items_response.data]
        
        actual_visits = []
        for visit in visits:
            customer_name = visit["customers"]["name"]
            is_planned = visit["customer_id"] in planned_customer_ids
            
            actual_visits.append(ActualVisit(
                customer_name=customer_name,
                checked_in_at=visit["checked_in_at"],
                checked_out_at=visit.get("checked_out_at"),
                duration_minutes=visit.get("duration_minutes"),
                planned=is_planned
            ))
        
        # Calculate summary metrics
        planned_count = len(plan_items_response.data)
        completed_count = sum(1 for item in plan_items_response.data if item["status"] == "completed")
        skipped_count = sum(1 for item in plan_items_response.data if item["status"] == "skipped")
        unplanned_count = sum(1 for v in visits if v["customer_id"] not in planned_customer_ids)
        
        completion_rate = (completed_count / planned_count * 100) if planned_count > 0 else 0
        plan_adherence_rate = ((planned_count - unplanned_count) / planned_count * 100) if planned_count > 0 else 0
        
        summary = {
            "planned_count": planned_count,
            "completed_count": completed_count,
            "skipped_count": skipped_count,
            "unplanned_count": unplanned_count,
            "completion_rate": round(completion_rate, 1),
            "plan_adherence_rate": round(plan_adherence_rate, 1)
        }
        
        # Get edit history
        edit_history_response = supabase.table("entity_edit_logs")\
            .select("*")\
            .eq("entity_type", "route_plan")\
            .eq("entity_id", plan["id"])\
            .order("edited_at")\
            .execute()
        
        edit_history = []
        for log in edit_history_response.data:
            try:
                previous_payload = eval(log["previous_payload"]) if log["previous_payload"] else {}
                new_payload = eval(log["new_payload"]) if log["new_payload"] else {}
                
                changes = {
                    "removed": [],  # TODO: Extract from payloads
                    "added": [],
                    "reordered": False
                }
            except:
                changes = {}
            
            edit_history.append(EditHistoryItem(
                edited_at=log["edited_at"],
                revision_number=log["revision_number"],
                edit_reason=log["edit_reason"],
                changes=changes
            ))
        
        return PlanVsActualResponse(
            date=date,
            field_officer={
                "email": officer["email"],
                "name": officer["name"]
            },
            plan={
                "id": plan["id"],
                "status": plan["status"],
                "submitted_at": plan.get("submitted_at"),
                "is_edited": bool(plan["is_edited"]),
                "revision_number": plan["revision_number"],
                "last_edit_reason": plan.get("last_edit_reason"),
                "planned_customers": planned_count
            },
            plan_items=plan_items,
            actual_visits=actual_visits,
            summary=summary,
            edit_history=edit_history
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Plan vs actual error: {str(e)}")


@router.get("/daily-plans")
async def get_daily_plans(
    date_from: str = Query(..., description="Start date YYYY-MM-DD"),
    date_to: str = Query(..., description="End date YYYY-MM-DD"),
    manager: dict = Depends(get_current_manager)
):
    """
    Get all route plans for date range
    
    **Returns:**
    - List of plans with submission status
    - Officer names
    - Plan counts
    """
    
    try:
        supabase = get_supabase_client()
        
        # Get all plans in date range
        plans_response = supabase.table("daily_route_plans")\
            .select("*, users!inner(name, email)")\
            .gte("plan_date", date_from)\
            .lte("plan_date", date_to)\
            .order("plan_date", desc=True)\
            .execute()
        
        plans = []
        for plan in plans_response.data:
            # Count items
            items_response = supabase.table("route_plan_items")\
                .select("id", count="exact")\
                .eq("plan_id", plan["id"])\
                .execute()
            
            item_count = items_response.count or 0
            
            plans.append({
                "plan_id": plan["id"],
                "plan_date": plan["plan_date"],
                "officer_name": plan["users"]["name"],
                "officer_email": plan["users"]["email"],
                "status": plan["status"],
                "is_edited": bool(plan["is_edited"]),
                "revision_number": plan["revision_number"],
                "submitted_at": plan.get("submitted_at"),
                "customer_count": item_count
            })
        
        return {
            "date_from": date_from,
            "date_to": date_to,
            "total_plans": len(plans),
            "plans": plans
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Daily plans error: {str(e)}")
