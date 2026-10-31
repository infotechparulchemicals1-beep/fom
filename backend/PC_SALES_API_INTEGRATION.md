# PC-Sales API Integration Guide
## AURA Manager & Caller Bridge APIs

**Target Audience:** PC-Sales Frontend Developers  
**Roles Covered:** Manager, Caller  
**Base URL:** `https://fom-1.onrender.com` (Production) | `http://localhost:8000` (Development)  
**Version:** 2.0.0  
**Last Updated:** November 1, 2026

---

## 📋 Table of Contents

1. [Authentication](#authentication)
2. [Manager APIs](#manager-apis)
3. [Caller APIs](#caller-apis)
4. [Data Models](#data-models)
5. [Error Handling](#error-handling)
6. [Code Examples](#code-examples)

---

## 🔐 Authentication

### Overview
All API requests require JWT authentication. The API uses a two-step authentication flow:

1. **Validate Manager/Caller** with API key
2. **Use JWT token** for subsequent requests

### Step 1: Validate User & Get Token

**Endpoint:** `POST /api/v1/manager/auth/validate`

**Request:**
```json
{
  "email": "manager@paruchemicals.com",
  "api_key": "AURA_MANAGER_SECRET_2026"
}
```

**Response (Success):**
```json
{
  "valid": true,
  "manager": {
    "email": "manager@paruchemicals.com",
    "name": "Rajesh Kumar",
    "role": "manager"
  },
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_at": "2026-11-01T16:30:00Z"
}
```

**Response (Invalid):**
```json
{
  "valid": false,
  "error": "Invalid API key or user not found"
}
```

**Token Expiry:** 8 hours

---

### Step 2: Use Token in Requests

**Header:**
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Example:**
```javascript
fetch('https://fom-1.onrender.com/api/v1/manager/dashboard/overview', {
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
});
```

---

### Step 3: Refresh Token (Optional)

**Endpoint:** `POST /api/v1/manager/auth/refresh`

**Headers:**
```
Authorization: Bearer <old_token>
```

**Response:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_at": "2026-11-01T18:30:00Z"
}
```

---

## 👔 Manager APIs

### 1. Dashboard Overview

**Purpose:** Get complete dashboard data for a manager including KPIs, alerts, and recent activity.

**Endpoint:** `GET /api/v1/manager/dashboard/overview`

**Query Parameters:**
- `month_year` (required): Format `YYYY-MM` (e.g., `2026-11`)

**Request:**
```
GET /api/v1/manager/dashboard/overview?month_year=2026-11
Authorization: Bearer <token>
```

**Response:**
```json
{
  "month_year": "2026-11",
  "kpis": {
    "total_orders": 145,
    "total_sales": 2450000.00,
    "total_collections": 2100000.00,
    "total_visits": 320,
    "avg_order_value": 16896.55,
    "conversion_rate": 45.31,
    "target_achievement": {
      "target_amount": 3000000.00,
      "achieved_amount": 2450000.00,
      "shortfall": 550000.00,
      "achievement_percent": 81.67
    }
  },
  "alerts": {
    "pending_verifications": 12,
    "high_discount_orders": 8,
    "plan_adherence_issues": 3
  },
  "recent_activity": [
    {
      "type": "order",
      "field_officer": "Amit Sharma",
      "customer": "Raj Traders",
      "amount": 45000.00,
      "discount_percent": 12.5,
      "timestamp": "2026-11-01T14:30:00Z"
    },
    {
      "type": "visit",
      "field_officer": "Priya Singh",
      "customer": "Gupta Distributors",
      "status": "completed",
      "timestamp": "2026-11-01T14:15:00Z"
    }
  ]
}
```

**Use Case:** Display on manager's home dashboard in PC-Sales.

---

### 2. Team Summary

**Purpose:** Get aggregated performance data for all field officers under a manager.

**Endpoint:** `GET /api/v1/manager/dashboard/team-summary`

**Query Parameters:**
- `month_year` (required): Format `YYYY-MM`

**Request:**
```
GET /api/v1/manager/dashboard/team-summary?month_year=2026-11
Authorization: Bearer <token>
```

**Response:**
```json
{
  "month_year": "2026-11",
  "team_performance": [
    {
      "field_officer": {
        "email": "amit.sharma@paruchemicals.com",
        "name": "Amit Sharma"
      },
      "stats": {
        "total_visits": 45,
        "total_orders": 32,
        "total_sales": 540000.00,
        "total_collections": 480000.00,
        "conversion_rate": 71.11,
        "avg_order_value": 16875.00
      },
      "targets": {
        "target_amount": 600000.00,
        "achievement_percent": 90.00,
        "shortfall": 60000.00
      }
    },
    {
      "field_officer": {
        "email": "priya.singh@paruchemicals.com",
        "name": "Priya Singh"
      },
      "stats": {
        "total_visits": 52,
        "total_orders": 28,
        "total_sales": 420000.00,
        "total_collections": 390000.00,
        "conversion_rate": 53.85,
        "avg_order_value": 15000.00
      },
      "targets": {
        "target_amount": 500000.00,
        "achievement_percent": 84.00,
        "shortfall": 80000.00
      }
    }
  ],
  "totals": {
    "total_field_officers": 10,
    "total_visits": 320,
    "total_orders": 145,
    "total_sales": 2450000.00,
    "team_conversion_rate": 45.31
  }
}
```

**Use Case:** Team performance page showing all FOs.

---

### 3. Route Plan vs Actual

**Purpose:** Compare planned route vs actual visits for a field officer on a specific date.

**Endpoint:** `GET /api/v1/manager/plans/vs-actual`

**Query Parameters:**
- `user_email` (required): Field officer email
- `date` (required): Format `YYYY-MM-DD`

**Request:**
```
GET /api/v1/manager/plans/vs-actual?user_email=amit.sharma@paruchemicals.com&date=2026-11-01
Authorization: Bearer <token>
```

**Response:**
```json
{
  "date": "2026-11-01",
  "field_officer": {
    "email": "amit.sharma@paruchemicals.com",
    "name": "Amit Sharma"
  },
  "plan": {
    "plan_id": "plan-uuid-123",
    "status": "submitted",
    "submission_time": "2026-11-01T08:15:00Z",
    "items": [
      {
        "sequence": 1,
        "customer": "Raj Traders",
        "village": "Kothrud",
        "planned_time": "09:00 AM",
        "status": "completed",
        "actual_visit": {
          "check_in_time": "2026-11-01T09:10:00Z",
          "check_out_time": "2026-11-01T09:45:00Z",
          "duration_minutes": 35,
          "deviation_minutes": 10
        }
      },
      {
        "sequence": 2,
        "customer": "Gupta Distributors",
        "village": "Shivaji Nagar",
        "planned_time": "10:30 AM",
        "status": "completed",
        "actual_visit": {
          "check_in_time": "2026-11-01T10:25:00Z",
          "check_out_time": "2026-11-01T11:00:00Z",
          "duration_minutes": 35,
          "deviation_minutes": -5
        }
      },
      {
        "sequence": 3,
        "customer": "Sharma Enterprises",
        "village": "Pimpri",
        "planned_time": "12:00 PM",
        "status": "skipped",
        "actual_visit": null
      }
    ]
  },
  "unplanned_visits": [
    {
      "customer": "New Customer XYZ",
      "village": "Wakad",
      "check_in_time": "2026-11-01T13:30:00Z",
      "check_out_time": "2026-11-01T14:00:00Z",
      "reason": "Customer called for urgent requirement"
    }
  ],
  "summary": {
    "planned_count": 3,
    "completed_count": 2,
    "skipped_count": 1,
    "unplanned_count": 1,
    "completion_rate": 66.67,
    "plan_adherence_rate": 66.67
  },
  "edit_history": [
    {
      "timestamp": "2026-11-01T11:15:00Z",
      "action": "remove",
      "customer": "Sharma Enterprises",
      "reason": "Customer unavailable today"
    }
  ]
}
```

**Use Case:** Plan adherence analysis and route optimization insights.

---

### 4. Daily Plans List

**Purpose:** Get list of route plans for date range.

**Endpoint:** `GET /api/v1/manager/plans/daily-plans`

**Query Parameters:**
- `user_email` (optional): Filter by field officer
- `start_date` (required): Format `YYYY-MM-DD`
- `end_date` (required): Format `YYYY-MM-DD`
- `status` (optional): `draft`, `submitted`, `completed`

**Request:**
```
GET /api/v1/manager/plans/daily-plans?start_date=2026-11-01&end_date=2026-11-07&status=submitted
Authorization: Bearer <token>
```

**Response:**
```json
{
  "plans": [
    {
      "plan_id": "plan-uuid-123",
      "date": "2026-11-01",
      "field_officer": {
        "email": "amit.sharma@paruchemicals.com",
        "name": "Amit Sharma"
      },
      "status": "submitted",
      "submission_time": "2026-11-01T08:15:00Z",
      "planned_visits": 5,
      "completed_visits": 4,
      "completion_rate": 80.00
    },
    {
      "plan_id": "plan-uuid-456",
      "date": "2026-11-02",
      "field_officer": {
        "email": "amit.sharma@paruchemicals.com",
        "name": "Amit Sharma"
      },
      "status": "submitted",
      "submission_time": "2026-11-02T08:20:00Z",
      "planned_visits": 6,
      "completed_visits": 5,
      "completion_rate": 83.33
    }
  ],
  "count": 2
}
```

**Use Case:** Weekly/monthly plan review.

---

### 5. Discount Analytics

**Purpose:** Get discount trends and high-discount orders.

**Endpoint:** `GET /api/v1/manager/analytics/discounts`

**Query Parameters:**
- `month_year` (required): Format `YYYY-MM`
- `user_email` (optional): Filter by field officer
- `threshold_percent` (optional): Default `10` (flag orders above this %)

**Request:**
```
GET /api/v1/manager/analytics/discounts?month_year=2026-11&threshold_percent=10
Authorization: Bearer <token>
```

**Response:**
```json
{
  "month_year": "2026-11",
  "summary": {
    "total_orders": 145,
    "total_discount_amount": 245000.00,
    "avg_discount_percent": 8.5,
    "high_discount_orders": 18,
    "manager_approval_needed": 3
  },
  "high_discount_orders": [
    {
      "order_id": "ORD-1730468123-abc",
      "order_number": "ORD-1730468123-abc",
      "date": "2026-11-01",
      "field_officer": {
        "email": "amit.sharma@paruchemicals.com",
        "name": "Amit Sharma"
      },
      "customer": "Raj Traders",
      "order_total": 45000.00,
      "discount_amount": 5625.00,
      "discount_percent": 12.5,
      "needs_approval": false,
      "alert_level": "warning"
    },
    {
      "order_id": "ORD-1730468789-def",
      "order_number": "ORD-1730468789-def",
      "date": "2026-11-01",
      "field_officer": {
        "email": "priya.singh@paruchemicals.com",
        "name": "Priya Singh"
      },
      "customer": "Gupta Distributors",
      "order_total": 80000.00,
      "discount_amount": 12800.00,
      "discount_percent": 16.0,
      "needs_approval": true,
      "alert_level": "critical"
    }
  ],
  "discount_by_fo": [
    {
      "field_officer": {
        "email": "amit.sharma@paruchemicals.com",
        "name": "Amit Sharma"
      },
      "total_discount": 52000.00,
      "avg_discount_percent": 9.2,
      "monthly_limit": 100000.00,
      "utilization_percent": 52.0
    }
  ],
  "trend": [
    {
      "date": "2026-11-01",
      "total_discount": 12500.00,
      "avg_percent": 8.2
    },
    {
      "date": "2026-11-02",
      "total_discount": 15200.00,
      "avg_percent": 9.1
    }
  ]
}
```

**Business Rules:**
- **Discount > 10%**: Warning alert (yellow)
- **Discount > 15%**: Critical alert (red), needs manager approval
- **Monthly Limit Tracking**: Per field officer

**Use Case:** Discount monitoring dashboard and approval workflow.

---

### 6. Top Products

**Purpose:** Get best-selling products by revenue or volume.

**Endpoint:** `GET /api/v1/manager/analytics/top-products`

**Query Parameters:**
- `month_year` (required): Format `YYYY-MM`
- `limit` (optional): Default `10`
- `sort_by` (optional): `revenue` or `volume`, default `revenue`

**Request:**
```
GET /api/v1/manager/analytics/top-products?month_year=2026-11&limit=10&sort_by=revenue
Authorization: Bearer <token>
```

**Response:**
```json
{
  "month_year": "2026-11",
  "top_products": [
    {
      "product_id": "prod-uuid-1",
      "product_name": "Parul Super Finish 20L",
      "total_quantity": 450,
      "total_liters": 9000.0,
      "total_revenue": 540000.00,
      "order_count": 85,
      "avg_price_per_unit": 1200.00
    },
    {
      "product_id": "prod-uuid-2",
      "product_name": "FS Calcival Premium 10L",
      "total_quantity": 320,
      "total_liters": 3200.0,
      "total_revenue": 384000.00,
      "order_count": 64,
      "avg_price_per_unit": 1200.00
    },
    {
      "product_id": "prod-uuid-3",
      "product_name": "Parul Economy Pack 5L",
      "total_quantity": 600,
      "total_liters": 3000.0,
      "total_revenue": 300000.00,
      "order_count": 120,
      "avg_price_per_unit": 500.00
    }
  ]
}
```

**Use Case:** Product performance analysis and inventory planning.

---

### 7. Sales Summary

**Purpose:** Get aggregated sales data for custom periods.

**Endpoint:** `GET /api/v1/manager/analytics/sales-summary`

**Query Parameters:**
- `period` (required): `today`, `week`, `month`, `custom`
- `start_date` (required if period=custom): Format `YYYY-MM-DD`
- `end_date` (required if period=custom): Format `YYYY-MM-DD`
- `user_email` (optional): Filter by field officer

**Request:**
```
GET /api/v1/manager/analytics/sales-summary?period=month
Authorization: Bearer <token>
```

**Response:**
```json
{
  "period": "month",
  "start_date": "2026-11-01",
  "end_date": "2026-11-30",
  "summary": {
    "total_orders": 145,
    "total_sales": 2450000.00,
    "total_collections": 2100000.00,
    "total_visits": 320,
    "total_customers": 95,
    "avg_order_value": 16896.55,
    "conversion_rate": 45.31,
    "collection_efficiency": 85.71
  },
  "by_payment_method": {
    "cash": 1200000.00,
    "upi": 650000.00,
    "cheque": 200000.00,
    "rtgs_neft": 50000.00
  },
  "daily_breakdown": [
    {
      "date": "2026-11-01",
      "orders": 12,
      "sales": 204000.00,
      "collections": 180000.00
    },
    {
      "date": "2026-11-02",
      "orders": 15,
      "sales": 255000.00,
      "collections": 220000.00
    }
  ]
}
```

**Use Case:** Financial reporting and performance tracking.

---

### 8. Pending Verifications

**Purpose:** Get list of visits that need manager verification (Second Pitch workflow).

**Endpoint:** `GET /api/v1/manager/verification/pending`

**Query Parameters:**
- `limit` (optional): Default `50`
- `offset` (optional): Default `0`

**Request:**
```
GET /api/v1/manager/verification/pending?limit=20
Authorization: Bearer <token>
```

**Response:**
```json
{
  "pending_visits": [
    {
      "visit_id": "visit-uuid-123",
      "date": "2026-11-01",
      "field_officer": {
        "email": "amit.sharma@paruchemicals.com",
        "name": "Amit Sharma"
      },
      "customer": {
        "customer_id": "cust-uuid-456",
        "name": "Raj Traders",
        "mobile": "9876543210",
        "village": "Kothrud"
      },
      "visit_details": {
        "check_in_time": "2026-11-01T09:10:00Z",
        "check_out_time": "2026-11-01T09:45:00Z",
        "duration_minutes": 35,
        "notes": "Discussed new product requirements. Customer interested in bulk order.",
        "photo_count": 3
      },
      "gps": {
        "latitude": 18.5074,
        "longitude": 73.8077
      },
      "order_created": true,
      "order_amount": 45000.00,
      "days_pending": 2
    },
    {
      "visit_id": "visit-uuid-789",
      "date": "2026-11-01",
      "field_officer": {
        "email": "priya.singh@paruchemicals.com",
        "name": "Priya Singh"
      },
      "customer": {
        "customer_id": "cust-uuid-321",
        "name": "Gupta Distributors",
        "mobile": "9876543211",
        "village": "Shivaji Nagar"
      },
      "visit_details": {
        "check_in_time": "2026-11-01T10:25:00Z",
        "check_out_time": "2026-11-01T11:00:00Z",
        "duration_minutes": 35,
        "notes": "Customer needs to discuss with partner. Follow-up required.",
        "photo_count": 2
      },
      "gps": {
        "latitude": 18.5304,
        "longitude": 73.8567
      },
      "order_created": false,
      "order_amount": null,
      "days_pending": 2
    }
  ],
  "total_pending": 12,
  "count": 2
}
```

**Use Case:** Manager verification workflow - call customers and verify visits.

---

### 9. Verify Visit (Second Pitch)

**Purpose:** Manager verifies visit after calling customer and records second pitch status.

**Endpoint:** `POST /api/v1/manager/verification/verify`

**Request Body:**
```json
{
  "visit_id": "visit-uuid-123",
  "manager_email": "manager@paruchemicals.com",
  "verified": true,
  "call_notes": "Called customer, confirmed visit. Customer agreed to place order next week.",
  "second_pitch_status": "pitched_interested"
}
```

**Second Pitch Status Values:**
- `not_pitched` - Manager didn't pitch product
- `pitched_interested` - Customer showed interest
- `pitched_follow_up` - Needs follow-up call/visit
- `pitched_converted` - Customer agreed to order

**Response:**
```json
{
  "success": true,
  "visit_id": "visit-uuid-123",
  "verification": {
    "verified": true,
    "verified_by": "manager@paruchemicals.com",
    "verified_at": "2026-11-03T15:30:00Z",
    "call_notes": "Called customer, confirmed visit. Customer agreed to place order next week.",
    "second_pitch_status": "pitched_interested"
  },
  "notification_sent": true,
  "follow_up_created": true,
  "follow_up_id": "followup-uuid-999"
}
```

**Business Logic:**
- If `second_pitch_status = "pitched_interested"` → Auto-creates follow-up task for FO
- Sends notification to field officer
- Updates visit record with verification data

**Use Case:** Second pitch workflow - manager calls customer and pitches again.

---

### 10. Visit Details

**Purpose:** Get complete visit details including photos, notes, orders, and receipts.

**Endpoint:** `GET /api/v1/manager/verification/visit-details/{visit_id}`

**Request:**
```
GET /api/v1/manager/verification/visit-details/visit-uuid-123
Authorization: Bearer <token>
```

**Response:**
```json
{
  "visit_id": "visit-uuid-123",
  "date": "2026-11-01",
  "field_officer": {
    "email": "amit.sharma@paruchemicals.com",
    "name": "Amit Sharma",
    "mobile": "9876543200"
  },
  "customer": {
    "customer_id": "cust-uuid-456",
    "name": "Raj Traders",
    "contact_person": "Rajesh Kumar",
    "mobile": "9876543210",
    "village": "Kothrud",
    "city": "Pune"
  },
  "visit_timeline": {
    "check_in_time": "2026-11-01T09:10:00Z",
    "check_out_time": "2026-11-01T09:45:00Z",
    "duration_minutes": 35
  },
  "gps_data": {
    "check_in_lat": 18.5074,
    "check_in_lon": 73.8077,
    "check_out_lat": 18.5075,
    "check_out_lon": 73.8078,
    "distance_from_customer": 12
  },
  "visit_notes": "Discussed new product requirements. Customer interested in bulk order next month.",
  "photos": [
    {
      "photo_id": "photo-uuid-1",
      "url": "https://storage.supabase.co/photos/visit-uuid-123-1.jpg",
      "timestamp": "2026-11-01T09:45:00Z"
    },
    {
      "photo_id": "photo-uuid-2",
      "url": "https://storage.supabase.co/photos/visit-uuid-123-2.jpg",
      "timestamp": "2026-11-01T09:45:00Z"
    }
  ],
  "orders": [
    {
      "order_id": "order-uuid-789",
      "order_number": "ORD-1730468123-abc",
      "date": "2026-11-01",
      "gross_amount": 50000.00,
      "discount_amount": 5000.00,
      "net_amount": 45000.00,
      "discount_percent": 10.0,
      "items_count": 5,
      "total_liters": 200.0
    }
  ],
  "receipts": [
    {
      "receipt_id": "receipt-uuid-101",
      "receipt_number": "RCP-1730468456-xyz",
      "date": "2026-11-01",
      "amount": 40000.00,
      "payment_method": "upi",
      "reference_number": "UPI12345678"
    }
  ],
  "verification": {
    "verified": false,
    "verified_by": null,
    "verified_at": null,
    "call_notes": null,
    "second_pitch_status": null
  }
}
```

**Use Case:** Detailed visit review before verification call.

---

### 11. Verification Summary

**Purpose:** Get monthly verification statistics.

**Endpoint:** `GET /api/v1/manager/verification/verification-summary`

**Query Parameters:**
- `month_year` (required): Format `YYYY-MM`

**Request:**
```
GET /api/v1/manager/verification/verification-summary?month_year=2026-11
Authorization: Bearer <token>
```

**Response:**
```json
{
  "month_year": "2026-11",
  "summary": {
    "total_visits": 320,
    "verified_visits": 285,
    "pending_verification": 35,
    "disputed_visits": 5,
    "verification_rate": 89.06,
    "avg_verification_time_hours": 36.5
  },
  "second_pitch_results": {
    "not_pitched": 50,
    "pitched_interested": 80,
    "pitched_follow_up": 45,
    "pitched_converted": 110
  },
  "by_field_officer": [
    {
      "field_officer": {
        "email": "amit.sharma@paruchemicals.com",
        "name": "Amit Sharma"
      },
      "total_visits": 45,
      "verified": 42,
      "pending": 3,
      "verification_rate": 93.33
    }
  ]
}
```

**Use Case:** Verification performance tracking.

---

### 12. Field Officers List

**Purpose:** Get list of all field officers with current month performance.

**Endpoint:** `GET /api/v1/manager/officers/list`

**Query Parameters:**
- `month_year` (optional): Format `YYYY-MM`, defaults to current month

**Request:**
```
GET /api/v1/manager/officers/list?month_year=2026-11
Authorization: Bearer <token>
```

**Response:**
```json
{
  "field_officers": [
    {
      "user_id": "user-uuid-1",
      "email": "amit.sharma@paruchemicals.com",
      "name": "Amit Sharma",
      "mobile": "9876543200",
      "role": "field_officer",
      "is_active": true,
      "current_month_stats": {
        "total_visits": 45,
        "total_orders": 32,
        "total_sales": 540000.00,
        "total_collections": 480000.00,
        "conversion_rate": 71.11
      },
      "targets": {
        "target_amount": 600000.00,
        "target_liters": 6000.0,
        "target_visits": 50,
        "achievement_percent": 90.00
      }
    },
    {
      "user_id": "user-uuid-2",
      "email": "priya.singh@paruchemicals.com",
      "name": "Priya Singh",
      "mobile": "9876543201",
      "role": "field_officer",
      "is_active": true,
      "current_month_stats": {
        "total_visits": 52,
        "total_orders": 28,
        "total_sales": 420000.00,
        "total_collections": 390000.00,
        "conversion_rate": 53.85
      },
      "targets": {
        "target_amount": 500000.00,
        "target_liters": 5000.0,
        "target_visits": 60,
        "achievement_percent": 84.00
      }
    }
  ],
  "count": 10
}
```

**Use Case:** Team management and FO selection dropdowns.

---

### 13. Set Monthly Targets

**Purpose:** Manager sets monthly targets for a field officer.

**Endpoint:** `POST /api/v1/manager/officers/targets/set`

**Request Body:**
```json
{
  "user_email": "amit.sharma@paruchemicals.com",
  "month_year": "2026-12",
  "target_amount": 650000.00,
  "target_liters": 6500.0,
  "target_visits": 55,
  "set_by_manager_email": "manager@paruchemicals.com"
}
```

**Response:**
```json
{
  "success": true,
  "target_id": "target-uuid-456",
  "target": {
    "user_email": "amit.sharma@paruchemicals.com",
    "month_year": "2026-12",
    "target_amount": 650000.00,
    "target_liters": 6500.0,
    "target_visits": 55,
    "set_by": "manager@paruchemicals.com",
    "set_at": "2026-11-03T16:00:00Z"
  },
  "notification_sent": true
}
```

**Use Case:** Monthly target setting workflow.

---

### 14. Get Target & Achievement

**Purpose:** Get target and current achievement for a field officer.

**Endpoint:** `GET /api/v1/manager/officers/targets/{email}/{month}`

**Path Parameters:**
- `email`: Field officer email
- `month`: Format `YYYY-MM`

**Request:**
```
GET /api/v1/manager/officers/targets/amit.sharma@paruchemicals.com/2026-11
Authorization: Bearer <token>
```

**Response:**
```json
{
  "user_email": "amit.sharma@paruchemicals.com",
  "month_year": "2026-11",
  "targets": {
    "target_amount": 600000.00,
    "target_liters": 6000.0,
    "target_visits": 50
  },
  "achievement": {
    "achieved_amount": 540000.00,
    "achieved_liters": 5400.0,
    "achieved_visits": 45,
    "amount_shortfall": 60000.00,
    "liters_shortfall": 600.0,
    "visits_shortfall": 5,
    "amount_percent": 90.00,
    "liters_percent": 90.00,
    "visits_percent": 90.00
  },
  "days_remaining": 15,
  "set_by": "manager@paruchemicals.com",
  "set_at": "2026-11-01T08:00:00Z"
}
```

**Use Case:** Performance tracking and progress monitoring.

---

## 📞 Caller APIs

### 1. Customer List

**Purpose:** Get list of all customers for calling campaigns.

**Endpoint:** `GET /api/v1/customers/list`

**Query Parameters:**
- `search` (optional): Search by name or mobile
- `village` (optional): Filter by village
- `customer_type` (optional): `retailer` or `distributor`
- `limit` (optional): Default `50`
- `offset` (optional): Default `0`

**Request:**
```
GET /api/v1/customers/list?limit=50&customer_type=retailer
Authorization: Bearer <token>
```

**Response:**
```json
{
  "customers": [
    {
      "customer_id": "cust-uuid-1",
      "name": "Raj Traders",
      "contact_person": "Rajesh Kumar",
      "mobile": "9876543210",
      "alternate_mobile": "9876543211",
      "customer_type": "retailer",
      "village": "Kothrud",
      "city": "Pune",
      "last_visit_date": "2026-11-01",
      "last_order_date": "2026-11-01",
      "last_order_amount": 45000.00,
      "total_orders": 12,
      "total_sales": 540000.00
    },
    {
      "customer_id": "cust-uuid-2",
      "name": "Gupta Distributors",
      "contact_person": "Suresh Gupta",
      "mobile": "9876543220",
      "alternate_mobile": null,
      "customer_type": "distributor",
      "village": "Shivaji Nagar",
      "city": "Pune",
      "last_visit_date": "2026-10-28",
      "last_order_date": "2026-10-25",
      "last_order_amount": 80000.00,
      "total_orders": 8,
      "total_sales": 640000.00
    }
  ],
  "total_count": 156,
  "count": 2
}
```

**Use Case:** Calling campaign list, customer selection for outbound calls.

---

### 2. Customer Visit History

**Purpose:** Get complete visit history for a customer.

**Endpoint:** `GET /api/v1/customers/{customer_id}/visits`

**Query Parameters:**
- `limit` (optional): Default `20`

**Request:**
```
GET /api/v1/customers/cust-uuid-1/visits?limit=20
Authorization: Bearer <token>
```

**Response:**
```json
{
  "customer": {
    "customer_id": "cust-uuid-1",
    "name": "Raj Traders",
    "mobile": "9876543210"
  },
  "visits": [
    {
      "visit_id": "visit-uuid-1",
      "date": "2026-11-01",
      "field_officer": {
        "name": "Amit Sharma",
        "mobile": "9876543200"
      },
      "check_in_time": "2026-11-01T09:10:00Z",
      "check_out_time": "2026-11-01T09:45:00Z",
      "duration_minutes": 35,
      "notes": "Discussed new product requirements.",
      "order_created": true,
      "order_amount": 45000.00
    },
    {
      "visit_id": "visit-uuid-2",
      "date": "2026-10-15",
      "field_officer": {
        "name": "Amit Sharma",
        "mobile": "9876543200"
      },
      "check_in_time": "2026-10-15T10:30:00Z",
      "check_out_time": "2026-10-15T11:00:00Z",
      "duration_minutes": 30,
      "notes": "Regular monthly visit.",
      "order_created": true,
      "order_amount": 35000.00
    }
  ],
  "total_visits": 24,
  "count": 2
}
```

**Use Case:** Before calling customer - review visit history.

---

### 3. Customer Order History

**Purpose:** Get complete order history for a customer.

**Endpoint:** `GET /api/v1/customers/{customer_id}/orders`

**Query Parameters:**
- `limit` (optional): Default `20`

**Request:**
```
GET /api/v1/customers/cust-uuid-1/orders?limit=20
Authorization: Bearer <token>
```

**Response:**
```json
{
  "customer": {
    "customer_id": "cust-uuid-1",
    "name": "Raj Traders"
  },
  "orders": [
    {
      "order_id": "order-uuid-1",
      "order_number": "ORD-1730468123-abc",
      "date": "2026-11-01",
      "field_officer": {
        "name": "Amit Sharma"
      },
      "gross_amount": 50000.00,
      "discount_amount": 5000.00,
      "net_amount": 45000.00,
      "discount_percent": 10.0,
      "total_liters": 200.0,
      "items": [
        {
          "product_name": "Parul Super Finish 20L",
          "quantity": 10,
          "unit_price": 1200.00,
          "total": 12000.00
        }
      ]
    }
  ],
  "total_orders": 12,
  "total_sales": 540000.00,
  "count": 1
}
```

**Use Case:** Before calling customer - review order history and suggest reorder.

---

### 4. Log Call Activity

**Purpose:** Caller logs outbound call details.

**Endpoint:** `POST /api/v1/customers/calls/log`

**Request Body:**
```json
{
  "customer_id": "cust-uuid-1",
  "caller_email": "caller@paruchemicals.com",
  "call_date": "2026-11-03",
  "call_outcome": "interested",
  "call_notes": "Customer interested in new product. Requested FO visit next week.",
  "follow_up_required": true,
  "follow_up_date": "2026-11-10"
}
```

**Call Outcome Values:**
- `interested` - Customer showed interest
- `not_interested` - Customer not interested
- `call_later` - Call back later
- `wrong_number` - Wrong number
- `not_reachable` - Number not reachable

**Response:**
```json
{
  "success": true,
  "call_log_id": "call-uuid-123",
  "call_log": {
    "customer_id": "cust-uuid-1",
    "caller_email": "caller@paruchemicals.com",
    "call_date": "2026-11-03",
    "call_outcome": "interested",
    "call_notes": "Customer interested in new product. Requested FO visit next week.",
    "follow_up_required": true,
    "follow_up_date": "2026-11-10",
    "logged_at": "2026-11-03T15:45:00Z"
  },
  "notification_sent_to_fo": true
}
```

**Use Case:** Call logging and follow-up creation.

---

### 5. Today's Calling List

**Purpose:** Get list of customers to call today (based on last visit date and call history).

**Endpoint:** `GET /api/v1/customers/calls/today`

**Request:**
```
GET /api/v1/customers/calls/today
Authorization: Bearer <token>
```

**Response:**
```json
{
  "calling_list": [
    {
      "customer_id": "cust-uuid-1",
      "name": "Raj Traders",
      "mobile": "9876543210",
      "village": "Kothrud",
      "last_visit_date": "2026-10-01",
      "days_since_visit": 33,
      "last_order_amount": 45000.00,
      "last_call_date": null,
      "priority": "high",
      "reason": "No visit in 30+ days"
    },
    {
      "customer_id": "cust-uuid-2",
      "name": "Sharma Enterprises",
      "mobile": "9876543230",
      "village": "Pimpri",
      "last_visit_date": "2026-10-25",
      "days_since_visit": 9,
      "last_order_amount": 25000.00,
      "last_call_date": "2026-10-30",
      "last_call_outcome": "call_later",
      "priority": "medium",
      "reason": "Follow-up from previous call"
    }
  ],
  "total_count": 25
}
```

**Priority Logic:**
- **High**: No visit/call in 30+ days
- **Medium**: Follow-up required or 15-30 days
- **Low**: 7-15 days

**Use Case:** Daily calling campaign list for callers.

---

## 📦 Data Models

### User Object
```typescript
interface User {
  user_id: string;
  email: string;
  name: string;
  mobile: string;
  role: 'manager' | 'field_officer' | 'caller';
  is_active: boolean;
}
```

### Customer Object
```typescript
interface Customer {
  customer_id: string;
  name: string;
  contact_person: string;
  mobile: string;
  alternate_mobile?: string;
  customer_type: 'retailer' | 'distributor';
  village: string;
  city: string;
  address?: string;
  gst_number?: string;
}
```

### Order Object
```typescript
interface Order {
  order_id: string;
  order_number: string;
  date: string; // ISO 8601
  customer_id: string;
  field_officer_email: string;
  gross_amount: number;
  discount_amount: number;
  net_amount: number;
  discount_percent: number;
  total_liters: number;
  items: OrderItem[];
}

interface OrderItem {
  product_id: string;
  product_name: string;
  quantity: number;
  unit_price: number;
  catalog_price: number;
  selling_price: number;
  discount_per_unit: number;
  line_total: number;
}
```

### Visit Object
```typescript
interface Visit {
  visit_id: string;
  date: string;
  customer_id: string;
  field_officer_email: string;
  check_in_time: string; // ISO 8601
  check_out_time: string;
  duration_minutes: number;
  check_in_lat: number;
  check_in_lon: number;
  notes: string;
  photo_count: number;
  verified: boolean;
  verified_by?: string;
  verified_at?: string;
  call_notes?: string;
  second_pitch_status?: 'not_pitched' | 'pitched_interested' | 'pitched_follow_up' | 'pitched_converted';
}
```

### Route Plan Object
```typescript
interface RoutePlan {
  plan_id: string;
  date: string;
  field_officer_email: string;
  status: 'draft' | 'submitted' | 'completed';
  submission_time?: string;
  items: RoutePlanItem[];
}

interface RoutePlanItem {
  sequence: number;
  customer_id: string;
  customer_name: string;
  village: string;
  planned_time: string;
  status: 'pending' | 'completed' | 'skipped';
}
```

---

## ⚠️ Error Handling

### Error Response Format
```json
{
  "error": true,
  "message": "Descriptive error message",
  "code": "ERROR_CODE",
  "details": {}
}
```

### Common Error Codes

| HTTP Code | Error Code | Message | Action |
|-----------|------------|---------|--------|
| 401 | `UNAUTHORIZED` | Invalid or expired token | Re-authenticate |
| 403 | `FORBIDDEN` | Insufficient permissions | Check user role |
| 404 | `NOT_FOUND` | Resource not found | Verify ID/email |
| 400 | `INVALID_REQUEST` | Missing required fields | Check request body |
| 422 | `VALIDATION_ERROR` | Validation failed | Check field formats |
| 429 | `RATE_LIMIT` | Too many requests | Retry after delay |
| 500 | `INTERNAL_ERROR` | Server error | Contact support |

### Example Error Responses

**401 Unauthorized:**
```json
{
  "error": true,
  "message": "Invalid or expired token",
  "code": "UNAUTHORIZED"
}
```

**403 Forbidden:**
```json
{
  "error": true,
  "message": "User does not have manager role",
  "code": "FORBIDDEN"
}
```

**404 Not Found:**
```json
{
  "error": true,
  "message": "Visit not found",
  "code": "NOT_FOUND",
  "details": {
    "visit_id": "visit-uuid-123"
  }
}
```

**400 Bad Request:**
```json
{
  "error": true,
  "message": "Missing required field: month_year",
  "code": "INVALID_REQUEST"
}
```

---

## 💻 Code Examples

### JavaScript/TypeScript (React/Next.js)

#### 1. Authentication Flow

```typescript
// Step 1: Authenticate and get token
async function authenticateManager(email: string, apiKey: string) {
  try {
    const response = await fetch('https://fom-1.onrender.com/api/v1/manager/auth/validate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        email: email,
        api_key: apiKey
      })
    });

    if (!response.ok) {
      throw new Error('Authentication failed');
    }

    const data = await response.json();
    
    if (data.valid) {
      // Store token in localStorage or secure cookie
      localStorage.setItem('aura_token', data.token);
      localStorage.setItem('aura_user', JSON.stringify(data.manager));
      return data;
    } else {
      throw new Error(data.error);
    }
  } catch (error) {
    console.error('Authentication error:', error);
    throw error;
  }
}

// Step 2: Use token in API calls
async function fetchWithAuth(url: string, options: RequestInit = {}) {
  const token = localStorage.getItem('aura_token');
  
  if (!token) {
    throw new Error('No authentication token found');
  }

  const headers = {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
    ...options.headers
  };

  const response = await fetch(url, {
    ...options,
    headers
  });

  // Handle token expiry
  if (response.status === 401) {
    // Clear token and redirect to login
    localStorage.removeItem('aura_token');
    window.location.href = '/login';
    throw new Error('Session expired');
  }

  return response;
}
```

#### 2. Get Dashboard Data

```typescript
interface DashboardData {
  month_year: string;
  kpis: {
    total_orders: number;
    total_sales: number;
    total_collections: number;
    conversion_rate: number;
  };
  alerts: {
    pending_verifications: number;
    high_discount_orders: number;
  };
}

async function getDashboard(monthYear: string): Promise<DashboardData> {
  const response = await fetchWithAuth(
    `https://fom-1.onrender.com/api/v1/manager/dashboard/overview?month_year=${monthYear}`
  );

  if (!response.ok) {
    throw new Error('Failed to fetch dashboard data');
  }

  return response.json();
}

// Usage in React component
function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getDashboard('2026-11')
      .then(data => {
        setData(data);
        setLoading(false);
      })
      .catch(error => {
        console.error('Error:', error);
        setLoading(false);
      });
  }, []);

  if (loading) return <div>Loading...</div>;
  if (!data) return <div>Error loading dashboard</div>;

  return (
    <div>
      <h1>Dashboard - {data.month_year}</h1>
      <div>Total Sales: ₹{data.kpis.total_sales.toLocaleString()}</div>
      <div>Total Orders: {data.kpis.total_orders}</div>
      <div>Conversion Rate: {data.kpis.conversion_rate}%</div>
    </div>
  );
}
```

#### 3. Verify Visit (Second Pitch)

```typescript
interface VerifyVisitRequest {
  visit_id: string;
  manager_email: string;
  verified: boolean;
  call_notes: string;
  second_pitch_status: 'not_pitched' | 'pitched_interested' | 'pitched_follow_up' | 'pitched_converted';
}

