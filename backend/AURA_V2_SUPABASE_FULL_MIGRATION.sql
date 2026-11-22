-- ============================================================
-- AURA Mobile v2.0 - Complete Supabase Migration
-- Version: 2.0.0
-- Date: November 1, 2026
-- 
-- Run this in Supabase SQL Editor to create all required tables
-- for Field Officer Mobile App + Manager Bridge APIs
-- ============================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- 1. USERS TABLE (Core Authentication)
-- ============================================================

CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    mobile TEXT,
    role TEXT NOT NULL CHECK (role IN ('field_officer', 'manager', 'caller', 'admin', 'hr')),
    manager_email TEXT, -- Email of manager (for field officers)
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON public.users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON public.users(role);
CREATE INDEX IF NOT EXISTS idx_users_manager_email ON public.users(manager_email);

COMMENT ON TABLE public.users IS 'User accounts for all roles';
COMMENT ON COLUMN public.users.manager_email IS 'Email of the manager (for field officers)';

-- ============================================================
-- 2. CUSTOMERS TABLE (Retailers/Distributors)
-- ============================================================

CREATE TABLE IF NOT EXISTS public.customers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    contact_person TEXT,
    mobile TEXT NOT NULL,
    alternate_mobile TEXT,
    customer_type TEXT NOT NULL CHECK (customer_type IN ('retailer', 'distributor')),
    village TEXT NOT NULL,
    city TEXT,
    address TEXT,
    pincode TEXT,
    state TEXT,
    gst_number TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_customers_name ON public.customers(name);
CREATE INDEX IF NOT EXISTS idx_customers_mobile ON public.customers(mobile);
CREATE INDEX IF NOT EXISTS idx_customers_village ON public.customers(village);
CREATE INDEX IF NOT EXISTS idx_customers_type ON public.customers(customer_type);
CREATE INDEX IF NOT EXISTS idx_customers_location ON public.customers(latitude, longitude);

COMMENT ON TABLE public.customers IS 'Retailer and distributor customer records';

-- ============================================================
-- 3. PRODUCTS TABLE (Self-contained catalog)
-- ============================================================

CREATE TABLE IF NOT EXISTS public.products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_code TEXT UNIQUE NOT NULL,
    product_name TEXT NOT NULL,
    brand TEXT NOT NULL DEFAULT 'standard',
    category TEXT NOT NULL,
    pack_size_liters NUMERIC(10, 2) NOT NULL,
    unit_price NUMERIC(12, 2) NOT NULL,
    mrp NUMERIC(12, 2),
    tax_rate NUMERIC(5, 2) NOT NULL DEFAULT 18.00,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_products_code ON public.products(product_code);
CREATE INDEX IF NOT EXISTS idx_products_brand ON public.products(brand);
CREATE INDEX IF NOT EXISTS idx_products_active ON public.products(is_active);

COMMENT ON TABLE public.products IS 'Product catalog (13 products)';

-- ============================================================
-- 4. FO_MONTHLY_TARGETS TABLE (Manager-set targets)
-- ============================================================

CREATE TABLE IF NOT EXISTS public.fo_monthly_targets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_email TEXT NOT NULL,
    month_year TEXT NOT NULL, -- Format: YYYY-MM
    target_amount NUMERIC(12, 2) NOT NULL DEFAULT 0,
    target_liters NUMERIC(12, 2) NOT NULL DEFAULT 0,
    target_visits INTEGER NOT NULL DEFAULT 0,
    monthly_discount_limit NUMERIC(12, 2) NOT NULL DEFAULT 0,
    set_by_manager_email TEXT,
    set_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_email, month_year)
);

CREATE INDEX IF NOT EXISTS idx_targets_user_email ON public.fo_monthly_targets(user_email);
CREATE INDEX IF NOT EXISTS idx_targets_month_year ON public.fo_monthly_targets(month_year);

COMMENT ON TABLE public.fo_monthly_targets IS 'Monthly targets set by managers for field officers';

-- ============================================================
-- 5. DAILY_ROUTE_PLANS TABLE (Daily route planning)
-- ============================================================

CREATE TABLE IF NOT EXISTS public.daily_route_plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_email TEXT NOT NULL,
    plan_date DATE NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'submitted', 'completed')),
    submission_time TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_email, plan_date)
);

CREATE INDEX IF NOT EXISTS idx_plans_user_email ON public.daily_route_plans(user_email);
CREATE INDEX IF NOT EXISTS idx_plans_date ON public.daily_route_plans(plan_date);
CREATE INDEX IF NOT EXISTS idx_plans_status ON public.daily_route_plans(status);

