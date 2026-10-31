# AURA v2.0 Architecture Reference

## 🎯 Core Architectural Principles

### 1. **Zero Database Coupling**
❌ **Old (v1.0):** AURA → PC-Sales PostgreSQL (foreign keys, duplicate data)  
✅ **New (v2.0):** AURA Supabase is fully self-contained, PC-Sales queries via REST API

### 2. **Email-Based Hierarchy**
❌ **Old:** `manager_id INTEGER` (cross-database FK nightmare)  
✅ **New:** `manager_email TEXT` (simple string matching, no FK constraints)

### 3. **Direct Manager Access**
❌ **Old:** Manager logs into deprecated fom-kappa.vercel.app admin portal  
✅ **New:** Manager uses pc-sales.vercel.app, queries AURA via CORS + API key

---

## 🗄️ Database Schema Comparison

### Products Table

**v1.0 (products_cache):**
```sql
product_id INTEGER PRIMARY KEY
product_name TEXT
price REAL
```

**v2.0 (products):**
```sql
id TEXT PRIMARY KEY
sku_code TEXT UNIQUE
product_name TEXT
packing_type TEXT
capacity_ltr REAL
standard_rate REAL
rate_gujarat REAL
rate_maharashtra REAL
rate_mp REAL
is_active INTEGER
```

### Monthly Targets

**v1.0:**
```sql
assigned_by_manager_id INTEGER -- FK to PC-Sales app_users.user_id
```

**v2.0:**
```sql
set_by_manager_email TEXT -- Email of Manager on pc-sales.vercel.app
```

### Sales Orders

**v1.0:**
```sql
pc_sales_sale_id INTEGER -- FK to PC-Sales sales.sale_id
status TEXT -- 'submitted', 'synced_to_pcsales', 'approved'
```

**v2.0:**
```sql
order_number TEXT UNIQUE -- Self-contained reference
-- No pc_sales_sale_id (zero coupling)
```

### Payment Receipts

**v1.0:**
```sql
receipt_no TEXT
pc_sales_payment_id INTEGER -- FK to PC-Sales payments.payment_id
```

**v2.0:**
```sql
receipt_number TEXT UNIQUE -- Renamed for consistency
-- No pc_sales_payment_id (zero coupling)
```

### Customer Visits

**v2.0 Additions:**
```sql
verification_status TEXT DEFAULT 'pending'
manager_verified_at TIMESTAMPTZ
manager_verified_by TEXT -- Manager email
manager_call_notes TEXT
second_pitch_status TEXT
```

---

## 🔄 Data Flow (v2.0)

### Field Officer → AURA
```
Mobile App (SQLite) 
  ↓ [Two-tier sync: FastAPI → Supabase]
AURA Cloud (Supabase PostgreSQL)
```

### Manager → AURA
```
PC-Sales Frontend (pc-sales.vercel.app)
  ↓ [CORS + x-user-email + X-Aura-Api-Key]
AURA Backend (fom-1.onrender.com/api/v1/manager/*)
  ↓
AURA Cloud (Supabase PostgreSQL)
```

### No More PC-Sales Coupling
```
❌ AURA → PC-Sales PostgreSQL (eliminated)
❌ Duplicate orders/receipts in PC-Sales (eliminated)
❌ Cross-database foreign keys (eliminated)
```

---

## 🔐 Authentication & Authorization

### Field Officer (Mobile App)
- **Method:** JWT token from AURA Supabase Auth
- **Storage:** Expo SecureStore
- **Header:** `Authorization: Bearer <jwt_token>`

### Manager (PC-Sales Web)
- **Method:** Email + AURA API Key
- **Headers:**
  ```
  x-user-email: manager@example.com
  X-Aura-Api-Key: <shared_secret>
  ```
- **CORS Origins:**
  - `https://pc-sales.vercel.app`
  - `http://localhost:5173` (dev)

---

## 📡 Manager Bridge API Endpoints

### Base URL
```
https://fom-1.onrender.com/api/v1/manager
```

### Endpoints

#### 1. Assign Field Officers
```http
POST /api/v1/manager/assign-officers
Content-Type: application/json
x-user-email: manager@example.com
X-Aura-Api-Key: <secret>

{
  "manager_email": "manager@example.com",
  "officer_emails": ["fo1@example.com", "fo2@example.com"]
}
```

#### 2. Set Monthly Target
```http
POST /api/v1/manager/targets
{
  "user_email": "fo@example.com",
  "month_year": "2026-11",
  "target_amount": 500000,
  "target_liters": 10000,
  "target_visits": 150,
  "set_by_manager_email": "manager@example.com"
}
```

#### 3. Get Plan vs. Actual
```http
GET /api/v1/manager/{manager_email}/plan-vs-actual?date=2026-10-31

Response:
{
  "field_officers": [
    {
      "email": "fo@example.com",
      "name": "John Doe",
      "plan": { ... },
      "plan_items": [ ... ],
      "actual_visits": [ ... ],
      "edit_history": [ ... ]
    }
  ]
}
```

#### 4. Get Discount Analytics
```http
GET /api/v1/manager/{manager_email}/discounts?month=2026-11

Response:
{
  "field_officers": [
    {
      "email": "fo@example.com",
      "orders": [
        {
          "order_number": "ORD-20261031-001",
          "gross_amount": 10000,
          "total_discount_amount": 500,
          "discount_percentage": 5.0,
          "items": [ ... ]
        }
      ],
      "monthly_totals": {
        "total_orders": 25,
        "total_gross": 250000,
        "total_discount": 12500,
        "discount_percentage": 5.0
      }
    }
  ]
}
```