async function verifyVisit(data: VerifyVisitRequest) {
  const response = await fetchWithAuth(
    'https://fom-1.onrender.com/api/v1/manager/verification/verify',
    {
      method: 'POST',
      body: JSON.stringify(data)
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.message);
  }

  return response.json();
}

// Usage
async function handleVerify(visitId: string, callNotes: string, interested: boolean) {
  try {
    const result = await verifyVisit({
      visit_id: visitId,
      manager_email: 'manager@paruchemicals.com',
      verified: true,
      call_notes: callNotes,
      second_pitch_status: interested ? 'pitched_interested' : 'not_pitched'
    });

    if (result.success) {
      alert('Visit verified successfully!');
      if (result.follow_up_created) {
        alert('Follow-up task created for field officer');
      }
    }
  } catch (error) {
    alert('Error: ' + error.message);
  }
}
```

#### 4. Get Discount Analytics

```typescript
async function getDiscountAnalytics(monthYear: string, threshold: number = 10) {
  const response = await fetchWithAuth(
    `https://fom-1.onrender.com/api/v1/manager/analytics/discounts?month_year=${monthYear}&threshold_percent=${threshold}`
  );

  if (!response.ok) {
    throw new Error('Failed to fetch discount analytics');
  }

  return response.json();
}

// Usage
function DiscountAlerts() {
  const [data, setData] = useState(null);

  useEffect(() => {
    getDiscountAnalytics('2026-11', 10)
      .then(data => setData(data))
      .catch(error => console.error(error));
  }, []);

  return (
    <div>
      <h2>High Discount Orders ({data?.high_discount_orders?.length})</h2>
      {data?.high_discount_orders.map(order => (
        <div key={order.order_id} className={order.alert_level}>
          <span>{order.customer}</span>
          <span>{order.discount_percent}%</span>
          <span>₹{order.order_total}</span>
          {order.needs_approval && <span>⚠️ Needs Approval</span>}
        </div>
      ))}
    </div>
  );
}
```

---

## 🔒 Security Best Practices

### 1. Store Tokens Securely
```typescript
// ✅ GOOD: Use httpOnly cookies (server-side)
res.cookie('aura_token', token, {
  httpOnly: true,
  secure: true,
  sameSite: 'strict',
  maxAge: 8 * 60 * 60 * 1000 // 8 hours
});