COMMENT ON TABLE public.daily_route_plans IS 'Daily route plans submitted by field officers';

-- ============================================================
-- 6. ROUTE_PLAN_ITEMS TABLE (Plan line items)
-- ============================================================

CREATE TABLE IF NOT EXISTS public.route_plan_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    plan_id UUID NOT NULL REFERENCES public.daily_route_plans(id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES public.customers(id),
    planned_sequence INTEGER NOT NULL,
    planned_time TEXT, -- HH:MM format
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'skipped')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_plan_items_plan_id ON public.route_plan_items(plan_id);
CREATE INDEX IF NOT EXISTS idx_plan_items_customer_id ON public.route_plan_items(customer_id);
CREATE INDEX IF NOT EXISTS idx_plan_items_sequence ON public.route_plan_items(planned_sequence);

COMMENT ON TABLE public.route_plan_items IS 'Individual items in route plans';

-- ============================================================
-- 7. ENTITY_EDIT_LOGS TABLE (Audit trail)
-- ============================================================

CREATE TABLE IF NOT EXISTS public.entity_edit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_type TEXT NOT NULL,
    entity_id UUID NOT NULL,
    field_officer_email TEXT NOT NULL,
    action_type TEXT NOT NULL,
    edit_reason TEXT NOT NULL,
    old_value JSONB,
    new_value JSONB,
    edit_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_edit_logs_entity_type ON public.entity_edit_logs(entity_type);
CREATE INDEX IF NOT EXISTS idx_edit_logs_entity_id ON public.entity_edit_logs(entity_id);
CREATE INDEX IF NOT EXISTS idx_edit_logs_user_email ON public.entity_edit_logs(field_officer_email);
CREATE INDEX IF NOT EXISTS idx_edit_logs_timestamp ON public.entity_edit_logs(edit_timestamp DESC);

COMMENT ON TABLE public.entity_edit_logs IS 'Audit trail for all entity edits';

-- ============================================================
-- 8. VISITS TABLE (Check-in/Check-out records)
-- ============================================================

CREATE TABLE IF NOT EXISTS public.visits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_email TEXT NOT NULL,
    customer_id UUID NOT NULL REFERENCES public.customers(id),
    visit_date DATE NOT NULL,
    check_in_time TIMESTAMPTZ NOT NULL,
    check_in_lat DOUBLE PRECISION NOT NULL,
    check_in_lon DOUBLE PRECISION NOT NULL,
    check_out_time TIMESTAMPTZ,
    check_out_lat DOUBLE PRECISION,
    check_out_lon DOUBLE PRECISION,
    duration_minutes INTEGER,
    notes TEXT,
    photo_urls TEXT[], -- Array of photo URLs
    was_planned BOOLEAN NOT NULL DEFAULT false,
    verified BOOLEAN NOT NULL DEFAULT false,
    verified_by TEXT, -- Manager email
    verified_at TIMESTAMPTZ,
    call_notes TEXT, -- Manager's call notes
    second_pitch_status TEXT CHECK (second_pitch_status IN ('not_pitched', 'pitched_interested', 'pitched_follow_up', 'pitched_converted')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_visits_user_email ON public.visits(user_email);
CREATE INDEX IF NOT EXISTS idx_visits_customer_id ON public.visits(customer_id);
CREATE INDEX IF NOT EXISTS idx_visits_date ON public.visits(visit_date);
CREATE INDEX IF NOT EXISTS idx_visits_verified ON public.visits(verified);
CREATE INDEX IF NOT EXISTS idx_visits_second_pitch ON public.visits(second_pitch_status);

COMMENT ON TABLE public.visits IS 'Field officer visit records (check-in/check-out)';
COMMENT ON COLUMN public.visits.verified IS 'Manager verification status';
COMMENT ON COLUMN public.visits.second_pitch_status IS 'Manager second pitch outcome';

-- ============================================================
-- 9. FO_SALES_ORDERS TABLE (Sales orders)
-- ============================================================

CREATE TABLE IF NOT EXISTS public.fo_sales_orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_number TEXT UNIQUE NOT NULL,
    order_date DATE NOT NULL,
    customer_id UUID NOT NULL REFERENCES public.customers(id),
    field_officer_email TEXT NOT NULL,
    visit_id UUID REFERENCES public.visits(id),
    gross_amount NUMERIC(12, 2) NOT NULL DEFAULT 0,
    discount_amount NUMERIC(12, 2) NOT NULL DEFAULT 0,
    net_amount NUMERIC(12, 2) NOT NULL DEFAULT 0,
    tax_amount NUMERIC(12, 2) NOT NULL DEFAULT 0,
    total_liters NUMERIC(12, 2) NOT NULL DEFAULT 0,
    discount_percent NUMERIC(5, 2) NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'confirmed', 'cancelled')),
    notes TEXT,
    revision_number INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_orders_number ON public.fo_sales_orders(order_number);
