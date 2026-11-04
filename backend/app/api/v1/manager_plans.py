"""
Manager Plans API
Phase 4: Manager Bridge APIs

Provides village-based plan vs actual comparison and sequence verification.
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
    village_name: str
    customer_name: Optional[str] = None
    task_type: str = "order"
    planned_time: Optional[str] = None
    status: str = "pending"
    executed_visit_id: Optional[str] = None
    actual_time: Optional[str] = None
    deviation_minutes: Optional[int] = None
    village_match: bool = False
    sequence_match: bool = False


class ActualVisit(BaseModel):
    visit_id: Optional[str] = None
    customer_name: str
    village: Optional[str] = None
    checked_in_at: str
    checked_out_at: Optional[str] = None
    duration_minutes: Optional[int] = None
    checkin_lat: Optional[float] = None
    checkin_lng: Optional[float] = None
    checkout_lat: Optional[float] = None
    checkout_lng: Optional[float] = None
    planned: bool = True
    village_in_plan: bool = False
    sequence_order_correct: bool = False


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
    Compare planned route (village-based) vs actual visits for a specific date.
    Evaluates:
    1. Is customer village matching the route plan village?
    2. Are customer visits conducted in the correct sequence as planned?
    3. Provides GPS coordinates and timestamps for check-in & check-out.
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
                    "planned_villages": 0,
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
                    "village_match_count": 0,
                    "sequence_adherence_pct": 100.0,
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
            visits_res = supabase.table("customer_visits").select("*, customers(*)").gte("checked_in_at", day_start).lte("checked_in_at", day_end).order("checked_in_at").execute()
            visits = visits_res.data or []
        except Exception:
            pass

        # Extract planned villages in sequence
        # (sequence_number, lower_case_village, original_village)
        planned_villages = []
        for idx, it in enumerate(raw_items):
            cust = it.get("customers") or {}
            v_name = (it.get("village_name") or cust.get("village") or cust.get("name") or "").strip()
            seq = it.get("planned_sequence") or (idx + 1)
            planned_villages.append((seq, v_name.lower(), v_name))

        # Build actual visits list with sequence & village verification
        actual_visits = []
        visited_villages_in_order = []

        for v_idx, v in enumerate(visits):
            cust = v.get("customers") or {}
            c_name = cust.get("name") or v.get("customer_name") or "Tracked Customer"
            v_village = (v.get("visit_village") or cust.get("village") or "").strip()
            v_village_lower = v_village.lower()
            visited_villages_in_order.append(v_village_lower)

            # Verification 1: Is this village in today's route plan?
            village_in_plan = any(pv[1] == v_village_lower for pv in planned_villages if pv[1])

            # Verification 2: Is this visit in the planned sequence order?
            # Expected planned village at position v_idx:
            expected_seq_village = planned_villages[v_idx][1] if v_idx < len(planned_villages) else None
            sequence_order_correct = (expected_seq_village == v_village_lower) if expected_seq_village else False

            is_planned = village_in_plan or (v.get("customer_id") in [it.get("customer_id") for it in raw_items])

            actual_visits.append(ActualVisit(
                visit_id=v.get("id"),
                customer_name=c_name,
                village=v_village or None,
                checked_in_at=v.get("checked_in_at", ""),
                checked_out_at=v.get("checked_out_at"),
                duration_minutes=v.get("duration_minutes", 0),
                checkin_lat=v.get("checkin_lat"),
                checkin_lng=v.get("checkin_lng"),
                checkout_lat=v.get("checkout_lat"),
                checkout_lng=v.get("checkout_lng"),
                planned=is_planned,
                village_in_plan=village_in_plan,
                sequence_order_correct=sequence_order_correct,
            ))

        # Build plan items with execution data and village matching
        plan_items = []
        for idx, item in enumerate(raw_items):
            cust = item.get("customers") or {}
            village_name = (item.get("village_name") or cust.get("village") or cust.get("name") or "Planned Village").strip()
            village_lower = village_name.lower()
            c_name = cust.get("name") or village_name
            seq = item.get("planned_sequence") or (idx + 1)

            # Find matching visit by customer or village
            matching_visit = next(
                (v for v in actual_visits if (v.village and v.village.lower() == village_lower) or (item.get("customer_id") and v.visit_id == item.get("executed_visit_id"))),
                None
            )

            actual_time = matching_visit.checked_in_at if matching_visit else None
            deviation_minutes = None
            if matching_visit and item.get("planned_time"):
                try:
                    p_dt = datetime.fromisoformat(f"{date}T{item['planned_time']}")
                    a_dt = datetime.fromisoformat(matching_visit.checked_in_at.replace("Z", "+00:00"))
                    deviation_minutes = int((a_dt.timestamp() - p_dt.timestamp()) / 60)
                except Exception:
                    pass

            village_match = bool(matching_visit)
            # Sequence match: did the actual visit index match the planned sequence?
            sequence_match = False
            if idx < len(visited_villages_in_order):
                sequence_match = (visited_villages_in_order[idx] == village_lower)

            item_status = "completed" if matching_visit else item.get("status", "pending")

            plan_items.append(PlanItemDetail(
                sequence=seq,
                village_name=village_name,
                customer_name=c_name,
                task_type=item.get("task_type", "order"),
                planned_time=item.get("planned_time", "09:00"),
                status=item_status,
                executed_visit_id=matching_visit.visit_id if matching_visit else None,
                actual_time=actual_time,
                deviation_minutes=deviation_minutes,
                village_match=village_match,
                sequence_match=sequence_match,
            ))

        planned_count = len(raw_items)
        completed_count = sum(1 for it in plan_items if it.status == "completed")
        skipped_count = sum(1 for it in plan_items if it.status == "skipped")
        unplanned_count = sum(1 for v in actual_visits if not v.planned)
        village_match_count = sum(1 for it in plan_items if it.village_match)

        correct_sequence_count = sum(1 for v in actual_visits if v.sequence_order_correct)
        sequence_adherence_pct = (correct_sequence_count / len(actual_visits) * 100) if len(actual_visits) > 0 else 100.0
        completion_rate = (completed_count / planned_count * 100) if planned_count > 0 else 0
        plan_adherence = ((planned_count - unplanned_count) / planned_count * 100) if planned_count > 0 else 0

        summary = {
            "planned_count": planned_count,
            "completed_count": completed_count,
            "skipped_count": skipped_count,
            "unplanned_count": unplanned_count,
            "completion_rate": round(completion_rate, 1),
            "plan_adherence_rate": round(max(0, plan_adherence), 1),
            "village_match_count": village_match_count,
            "sequence_adherence_pct": round(sequence_adherence_pct, 1),
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
                "planned_villages": planned_count,
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
                "village_count": item_count,
            })

        return {
            "date_from": date_from,
            "date_to": date_to,
            "total_plans": len(plans),
            "plans": plans,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Daily plans error: {str(e)}")
