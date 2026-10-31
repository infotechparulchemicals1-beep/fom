"""
Manager Analytics API
Phase 4: Manager Bridge APIs

Provides discount analytics and high-discount order tracking.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.api.v1.manager_auth import get_current_manager
from app.db.supabase_client import get_supabase

router = APIRouter(prefix="/manager/analytics", tags=["Manager Analytics"])


class OrderItemDetail(BaseModel):
    product_name: str
    quantity: int
    catalog_rate: float
    selling_rate: float
    discount_per_unit: float
    line_discount: float


class HighDiscountOrder(BaseModel):
    order_number: str
    order_date: str
    customer_name: str
    gross_amount: float
    discount_amount: float
    discount_percent: float
    net_amount: float
    items: List[OrderItemDetail]
    manager_approval_needed: bool


class DiscountTrendPoint(BaseModel):
    date: str
    discount_percent: float


class DiscountAnalyticsResponse(BaseModel):
    month_year: str
    field_officer: str
    summary: dict
    high_discount_orders: List[HighDiscountOrder]
    discount_trend: List[DiscountTrendPoint]


@router.get("/discounts", response_model=DiscountAnalyticsResponse)
async def get_discount_analytics(
    user_email: Optional[str] = Query(None, description="Specific FO email or None for all"),
    month_year: str = Query(..., description="Format: YYYY-MM"),
    threshold_percent: float = Query(10.0, description="High discount threshold %"),
    manager: dict = Depends(get_current_manager)
):
    """
    Analyze discount trends and identify high-discount orders
    
    **Provides:**
    - Monthly discount summary
    - High-discount orders (>threshold%)
    - Discount trend by date
    - Discount limit tracking
    
    **Query Parameters:**
    - user_email: Filter by specific FO (optional)
    - month_year: Month to analyze (YYYY-MM)
    - threshold_percent: Flag orders above this % (default 10%)
    
    **Business Rules:**
    - Discount > 10% = Warning alert
    - Discount > 15% = Manager approval needed
    - Monthly discount limit per FO tracked
    """
    
    try:
        supabase = get_supabase()
        
        # Get date range
        month_start = f"{month_year}-01"
        year, month = map(int, month_year.split("-"))
        if month == 12:
            next_month = f"{year+1}-01-01"
        else:
            next_month = f"{year}-{month+1:02d}-01"
        
        # Build query for orders
        query = supabase.table("fo_sales_orders")\
            .select("*, users!inner(name, email), customers!inner(name)")\
            .gte("order_date", month_start)\
            .lt("order_date", next_month)
        
        if user_email:
            # Get user ID from email
            user_response = supabase.table("users")\
                .select("id")\
                .eq("email", user_email)\
                .execute()
            
            if not user_response.data:
                raise HTTPException(status_code=404, detail="Field officer not found")
            
            query = query.eq("user_id", user_response.data[0]["id"])
        
        orders_response = query.execute()
        orders = orders_response.data
        
        # Calculate summary
        total_orders = len(orders)
        total_gross = sum(o.get("gross_amount", 0) for o in orders)
        total_discount = sum(o.get("total_discount_amount", 0) for o in orders)
        total_net = sum(o.get("net_amount", 0) for o in orders)
        average_discount_percent = (total_discount / total_gross * 100) if total_gross > 0 else 0
        
        # Find highest discount
        highest_discount_percent = 0
        for o in orders:
            if o.get("gross_amount", 0) > 0:
                discount_pct = (o.get("total_discount_amount", 0) / o["gross_amount"] * 100)
                if discount_pct > highest_discount_percent:
                    highest_discount_percent = discount_pct
        
        # Get discount limit (placeholder - would be from fo_monthly_targets)
        discount_limit = 20000.00
        discount_remaining = discount_limit - total_discount
        limit_utilization_percent = (total_discount / discount_limit * 100) if discount_limit > 0 else 0
        
        summary = {
            "total_orders": total_orders,
            "total_gross": round(total_gross, 2),
            "total_discount": round(total_discount, 2),
            "total_net": round(total_net, 2),
            "average_discount_percent": round(average_discount_percent, 1),
            "highest_discount_percent": round(highest_discount_percent, 1),
            "discount_limit": discount_limit,
            "discount_remaining": round(discount_remaining, 2),
            "limit_utilization_percent": round(limit_utilization_percent, 1)
        }
        
        # Find high discount orders
        high_discount_orders = []
        for order in orders:
            if order.get("gross_amount", 0) > 0:
                discount_pct = (order.get("total_discount_amount", 0) / order["gross_amount"] * 100)
                
                if discount_pct >= threshold_percent:
                    # Get order items
                    items_response = supabase.table("fo_sales_order_items")\
                        .select("*")\
                        .eq("order_id", order["id"])\
                        .execute()
                    
                    items = []
                    for item in items_response.data:
                        items.append(OrderItemDetail(
                            product_name=item["product_name"],
                            quantity=item["quantity"],
                            catalog_rate=item["catalog_rate"],
                            selling_rate=item["selling_rate"],
                            discount_per_unit=item["discount_per_unit"],
                            line_discount=item["line_discount_total"]
                        ))
                    
                    high_discount_orders.append(HighDiscountOrder(
                        order_number=order["order_number"],
                        order_date=order["order_date"],
                        customer_name=order["customers"]["name"],
                        gross_amount=order["gross_amount"],
                        discount_amount=order["total_discount_amount"],
                        discount_percent=round(discount_pct, 1),
                        net_amount=order["net_amount"],
                        items=items,
                        manager_approval_needed=(discount_pct > 15.0)
                    ))
        
        # Sort by discount percent desc
        high_discount_orders.sort(key=lambda x: x.discount_percent, reverse=True)
        
        # Build discount trend (by date)
        discount_trend = {}
        for order in orders:
            date = order["order_date"]
            if date not in discount_trend:
                discount_trend[date] = {"gross": 0, "discount": 0}
            
            discount_trend[date]["gross"] += order.get("gross_amount", 0)
            discount_trend[date]["discount"] += order.get("total_discount_amount", 0)
        
        discount_trend_list = []
        for date, values in sorted(discount_trend.items()):
            discount_pct = (values["discount"] / values["gross"] * 100) if values["gross"] > 0 else 0
            discount_trend_list.append(DiscountTrendPoint(
                date=date,
                discount_percent=round(discount_pct, 1)
            ))
        
        return DiscountAnalyticsResponse(
            month_year=month_year,
            field_officer=user_email or "All Officers",
            summary=summary,
            high_discount_orders=high_discount_orders,
            discount_trend=discount_trend_list
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Discount analytics error: {str(e)}")


@router.get("/top-products")
async def get_top_products(
    month_year: str = Query(..., description="Format: YYYY-MM"),
    limit: int = Query(10, description="Number of products to return"),
    manager: dict = Depends(get_current_manager)
):
    """
    Get top-selling products for the month
    
    **Returns:**
    - Product name
    - Quantity sold
    - Revenue generated
    - Average discount %
    """
    
    try:
        supabase = get_supabase()
        
        # Get date range
        month_start = f"{month_year}-01"
        year, month = map(int, month_year.split("-"))
        if month == 12:
            next_month = f"{year+1}-01-01"
        else:
            next_month = f"{year}-{month+1:02d}-01"
        
        # Get all order items for the month
        items_response = supabase.table("fo_sales_order_items")\
            .select("*, fo_sales_orders!inner(order_date)")\
            .gte("fo_sales_orders.order_date", month_start)\
            .lt("fo_sales_orders.order_date", next_month)\
            .execute()
        
        # Aggregate by product
        products = {}
        for item in items_response.data:
            product_name = item["product_name"]
            
            if product_name not in products:
                products[product_name] = {
                    "quantity_sold": 0,
                    "revenue": 0,
                    "total_discount": 0,
                    "gross_revenue": 0
                }
            
            products[product_name]["quantity_sold"] += item["quantity"]
            products[product_name]["revenue"] += item["line_net_amount"]
            products[product_name]["total_discount"] += item["line_discount_total"]
            products[product_name]["gross_revenue"] += (item["catalog_rate"] * item["quantity"])
        
        # Convert to list and add avg discount
        product_list = []
        for name, data in products.items():
            avg_discount_pct = (data["total_discount"] / data["gross_revenue"] * 100) if data["gross_revenue"] > 0 else 0
            
            product_list.append({
                "product_name": name,
                "quantity_sold": data["quantity_sold"],
                "revenue": round(data["revenue"], 2),
                "average_discount_percent": round(avg_discount_pct, 1)
            })
        
        # Sort by revenue desc
        product_list.sort(key=lambda x: x["revenue"], reverse=True)
        
        return {
            "month_year": month_year,
            "top_products": product_list[:limit],
            "total_products": len(product_list)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Top products error: {str(e)}")


@router.get("/sales-summary")
async def get_sales_summary(
    period: str = Query(..., description="today, week, month, custom"),
    date_from: Optional[str] = Query(None, description="For custom period"),
    date_to: Optional[str] = Query(None, description="For custom period"),
    manager: dict = Depends(get_current_manager)
):
    """
    Get aggregated sales data for dashboard
    
    **Periods:**
    - today: Today's sales
    - week: Last 7 days
    - month: Current month
    - custom: Specify date_from and date_to
    
    **Returns:**
    - Total orders, sales, discounts, collections
    - Average order value
    - Conversion rate
    - Team breakdown
    """
    
    try:
        supabase = get_supabase()
        
        # Calculate date range based on period
        today = datetime.now().date()
        
        if period == "today":
            date_from = str(today)
            date_to = str(today)
        elif period == "week":
            date_from = str(today - timedelta(days=6))
            date_to = str(today)
        elif period == "month":
            date_from = f"{today.year}-{today.month:02d}-01"
            date_to = str(today)
        elif period == "custom":
            if not date_from or not date_to:
                raise HTTPException(status_code=400, detail="date_from and date_to required for custom period")
        else:
            raise HTTPException(status_code=400, detail="Invalid period")
        
        # Get orders
        orders_response = supabase.table("fo_sales_orders")\
            .select("*")\
            .gte("order_date", date_from)\
            .lte("order_date", date_to)\
            .execute()
        
        orders = orders_response.data
        
        # Get receipts
        receipts_response = supabase.table("fo_payment_receipts")\
            .select("*")\
            .gte("payment_date", date_from)\
            .lte("payment_date", date_to)\
            .execute()
        
        receipts = receipts_response.data
        
        # Get visits
        visits_response = supabase.table("customer_visits")\
            .select("id", count="exact")\
            .gte("checked_in_at", f"{date_from}T00:00:00")\
            .lte("checked_in_at", f"{date_to}T23:59:59")\
            .execute()
        
        total_visits = visits_response.count or 0
        
        # Calculate summary
        total_orders = len(orders)
        total_sales = sum(o.get("net_amount", 0) for o in orders)
        total_discount = sum(o.get("total_discount_amount", 0) for o in orders)
        total_collection = sum(r.get("amount", 0) for r in receipts)
        average_order_value = total_sales / total_orders if total_orders > 0 else 0
        conversion_rate = (total_orders / total_visits * 100) if total_visits > 0 else 0
        
        # Get unique officers
        officer_ids = list(set([o["user_id"] for o in orders]))
        
        return {
            "period": period,
            "date_from": date_from,
            "date_to": date_to,
            "team_summary": {
                "total_orders": total_orders,
                "total_sales": round(total_sales, 2),
                "total_discount": round(total_discount, 2),
                "total_collection": round(total_collection, 2),
                "total_visits": total_visits,
                "average_order_value": round(average_order_value, 2),
                "conversion_rate": round(conversion_rate, 1),
                "officers_count": len(officer_ids)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sales summary error: {str(e)}")


from datetime import timedelta