CREATE INDEX IF NOT EXISTS idx_orders_date ON public.fo_sales_orders(order_date);
CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON public.fo_sales_orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_fo_email ON public.fo_sales_orders(field_officer_email);
CREATE INDEX IF NOT EXISTS idx_orders_visit_id ON public.fo_sales_orders(visit_id);
CREATE INDEX IF NOT EXISTS idx_orders_discount_percent ON public.fo_sales_orders(discount_percent);

COMMENT ON TABLE public.fo_sales_orders IS 'Sales orders created by field officers';

-- ============================================================
-- 10. FO_SALES_ORDER_ITEMS TABLE (Order line items)
-- ============================================================

CREATE TABLE IF NOT EXISTS public.fo_sales_order_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id UUID NOT NULL REFERENCES public.fo_sales_orders(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES public.products(id),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(12, 2) NOT NULL,
    catalog_price NUMERIC(12, 2) NOT NULL,
    selling_price NUMERIC(12, 2) NOT NULL,
    discount_per_unit NUMERIC(12, 2) NOT NULL DEFAULT 0,
    line_total NUMERIC(12, 2) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON public.fo_sales_order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON public.fo_sales_order_items(product_id);

COMMENT ON TABLE public.fo_sales_order_items IS 'Line items for sales orders';

-- ============================================================
-- 11. FO_PAYMENT_RECEIPTS TABLE (Payment receipts)
-- ============================================================

CREATE TABLE IF NOT EXISTS public.fo_payment_receipts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    receipt_number TEXT UNIQUE NOT NULL,
    receipt_date DATE NOT NULL,
    customer_id UUID NOT NULL REFERENCES public.customers(id),
    field_officer_email TEXT NOT NULL,
    visit_id UUID REFERENCES public.visits(id),
    order_id UUID REFERENCES public.fo_sales_orders(id),
    amount NUMERIC(12, 2) NOT NULL CHECK (amount > 0),
    payment_method TEXT NOT NULL CHECK (payment_method IN ('cash', 'upi', 'cheque', 'rtgs_neft')),
    reference_number TEXT, -- UPI/Cheque/RTGS reference
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_receipts_number ON public.fo_payment_receipts(receipt_number);
CREATE INDEX IF NOT EXISTS idx_receipts_date ON public.fo_payment_receipts(receipt_date);
CREATE INDEX IF NOT EXISTS idx_receipts_customer_id ON public.fo_payment_receipts(customer_id);
CREATE INDEX IF NOT EXISTS idx_receipts_fo_email ON public.fo_payment_receipts(field_officer_email);
CREATE INDEX IF NOT EXISTS idx_receipts_payment_method ON public.fo_payment_receipts(payment_method);

COMMENT ON TABLE public.fo_payment_receipts IS 'Payment receipts collected by field officers';

-- ============================================================
-- 12. FO_STOCK_REQUESTS TABLE (Stock requisitions)
-- ============================================================

CREATE TABLE IF NOT EXISTS public.fo_stock_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    request_number TEXT UNIQUE NOT NULL,
    field_officer_email TEXT NOT NULL,
    request_date DATE NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'fulfilled', 'rejected')),
    requested_items JSONB NOT NULL, -- Array of {product_id, quantity}
    notes TEXT,
    approved_by TEXT, -- Manager email
    approved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_stock_requests_fo_email ON public.fo_stock_requests(field_officer_email);
CREATE INDEX IF NOT EXISTS idx_stock_requests_status ON public.fo_stock_requests(status);
CREATE INDEX IF NOT EXISTS idx_stock_requests_date ON public.fo_stock_requests(request_date);

COMMENT ON TABLE public.fo_stock_requests IS 'Stock requisition requests from field officers';

-- ============================================================
-- 13. FO_NOTIFICATIONS TABLE (Push notifications)
-- ============================================================

CREATE TABLE IF NOT EXISTS public.fo_notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_email TEXT NOT NULL,
    notification_type TEXT NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    data JSONB, -- Additional data
    is_read BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notifications_user_email ON public.fo_notifications(user_email);
CREATE INDEX IF NOT EXISTS idx_notifications_read ON public.fo_notifications(is_read);
CREATE INDEX IF NOT EXISTS idx_notifications_created ON public.fo_notifications(created_at DESC);

