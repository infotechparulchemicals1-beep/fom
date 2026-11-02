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
from app.db.supabase_client import get_supabase

router = APIRouter(prefix="/manager/plans", tags=["Manager Plans"])


class PlanItemDetail(BaseModel):
    sequence: int
    customer_name: str
    task_type: str = "order"
    planned_time: Optional[str] = None
    status: str = "pending"
    executed_visit_id: Optional[str] = None
    actual_time: Optional[str] = None
    deviation_minutes: Optional[int] = None


class ActualVisit(BaseModel):
    customer_name: str
    checked_in_at: str
    checked_out_at: Optional[str] = None
    duration_minutes: Optional[int] = None
    planned: bool = True


class EditHistoryItem(BaseModel):
    edited_at: str
    revision_number: int = 1
    edit_reason: str = ""
    changes: dict = {}


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
    """
    try:
        supabase = get_supabase()

        # Get field officer info
        officer = {"email": user_email, "name": user_email.split("@")[0]}
        try:
            officer_res = supabase.table("users").select("id, email, name").eq("email", user_email).execute()
            if officer_res.data:
                officer = officer_res.data[0]
        except Exception:
            pass

        # Query route plan by user_email and plan_date
        plan_res = supabase.table("daily_route_plans").select("*").eq("user_email", user_email).eq("plan_date", date).execute()

        if not plan_res.data:
            # Return empty response instead of failing
            return PlanVsActualResponse(
                date=date,
                field_officer={"email": user_email, "name": officer.get("name") or user_email},
                plan={
                    "id": f"plan-{date}-{user_email.split('@')[0]}",
                    "status": "draft",
                    "submitted_at": None,
                    "is_edited": False,
                    "revision_number": 1,
                    "last_edit_reason": None,
                    "planned_customers": 0,
                },
                plan_items=[],
                actual_visits=[],
                summary={
                    "planned_count": 0,
                    "completed_count": 0,
                    "skipped_count": 0,
                    "unplanned_count": 0,
                    "completion_rate": 0.0,
                    "plan_adherence_rate": 100.0,
                },
                edit_history=[],
            )

        plan = plan_res.data[0]

        # Get plan items with customer details
        plan_items_res = supabase.table("route_plan_items").select("*, customers(*)").eq("plan_id", plan["id"]).order("planned_sequence").execute()
        raw_items = plan_items_res.data or []

        # Get actual visits for the day
        day_start = f"{date}T00:00:00"
        day_end = f"{date}T23:59:59"
        visits = []
        try:
            visits_res = supabase.table("customer_visits").select("*, customers(*)").gte("checked_in_at", day_start).lte("checked_in_at", day_end).execute()
            visits = visits_res.data or []
        except Exception:
            pass

        # Build plan items with execution data
        plan_items = []
        planned_customer_ids = []
        for item in raw_items:
            cust = item.get("customers") or {}
            c_name = cust.get("name") or f"Customer #{str(item.get('customer_id', ''))[:8]}"
            c_id = item.get("customer_id")
            planned_customer_ids.append(c_id)

            matching_visit = next((v for v in visits if v.get("customer_id") == c_id), None)
            actual_time = matching_visit.get("checked_in_at") if matching_visit else None

            deviation_minutes = None
            if matching_visit and item.get("planned_time"):
                try:
                    p_dt = datetime.fromisoformat(f"{date}T{item['planned_time']}")
                    a_dt = datetime.fromisoformat(matching_visit["checked_in_at"].replace("Z", "+00:00"))
                    deviation_minutes = int((a_dt.timestamp() - p_dt.timestamp()) / 60)
                except Exception:
                    pass

            item_status = "completed" if matching_visit else item.get("status", "pending")

            plan_items.append(PlanItemDetail(
                sequence=item.get("planned_sequence", 1),
                customer_name=c_name,
                task_type=item.get("task_type", "order"),
                planned_time=item.get("planned_time", "09:00"),
                status=item_status,
                executed_visit_id=matching_visit.get("id") if matching_visit else None,
                actual_time=actual_time,
                deviation_minutes=deviation_minutes,
            ))

        # Build actual visits list
        actual_visits = []
        for v in visits:
            cust = v.get("customers") or {}
            c_name = cust.get("name") or "Tracked Customer"
            is_planned = v.get("customer_id") in planned_customer_ids

            actual_visits.append(ActualVisit(
                customer_name=c_name,
                checked_in_at=v.get("checked_in_at", ""),
                checked_out_at=v.get("checked_out_at"),
                duration_minutes=v.get("duration_minutes", 0),
                planned=is_planned,
            ))

        planned_count = len(raw_items)
        completed_count = sum(1 for it in plan_items if it.status == "completed")
        skipped_count = sum(1 for it in plan_items if it.status == "skipped")
        unplanned_count = sum(1 for v in actual_visits if not v.planned)

        completion_rate = (completed_count / planned_count * 100) if planned_count > 0 else 0
        plan_adherence = ((planned_count - unplanned_count) / planned_count * 100) if planned_count > 0 else 0

        summary = {
            "planned_count": planned_count,
            "completed_count": completed_count,
            "skipped_count": skipped_count,
            "unplanned_count": unplanned_count,
            "completion_rate": round(completion_rate, 1),
            "plan_adherence_rate": round(max(0, plan_adherence), 1),
        }

        # Edit history fallback
        edit_history = []
        try:
            eh_res = supabase.table("entity_edit_logs").select("*").eq("entity_type", "route_plan").eq("entity_id", plan["id"]).order("edited_at").execute()
            for log in eh_res.data or []:
                edit_history.append(EditHistoryItem(
                    edited_at=log.get("edited_at", ""),
                    revision_number=log.get("revision_number", 1),
                    edit_reason=log.get("edit_reason", ""),
                    changes={},
                ))
        except Exception:
            pass

        return PlanVsActualResponse(
            date=date,
            field_officer={
                "email": officer.get("email") or user_email,
                "name": officer.get("name") or user_email.split("@")[0],
            },
            plan={
                "id": plan["id"],
                "status": plan.get("status", "draft"),
                "submitted_at": plan.get("submission_time") or plan.get("submitted_at"),
                "is_edited": bool(plan.get("is_edited", False)),
                "revision_number": plan.get("revision_number", 1),
                "last_edit_reason": plan.get("last_edit_reason"),
                "planned_customers": planned_count,
            },
            plan_items=plan_items,
            actual_visits=actual_visits,
            summary=summary,
            edit_history=edit_history,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Plan vs actual error: {str(e)}")


@router.get("/daily-plans")
async def get_daily_plans(
    date_from: str = Query(..., description="Start date YYYY-MM-DD"),
    date_to: str = Query(..., description="End date YYYY-MM-DD"),
    user_email: Optional[str] = Query(None, description="Optional officer email"),
    manager: dict = Depends(get_current_manager)
):
    """
    Get all route plans for date range
    """
    try:
        supabase = get_supabase()

        query = supabase.table("daily_route_plans").select("*").gte("plan_date", date_from).lte("plan_date", date_to).order("plan_date", desc=True)
        if user_email:
            query = query.eq("user_email", user_email)

        plans_res = query.execute()

        plans = []
        for plan in plans_res.data or []:
            try:
                items_res = supabase.table("route_plan_items").select("id", count="exact").eq("plan_id", plan["id"]).execute()
                item_count = items_res.count or len(items_res.data or [])
            except Exception:
                item_count = 0

            email = plan.get("user_email") or ""
            name = email.split("@")[0] if "@" in email else email

            plans.append({
                "plan_id": plan["id"],
                "plan_date": plan["plan_date"],
                "officer_name": name,
                "officer_email": email,
                "status": plan.get("status", "draft"),
                "is_edited": bool(plan.get("is_edited", False)),
                "revision_number": plan.get("revision_number", 1),
                "submitted_at": plan.get("submission_time") or plan.get("submitted_at"),
                "customer_count": item_count,
            })

        return {
            "date_from": date_from,
            "date_to": date_to,
            "total_plans": len(plans),
            "plans": plans,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Daily plans error: {str(e)}")
