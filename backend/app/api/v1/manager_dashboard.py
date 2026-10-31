"""
Manager Dashboard API
Phase 4: Manager Bridge APIs

Provides dashboard data for manager overview screen.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
from app.api.v1.manager_auth import get_current_manager
from app.db.supabase_client import get_supabase_client

router = APIRouter(prefix="/manager/dashboard", tags=["Manager Dashboard"])


class KPIMetrics(BaseModel):
    month_target: float
    month_achieved: float
    achievement_percent: float
    pending_verifications: int
    high_discount_alerts: int
    plan_adherence_avg: float


class Alert(BaseModel):
    type: str
    severity: str
    message: str
    action_url: Optional[str] = None


class RecentActivity(BaseModel):
    timestamp: str
    officer: str
    activity: str


class DashboardResponse(BaseModel):
    manager: dict
    kpis: KPIMetrics
    alerts: List[Alert]
    recent_activity: List[RecentActivity]


@router.get("/overview", response_model=DashboardResponse)
async def get_dashboard_overview(
    month_year: str = Query(..., description="Format: YYYY-MM"),
    manager: dict = Depends(get_current_manager)
):
    """
    Get complete dashboard data for manager home screen
    
    **Provides:**
    - Monthly KPIs (target, achieved, pending items)
    - Alerts (high discounts, plan deviations)
    - Recent activity feed
    
    **Query Parameters:**
    - month_year: Month to show data for (YYYY-MM)
    
    **Authentication:**
    Requires valid manager JWT token in Authorization header.
    """
    
    try:
        supabase = get_supabase_client()
        manager_email = manager["email"]
        
        # Get manager's assigned officers
        # In production, query manager_officer_assignments table
        # For now, get all active field officers (simplified)
        officers_response = supabase.table("users")\
            .select("email, name")\
            .eq("role", "field_officer")\
            .eq("is_active", True)\
            .execute()
        
        officer_emails = [o["email"] for o in officers_response.data]
        team_size = len(officer_emails)
        
        # Calculate monthly KPIs
        month_start = f"{month_year}-01"
        # Get last day of month
        year, month = map(int, month_year.split("-"))
        if month == 12:
            next_month = f"{year+1}-01-01"
        else:
            next_month = f"{year}-{month+1:02d}-01"
        
        # Get monthly targets
        targets_response = supabase.table("fo_monthly_targets")\
            .select("*")\
            .eq("month_year", month_year)\
            .in_("user_id", officer_emails)\
            .execute()
        
        month_target = sum(t["target_amount"] for t in targets_response.data)
        
        # Get achieved sales (from orders)
        orders_response = supabase.table("fo_sales_orders")\
            .select("net_amount")\
            .gte("order_date", month_start)\
            .lt("order_date", next_month)\
            .execute()
        
        month_achieved = sum(o["net_amount"] for o in orders_response.data if o["net_amount"])
        
        achievement_percent = (month_achieved / month_target * 100) if month_target > 0 else 0
        
        # Get pending verifications (visits)
        pending_verifications_response = supabase.table("customer_visits")\
            .select("id", count="exact")\
            .eq("verification_status", "pending")\
            .gte("checked_in_at", month_start)\
            .lt("checked_in_at", next_month)\
            .execute()
        
        pending_verifications = pending_verifications_response.count or 0
        
        # Get high discount alerts (orders with > 10% discount)
        high_discount_response = supabase.table("fo_sales_orders")\
            .select("*")\
            .gte("order_date", month_start)\
            .lt("order_date", next_month)\
            .execute()
        
        high_discount_orders = [
            o for o in high_discount_response.data 
            if o.get("gross_amount", 0) > 0 and 
            (o.get("total_discount_amount", 0) / o["gross_amount"] * 100) > 10
        ]
        high_discount_alerts = len(high_discount_orders)
        
        # Calculate plan adherence (simplified)
        # In production, compare route_plan_items with actual customer_visits
        plan_adherence_avg = 87.5  # Placeholder
        
        # Build KPIs
        kpis = KPIMetrics(
            month_target=month_target,
            month_achieved=month_achieved,
            achievement_percent=round(achievement_percent, 1),
            pending_verifications=pending_verifications,
            high_discount_alerts=high_discount_alerts,
            plan_adherence_avg=plan_adherence_avg
        )
        
        # Build alerts
        alerts = []
        
        # High discount alerts
        if high_discount_alerts > 0:
            for order in high_discount_orders[:3]:  # Top 3
                discount_pct = (order["total_discount_amount"] / order["gross_amount"] * 100)
                alerts.append(Alert(
                    type="high_discount",
                    severity="warning",
                    message=f"Order {order['order_number']} has {discount_pct:.1f}% discount",
                    action_url=f"/orders/{order['id']}"
                ))
        
        # Pending verifications alert
        if pending_verifications > 10:
            alerts.append(Alert(
                type="pending_verifications",
                severity="info",
                message=f"{pending_verifications} visits pending verification",
                action_url="/verifications"
            ))
        
        # Get recent activity (last 10 orders/receipts)
        recent_orders = supabase.table("fo_sales_orders")\
            .select("*, users!inner(name)")\
            .order("created_at", desc=True)\
            .limit(5)\
            .execute()
        
        recent_receipts = supabase.table("fo_payment_receipts")\
            .select("*, users!inner(name)")\
            .order("created_at", desc=True)\
            .limit(5)\
            .execute()
        
        recent_activity = []
        
        for order in recent_orders.data:
            recent_activity.append(RecentActivity(
                timestamp=order["created_at"],
                officer=order["users"]["name"] if "users" in order else "Field Officer",
                activity=f"Created order {order['order_number']} for ₹{order['net_amount']:,.2f}"
            ))
        
        for receipt in recent_receipts.data:
            recent_activity.append(RecentActivity(
                timestamp=receipt["created_at"],
                officer=receipt["users"]["name"] if "users" in receipt else "Field Officer",
                activity=f"Collected payment {receipt['receipt_number']} of ₹{receipt['amount']:,.2f}"
            ))
        
        # Sort by timestamp desc
        recent_activity.sort(key=lambda x: x.timestamp, reverse=True)
        recent_activity = recent_activity[:10]  # Top 10
        
        return DashboardResponse(
            manager={
                "email": manager_email,
                "name": manager["name"],
                "team_size": team_size
            },
            kpis=kpis,
            alerts=alerts,
            recent_activity=recent_activity
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dashboard error: {str(e)}")


@router.get("/team-summary")
async def get_team_summary(
    month_year: str = Query(..., description="Format: YYYY-MM"),
    manager: dict = Depends(get_current_manager)
):
    """
    Get aggregated team performance summary
    
    **Returns:**
    - Total orders, sales, collections
    - Average order value
    - Conversion rate
    - Officer count
    - Performance by officer
    """
    
    try:
        supabase = get_supabase_client()
        
        # Get date range
        month_start = f"{month_year}-01"
        year, month = map(int, month_year.split("-"))
        if month == 12:
            next_month = f"{year+1}-01-01"
        else:
            next_month = f"{year}-{month+1:02d}-01"
        
        # Get team officers
        officers_response = supabase.table("users")\
            .select("id, email, name")\
            .eq("role", "field_officer")\
            .eq("is_active", True)\
            .execute()
        
        officers = officers_response.data
        officer_ids = [o["id"] for o in officers]
        
        # Get orders
        orders_response = supabase.table("fo_sales_orders")\
            .select("*")\
            .in_("user_id", officer_ids)\
            .gte("order_date", month_start)\
            .lt("order_date", next_month)\
            .execute()
        
        orders = orders_response.data
        
        # Get receipts
        receipts_response = supabase.table("fo_payment_receipts")\
            .select("*")\
            .in_("user_id", officer_ids)\
            .gte("payment_date", month_start)\
            .lt("payment_date", next_month)\
            .execute()
        
        receipts = receipts_response.data
        
        # Get visits
        visits_response = supabase.table("customer_visits")\
            .select("id", count="exact")\
            .gte("checked_in_at", month_start)\
            .lt("checked_in_at", next_month)\
            .execute()
        
        total_visits = visits_response.count or 0
        
        # Calculate metrics
        total_orders = len(orders)
        total_sales = sum(o.get("net_amount", 0) for o in orders)
        total_discount = sum(o.get("total_discount_amount", 0) for o in orders)
        total_collection = sum(r.get("amount", 0) for r in receipts)
        average_order_value = total_sales / total_orders if total_orders > 0 else 0
        conversion_rate = (total_orders / total_visits * 100) if total_visits > 0 else 0
        
        # By officer breakdown
        by_officer = []
        for officer in officers:
            officer_orders = [o for o in orders if o["user_id"] == officer["id"]]
            officer_receipts = [r for r in receipts if r["user_id"] == officer["id"]]
            
            officer_sales = sum(o.get("net_amount", 0) for o in officer_orders)
            officer_collection = sum(r.get("amount", 0) for r in officer_receipts)
            
            # Get target
            target_response = supabase.table("fo_monthly_targets")\
                .select("target_amount")\
                .eq("user_id", officer["id"])\
                .eq("month_year", month_year)\
                .execute()
            
            target = target_response.data[0]["target_amount"] if target_response.data else 0
            achievement_pct = (officer_sales / target * 100) if target > 0 else 0
            
            by_officer.append({
                "email": officer["email"],
                "name": officer["name"],
                "orders_count": len(officer_orders),
                "sales_amount": officer_sales,
                "collection_amount": officer_collection,
                "visits_count": 0,  # TODO: Count visits per officer
                "target_achievement_percent": round(achievement_pct, 1)
            })
        
        return {
            "period": "month",
            "date_from": month_start,
            "date_to": next_month,
            "team_summary": {
                "total_orders": total_orders,
                "total_sales": round(total_sales, 2),
                "total_discount": round(total_discount, 2),
                "total_collection": round(total_collection, 2),
                "total_visits": total_visits,
                "average_order_value": round(average_order_value, 2),
                "conversion_rate": round(conversion_rate, 1),
                "officers_count": len(officers)
            },
            "by_officer": by_officer
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Team summary error: {str(e)}")