COMMENT ON TABLE public.fo_notifications IS 'Push notifications for field officers';

-- ============================================================
-- 14. FOLLOW_UPS TABLE (Auto-generated follow-up tasks)
-- ============================================================

CREATE TABLE IF NOT EXISTS public.follow_ups (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_email TEXT NOT NULL,
    customer_id UUID NOT NULL REFERENCES public.customers(id),
    visit_id UUID REFERENCES public.visits(id),
    follow_up_reason TEXT NOT NULL,
    due_date DATE NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'cancelled')),
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_followups_user_email ON public.follow_ups(user_email);
CREATE INDEX IF NOT EXISTS idx_followups_customer_id ON public.follow_ups(customer_id);
CREATE INDEX IF NOT EXISTS idx_followups_status ON public.follow_ups(status);
CREATE INDEX IF NOT EXISTS idx_followups_due_date ON public.follow_ups(due_date);

COMMENT ON TABLE public.follow_ups IS 'Follow-up tasks auto-generated from visit notes or manager calls';

-- ============================================================
-- 15. CALL_LOGS TABLE (Caller activity logs)
-- ============================================================

CREATE TABLE IF NOT EXISTS public.call_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID NOT NULL REFERENCES public.customers(id),
    caller_email TEXT NOT NULL,
    call_date DATE NOT NULL,
    call_outcome TEXT NOT NULL CHECK (call_outcome IN ('interested', 'not_interested', 'call_later', 'wrong_number', 'not_reachable')),
    call_notes TEXT,
    follow_up_required BOOLEAN NOT NULL DEFAULT false,
    follow_up_date DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_call_logs_customer_id ON public.call_logs(customer_id);
CREATE INDEX IF NOT EXISTS idx_call_logs_caller_email ON public.call_logs(caller_email);
CREATE INDEX IF NOT EXISTS idx_call_logs_date ON public.call_logs(call_date);
CREATE INDEX IF NOT EXISTS idx_call_logs_outcome ON public.call_logs(call_outcome);

COMMENT ON TABLE public.call_logs IS 'Call activity logs from callers';

-- ============================================================
-- 16. TRACKING_SESSIONS TABLE (GPS tracking sessions)
-- ============================================================

CREATE TABLE IF NOT EXISTS public.tracking_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ,
    total_distance_km NUMERIC(12, 4) NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused', 'completed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON public.tracking_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_started_at ON public.tracking_sessions(started_at DESC);

COMMENT ON TABLE public.tracking_sessions IS 'GPS tracking sessions for field officers';

-- ============================================================
-- 17. LOCATION_POINTS TABLE (GPS location points)
-- ============================================================