#### 5. Verify Visit
```http
PATCH /api/v1/manager/visits/{visit_id}/verify
{
  "manager_email": "manager@example.com",
  "verified": true,
  "call_notes": "Spoke with farmer, confirmed visit and pitched new 20L steel barni",
  "second_pitch_status": "pitched_interested"
}
```

#### 6. Get Edit Audit Logs
```http
GET /api/v1/manager/audit/edit-logs?user_email=fo@example.com&start_date=2026-11-01&end_date=2026-11-30

Response:
{
  "logs": [
    {
      "id": "log-123",
      "entity_type": "sales_order",
      "entity_id": "order-456",
      "revision_number": 2,
      "edit_reason": "Customer requested quantity change from 2 to 4 units",
      "previous_payload": { ... },
      "new_payload": { ... },
      "edited_at": "2026-11-15T10:30:00Z"
    }
  ]
}
```

---

## 🎨 Manager UI Integration (PC-Sales)

### Example: React Component Fetching AURA Data

```typescript
// pc-sales/src/hooks/useAuraData.ts
import { useAuth } from '@/contexts/AuthContext';

const AURA_API_URL = 'https://fom-1.onrender.com/api/v1/manager';
const AURA_API_KEY = process.env.NEXT_PUBLIC_AURA_API_KEY;

export function useAuraFieldOfficers() {
  const { user } = useAuth(); // Manager's auth context
  
  return useQuery({
    queryKey: ['aura-officers', user.email],
    queryFn: async () => {
      const response = await fetch(
        `${AURA_API_URL}/${user.email}/officers`,
        {
          headers: {
            'x-user-email': user.email,
            'X-Aura-Api-Key': AURA_API_KEY,
          },
        }
      );
      return response.json();
    },
  });
}

export function useAuraPlanVsActual(date: string) {
  const { user } = useAuth();
  
  return useQuery({
    queryKey: ['aura-plan-vs-actual', user.email, date],
    queryFn: async () => {
      const response = await fetch(
        `${AURA_API_URL}/${user.email}/plan-vs-actual?date=${date}`,
        {
          headers: {
            'x-user-email': user.email,
            'X-Aura-Api-Key': AURA_API_KEY,
          },
        }
      );
      return response.json();
    },
  });
}
```

### Example: Manager Dashboard Component

```typescript
// pc-sales/src/app/(manager)/field-team/page.tsx
import { useAuraFieldOfficers, useAuraPlanVsActual } from '@/hooks/useAuraData';

export default function FieldTeamDashboard() {
  const { data: officers } = useAuraFieldOfficers();
  const today = new Date().toISOString().split('T')[0];
  const { data: planData } = useAuraPlanVsActual(today);

  return (
    <div>
      <h1>Field Team Overview</h1>
      {officers?.map((officer) => (
        <div key={officer.email}>
          <h2>{officer.name}</h2>
          <p>Email: {officer.email}</p>
          <p>Assigned Districts: {officer.assigned_districts}</p>
        </div>
      ))}
      
      <h2>Today's Plan vs. Actual</h2>
      {planData?.field_officers.map((fo) => (
        <div key={fo.email}>
          <h3>{fo.name}</h3>
          <p>Planned Visits: {fo.plan_items.length}</p>
          <p>Actual Visits: {fo.actual_visits.length}</p>
          {fo.plan.is_edited && (
            <p className="text-warning">
              Plan Edited (Rev {fo.plan.revision_number}): {fo.plan.last_edit_reason}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}
```

---

## 📱 Mobile App Changes

### Key Files Modified

1. **Database Schema**
   - `src/db/database.ts` - Updated with v2.0 tables
   - `src/db/migrations/v2_architecture_update.sql` - Migration script

2. **Type Definitions**
   - `src/types/aura-v2.ts` - All v2.0 interfaces

3. **Stores**
   - `src/store/routePlanStore.ts` - NEW: Route planning logic
   - `src/store/visitStore.ts` - Enhanced checkout validation

4. **Screens**
   - `app/(tabs)/plan.tsx` - NEW: Route plan view
   - `app/plan/create.tsx` - NEW: Plan creation
   - `app/(tabs)/orders.tsx` - NEW: Orders & stock view

5. **Navigation**
   - `app/(tabs)/_layout.tsx` - FO-only tabs, removed team/map

---

## 🚀 Deployment Checklist

### AURA Backend (FastAPI)
- [ ] Add CORS origins: `pc-sales.vercel.app`, `localhost:5173`
- [ ] Implement Manager Bridge API endpoints (`/api/v1/manager/*`)
- [ ] Set up `X-Aura-Api-Key` shared secret (environment variable)
- [ ] Deploy to Render with updated dependencies

### AURA Supabase
- [ ] Run migration script (v2_architecture_update.sql)
- [ ] Enable Row Level Security (RLS) policies
- [ ] Create indexes for manager_email columns
- [ ] Initialize 13 products via SQL

### PC-Sales Frontend
- [ ] Store `NEXT_PUBLIC_AURA_API_KEY` in environment variables
- [ ] Implement React hooks for AURA data fetching
- [ ] Build Manager dashboard components
- [ ] Add AURA-specific routes under `/(manager)/field-team`

### Mobile App
- [ ] Run database migration on user devices (check schema version)
- [ ] Test offline → online sync with new tables
- [ ] Verify photo upload with new checkout validation
- [ ] Test route plan submission → check-in lock flow

---

**Last Updated:** 2024-10-31  
**Architecture Version:** 2.0  
**Document Owner:** AURA Development Team