// ⚠️ ACCEPTABLE: localStorage (client-side only)
localStorage.setItem('aura_token', token);

// ❌ BAD: Never expose in URL
// https://pc-sales.vercel.app/dashboard?token=abc123
```

### 2. Handle Token Expiry
```typescript
async function apiCall(url: string) {
  let response = await fetchWithAuth(url);
  
  if (response.status === 401) {
    // Try to refresh token
    const refreshed = await refreshToken();
    if (refreshed) {
      // Retry original request
      response = await fetchWithAuth(url);
    } else {
      // Redirect to login
      window.location.href = '/login';
    }
  }
  
  return response;
}
```

### 3. Never Expose API Key in Frontend
```typescript
// ❌ BAD: Hardcoded in frontend
const API_KEY = 'AURA_MANAGER_SECRET_2026';

// ✅ GOOD: Use environment variable on server
const API_KEY = process.env.AURA_API_KEY;

// ✅ GOOD: Authenticate on backend, pass token to frontend
// Backend route:
app.post('/api/authenticate', async (req, res) => {
  const { email } = req.body;
  const token = await authenticateWithAura(email, process.env.AURA_API_KEY);
  res.json({ token });
});
```

### 4. Rate Limiting
```typescript
// Implement client-side rate limiting
class RateLimiter {
  private calls: number[] = [];
  private limit: number;
  private window: number;