CREATE TABLE IF NOT EXISTS public.location_points (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES public.tracking_sessions(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL,
    accuracy_m REAL,
    altitude_m REAL,
    speed_mps REAL,
    synced_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_points_session_id ON public.location_points(session_id);
CREATE INDEX IF NOT EXISTS idx_points_user_id ON public.location_points(user_id);
CREATE INDEX IF NOT EXISTS idx_points_recorded_at ON public.location_points(recorded_at ASC);

COMMENT ON TABLE public.location_points IS 'GPS location points captured during tracking';

-- ============================================================
-- SEED DATA: Insert Sample Products
-- ============================================================

INSERT INTO public.products (product_code, product_name, brand, category, pack_size_liters, unit_price, mrp, tax_rate)
VALUES
    ('10L-CARBO', '10 LITRE PLASTIC CARBO', 'standard', 'PLASTIC', 10.00, 1000.00, 1000.00, 18.00),
    ('20L-CARBO', '20 litre Carbo', 'standard', 'carbo', 20.00, 5000.00, 5000.00, 18.00),
    ('5L-CARBO-ARH', '5 LITRE PLASTIC CARBO (ARH )', 'standard', 'REGULAR', 5.00, 550.00, 550.00, 18.00),
    ('20L-STEEL-BARNI', '20 LTR STEEL BARNI', 'standard', 'Premium', 20.00, 3100.00, 3100.00, 18.00),
    ('5L-PLASTIC-JAR', '5 LTR PLASTIC JAR', 'standard', 'Regular', 5.00, 485.00, 485.00, 18.00),
    ('10L-STEEL-BARNI', '10 LTR STEEL BARNI', 'standard', 'Premium', 10.00, 1500.00, 1500.00, 18.00),
    ('2L-PLASTIC-JAR', '2 LTR PLASTIC JAR', 'standard', 'Regular', 2.00, 300.00, 300.00, 18.00),
    ('1L-PET-BOTTLE', '1 LITRE PET BOTTLE', 'standard', 'PET BOTTLE', 1.00, 110.00, 110.00, 18.00),
    ('5L-PLASTIC-CARBO', '5 litre plastic carbo', 'standard', 'Regular', 5.00, 520.00, 520.00, 18.00),
    ('10L-PLASTIC-JAR', '10 litre plastic Jar', 'standard', 'premium', 10.00, 1000.00, 1000.00, 18.00),
    ('5L-STEEL-BARNI', '5 LTR STEEL BARNI', 'standard', 'Premium', 5.00, 800.00, 800.00, 18.00),
    ('1L-PLASTIC-JAR', '1 LTR PLASTIC JAR', 'standard', 'Regular', 1.00, 105.00, 105.00, 18.00),
    ('20L-PLASTIC-CAN', '20 LITRE PLASTIC CAN', 'standard', 'STANDARD', 20.00, 3280.00, 3280.00, 18.00)
ON CONFLICT (product_code) DO NOTHING;

-- ============================================================
-- SEED DATA: Insert Sample Users
-- ============================================================

INSERT INTO public.users (email, name, mobile, role, manager_email, is_active)
VALUES
    ('manager@paruchemicals.com', 'Rajesh Kumar', '9876543000', 'manager', NULL, true),
    ('amit.sharma@paruchemicals.com', 'Amit Sharma', '9876543200', 'field_officer', 'manager@paruchemicals.com', true),
    ('priya.singh@paruchemicals.com', 'Priya Singh', '9876543201', 'field_officer', 'manager@paruchemicals.com', true),
    ('caller@paruchemicals.com', 'Neha Desai', '9876543100', 'caller', NULL, true)
ON CONFLICT (email) DO NOTHING;

-- ============================================================
-- SEED DATA: Insert Sample Customers
-- ============================================================

INSERT INTO public.customers (name, contact_person, mobile, customer_type, village, city, latitude, longitude, is_active)
VALUES
    ('Raj Traders', 'Rajesh Kumar', '9876543210', 'retailer', 'Kothrud', 'Pune', 18.5074, 73.8077, true),
    ('Gupta Distributors', 'Suresh Gupta', '9876543220', 'distributor', 'Shivaji Nagar', 'Pune', 18.5304, 73.8567, true),
    ('Sharma Enterprises', 'Amit Sharma', '9876543230', 'retailer', 'Pimpri', 'Pune', 18.6298, 73.7997, true)
ON CONFLICT DO NOTHING;

-- ============================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================================

-- Enable RLS on all tables
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.products ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fo_monthly_targets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.daily_route_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.route_plan_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.entity_edit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.visits ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fo_sales_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fo_sales_order_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fo_payment_receipts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fo_stock_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fo_notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.follow_ups ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.call_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tracking_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.location_points ENABLE ROW LEVEL SECURITY;

-- Service role (FastAPI Backend) has full access to all tables
DO $$
DECLARE
    tbl TEXT;
BEGIN
    FOR tbl IN 
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE'
    LOOP
        EXECUTE format('DROP POLICY IF EXISTS service_role_all_%I ON public.%I', tbl, tbl);
        EXECUTE format('CREATE POLICY service_role_all_%I ON public.%I FOR ALL TO service_role USING (true) WITH CHECK (true)', tbl, tbl);
    END LOOP;
END $$;

-- Authenticated and anon roles have full access (for mobile app)
DO $$
DECLARE
    tbl TEXT;
BEGIN
    FOR tbl IN 
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE'
    LOOP
        EXECUTE format('DROP POLICY IF EXISTS authenticated_all_%I ON public.%I', tbl, tbl);
        EXECUTE format('CREATE POLICY authenticated_all_%I ON public.%I FOR ALL TO authenticated USING (true) WITH CHECK (true)', tbl, tbl);
        
        EXECUTE format('DROP POLICY IF EXISTS anon_all_%I ON public.%I', tbl, tbl);
        EXECUTE format('CREATE POLICY anon_all_%I ON public.%I FOR ALL TO anon USING (true) WITH CHECK (true)', tbl, tbl);
    END LOOP;
END $$;

-- ============================================================
-- COMPLETION MESSAGE
-- ============================================================

DO $$
BEGIN
    RAISE NOTICE '✅ AURA Mobile v2.0 - Migration completed successfully!';
    RAISE NOTICE '📊 Created 17 tables';
    RAISE NOTICE '🔐 Enabled Row Level Security';
    RAISE NOTICE '📦 Inserted seed data: 13 products, 4 users, 3 customers';
    RAISE NOTICE '🚀 Backend is ready to use!';
END $$;