  constructor(limit: number, windowMs: number) {
    this.limit = limit;
    this.window = windowMs;
  }

  async throttle<T>(fn: () => Promise<T>): Promise<T> {
    const now = Date.now();
    this.calls = this.calls.filter(time => now - time < this.window);

    if (this.calls.length >= this.limit) {
      const waitTime = this.window - (now - this.calls[0]);
      await new Promise(resolve => setTimeout(resolve, waitTime));
    }

    this.calls.push(Date.now());
    return fn();
  }
}

// Usage: Max 10 calls per minute
const limiter = new RateLimiter(10, 60000);
await limiter.throttle(() => getDashboard('2026-11'));
```

---

## 🎯 Quick Start Checklist

### For Manager Module:
- [ ] Authenticate manager and get JWT token
- [ ] Display dashboard overview with KPIs
- [ ] Show pending verifications list
- [ ] Implement second pitch verification workflow
- [ ] Display discount analytics with alerts
- [ ] Show plan vs actual comparison
- [ ] Implement monthly target setting
- [ ] Show team performance summary

### For Caller Module:
- [ ] Authenticate caller and get JWT token
- [ ] Display today's calling list
- [ ] Show customer details before call
- [ ] Implement call logging workflow
- [ ] Create follow-up tasks for field officers
- [ ] Show customer visit/order history

---

## 📞 Support

**API Issues:** backend-support@paruchemicals.com  
**Integration Help:** developers@paruchemicals.com  
**Documentation:** https://fom-1.onrender.com/docs  

---

**Document Version:** 1.0.0  
**Last Updated:** November 1, 2026  
**Status:** Production Ready ✅
