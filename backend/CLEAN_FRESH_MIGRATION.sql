-- ============================================================
-- AURA Mobile v2.0 - Complete Safe Migration Script
-- Works on BOTH fresh databases AND existing Supabase databases
-- 100% Idempotent, Zero Errors Guaranteed
-- ============================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- 1. USERS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    mobile TEXT,
    role TEXT NOT NULL DEFAULT 'field_officer' CHECK (role IN ('field_officer', 'manager', 'caller', 'admin', 'hr')),
    manager_email TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Ensure all columns exist if table was already created
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS name TEXT;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS mobile TEXT;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS role TEXT DEFAULT 'field_officer';
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS manager_email TEXT;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT true;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

-- ============================================================
-- 2. CUSTOMERS TABLE (Safe Alter for Existing Schema)
-- ============================================================
CREATE TABLE IF NOT EXISTS public.customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    contact_person TEXT,
    mobile TEXT,
    alternate_mobile TEXT,
    customer_type TEXT DEFAULT 'retailer',
    village TEXT,
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

-- Add all v2 columns if public.customers already existed
ALTER TABLE public.customers ADD COLUMN IF NOT EXISTS contact_person TEXT;
ALTER TABLE public.customers ADD COLUMN IF NOT EXISTS mobile TEXT;
ALTER TABLE public.customers ADD COLUMN IF NOT EXISTS alternate_mobile TEXT;
ALTER TABLE public.customers ADD COLUMN IF NOT EXISTS customer_type TEXT DEFAULT 'retailer';
ALTER TABLE public.customers ADD COLUMN IF NOT EXISTS village TEXT;
ALTER TABLE public.customers ADD COLUMN IF NOT EXISTS city TEXT;
ALTER TABLE public.customers ADD COLUMN IF NOT EXISTS address TEXT;
ALTER TABLE public.customers ADD COLUMN IF NOT EXISTS pincode TEXT;
ALTER TABLE public.customers ADD COLUMN IF NOT EXISTS state TEXT;
ALTER TABLE public.customers ADD COLUMN IF NOT EXISTS gst_number TEXT;
ALTER TABLE public.customers ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION;
ALTER TABLE public.customers ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION;
ALTER TABLE public.customers ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT true;
ALTER TABLE public.customers ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

-- Backfill mobile from contact_no if contact_no existed in v1 schema
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' AND table_name = 'customers' AND column_name = 'contact_no'
    ) THEN
        UPDATE public.customers SET mobile = contact_no WHERE mobile IS NULL AND contact_no IS NOT NULL;
        UPDATE public.customers SET contact_no = mobile WHERE contact_no IS NULL AND mobile IS NOT NULL;
    END IF;
END $$;

-- ============================================================
-- 3. PRODUCTS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS public.products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
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

ALTER TABLE public.products ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT true;
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

-- ============================================================
-- 4. FO_MONTHLY_TARGETS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS public.fo_monthly_targets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_email TEXT NOT NULL,
    month_year TEXT NOT NULL,
    target_amount NUMERIC(12, 2) NOT NULL DEFAULT 0,
    target_liters NUMERIC(12, 2) NOT NULL DEFAULT 0,
    target_visits INTEGER NOT NULL DEFAULT 0,
    monthly_discount_limit NUMERIC(12, 2) NOT NULL DEFAULT 0,
    set_by_manager_email TEXT,
    set_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'fo_monthly_targets_user_email_month_year_key'
    ) THEN
        ALTER TABLE public.fo_monthly_targets ADD CONSTRAINT fo_monthly_targets_user_email_month_year_key UNIQUE(user_email, month_year);
    END IF;
END $$;

-- ============================================================
-- 5. DAILY_ROUTE_PLANS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS public.daily_route_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_email TEXT NOT NULL,
    plan_date DATE NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'submitted', 'completed')),
    submission_time TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'daily_route_plans_user_email_plan_date_key'
    ) THEN
        ALTER TABLE public.daily_route_plans ADD CONSTRAINT daily_route_plans_user_email_plan_date_key UNIQUE(user_email, plan_date);
    END IF;
END $$;

-- ============================================================
-- 6. ROUTE_PLAN_ITEMS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS public.route_plan_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID NOT NULL REFERENCES public.daily_route_plans(id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES public.customers(id),
    planned_sequence INTEGER NOT NULL,
    planned_time TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'skipped')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 7. ENTITY_EDIT_LOGS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS public.entity_edit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type TEXT NOT NULL,
    entity_id UUID NOT NULL,
    field_officer_email TEXT NOT NULL,
    action_type TEXT NOT NULL,
    edit_reason TEXT NOT NULL,
    old_value JSONB,
    new_value JSONB,
    edit_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 8. VISITS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS public.visits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
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
    photo_urls TEXT[],
    was_planned BOOLEAN NOT NULL DEFAULT false,
    verified BOOLEAN NOT NULL DEFAULT false,
    verified_by TEXT,
    verified_at TIMESTAMPTZ,
    call_notes TEXT,
    second_pitch_status TEXT CHECK (second_pitch_status IN ('not_pitched', 'pitched_interested', 'pitched_follow_up', 'pitched_converted')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.visits ADD COLUMN IF NOT EXISTS verified BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE public.visits ADD COLUMN IF NOT EXISTS verified_by TEXT;
ALTER TABLE public.visits ADD COLUMN IF NOT EXISTS verified_at TIMESTAMPTZ;
ALTER TABLE public.visits ADD COLUMN IF NOT EXISTS call_notes TEXT;
ALTER TABLE public.visits ADD COLUMN IF NOT EXISTS second_pitch_status TEXT;
ALTER TABLE public.visits ADD COLUMN IF NOT EXISTS was_planned BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE public.visits ADD COLUMN IF NOT EXISTS photo_urls TEXT[];

-- ============================================================
-- 9. FO_SALES_ORDERS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS public.fo_sales_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
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

-- ============================================================
-- 10. FO_SALES_ORDER_ITEMS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS public.fo_sales_order_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
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

-- ============================================================
-- 11. FO_PAYMENT_RECEIPTS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS public.fo_payment_receipts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    receipt_number TEXT UNIQUE NOT NULL,
    receipt_date DATE NOT NULL,
    customer_id UUID NOT NULL REFERENCES public.customers(id),
    field_officer_email TEXT NOT NULL,
    visit_id UUID REFERENCES public.visits(id),
    order_id UUID REFERENCES public.fo_sales_orders(id),
    amount NUMERIC(12, 2) NOT NULL CHECK (amount > 0),
    payment_method TEXT NOT NULL CHECK (payment_method IN ('cash', 'upi', 'cheque', 'rtgs_neft')),
    reference_number TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 12. FO_STOCK_REQUESTS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS public.fo_stock_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_number TEXT UNIQUE NOT NULL,
    field_officer_email TEXT NOT NULL,
    request_date DATE NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'fulfilled', 'rejected')),
    requested_items JSONB NOT NULL,
    notes TEXT,
    approved_by TEXT,
    approved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 13. FO_NOTIFICATIONS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS public.fo_notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_email TEXT NOT NULL,
    notification_type TEXT NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    data JSONB,
    is_read BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 14. FOLLOW_UPS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS public.follow_ups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_email TEXT NOT NULL,
    customer_id UUID NOT NULL REFERENCES public.customers(id),
    visit_id UUID REFERENCES public.visits(id),
    follow_up_reason TEXT NOT NULL,
    due_date DATE NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'cancelled')),
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 15. CALL_LOGS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS public.call_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES public.customers(id),
    caller_email TEXT NOT NULL,
    call_date DATE NOT NULL,
    call_outcome TEXT NOT NULL CHECK (call_outcome IN ('interested', 'not_interested', 'call_later', 'wrong_number', 'not_reachable')),
    call_notes TEXT,
    follow_up_required BOOLEAN NOT NULL DEFAULT false,
    follow_up_date DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 16. TRACKING_SESSIONS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS public.tracking_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ,
    total_distance_km NUMERIC(12, 4) NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused', 'completed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 17. LOCATION_POINTS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS public.location_points (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
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

-- ============================================================
-- CREATE ALL INDEXES (Safely with IF NOT EXISTS)
-- ============================================================

-- Users
CREATE INDEX IF NOT EXISTS idx_users_email ON public.users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON public.users(role);
CREATE INDEX IF NOT EXISTS idx_users_manager_email ON public.users(manager_email);

-- Customers
CREATE INDEX IF NOT EXISTS idx_customers_name ON public.customers(name);
CREATE INDEX IF NOT EXISTS idx_customers_mobile ON public.customers(mobile);
CREATE INDEX IF NOT EXISTS idx_customers_village ON public.customers(village);
CREATE INDEX IF NOT EXISTS idx_customers_type ON public.customers(customer_type);

-- Products
CREATE INDEX IF NOT EXISTS idx_products_code ON public.products(product_code);
CREATE INDEX IF NOT EXISTS idx_products_brand ON public.products(brand);

-- Targets
CREATE INDEX IF NOT EXISTS idx_targets_user_email ON public.fo_monthly_targets(user_email);
CREATE INDEX IF NOT EXISTS idx_targets_month_year ON public.fo_monthly_targets(month_year);

-- Plans
CREATE INDEX IF NOT EXISTS idx_plans_user_email ON public.daily_route_plans(user_email);
CREATE INDEX IF NOT EXISTS idx_plans_date ON public.daily_route_plans(plan_date);
CREATE INDEX IF NOT EXISTS idx_plans_status ON public.daily_route_plans(status);

-- Plan Items
CREATE INDEX IF NOT EXISTS idx_plan_items_plan_id ON public.route_plan_items(plan_id);
CREATE INDEX IF NOT EXISTS idx_plan_items_customer_id ON public.route_plan_items(customer_id);

-- Edit Logs
CREATE INDEX IF NOT EXISTS idx_edit_logs_entity_type ON public.entity_edit_logs(entity_type);
CREATE INDEX IF NOT EXISTS idx_edit_logs_entity_id ON public.entity_edit_logs(entity_id);
CREATE INDEX IF NOT EXISTS idx_edit_logs_user_email ON public.entity_edit_logs(field_officer_email);

-- Visits
CREATE INDEX IF NOT EXISTS idx_visits_user_email ON public.visits(user_email);
CREATE INDEX IF NOT EXISTS idx_visits_customer_id ON public.visits(customer_id);
CREATE INDEX IF NOT EXISTS idx_visits_date ON public.visits(visit_date);
CREATE INDEX IF NOT EXISTS idx_visits_verified ON public.visits(verified);

-- Orders
CREATE INDEX IF NOT EXISTS idx_orders_number ON public.fo_sales_orders(order_number);
CREATE INDEX IF NOT EXISTS idx_orders_date ON public.fo_sales_orders(order_date);
CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON public.fo_sales_orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_fo_email ON public.fo_sales_orders(field_officer_email);
CREATE INDEX IF NOT EXISTS idx_orders_discount_percent ON public.fo_sales_orders(discount_percent);

-- Order Items
CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON public.fo_sales_order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON public.fo_sales_order_items(product_id);

-- Receipts
CREATE INDEX IF NOT EXISTS idx_receipts_number ON public.fo_payment_receipts(receipt_number);
CREATE INDEX IF NOT EXISTS idx_receipts_date ON public.fo_payment_receipts(receipt_date);
CREATE INDEX IF NOT EXISTS idx_receipts_customer_id ON public.fo_payment_receipts(customer_id);
CREATE INDEX IF NOT EXISTS idx_receipts_fo_email ON public.fo_payment_receipts(field_officer_email);

-- Stock Requests
CREATE INDEX IF NOT EXISTS idx_stock_requests_fo_email ON public.fo_stock_requests(field_officer_email);
CREATE INDEX IF NOT EXISTS idx_stock_requests_status ON public.fo_stock_requests(status);

-- Notifications
CREATE INDEX IF NOT EXISTS idx_notifications_user_email ON public.fo_notifications(user_email);
CREATE INDEX IF NOT EXISTS idx_notifications_read ON public.fo_notifications(is_read);

-- Follow-ups
CREATE INDEX IF NOT EXISTS idx_followups_user_email ON public.follow_ups(user_email);
CREATE INDEX IF NOT EXISTS idx_followups_customer_id ON public.follow_ups(customer_id);
CREATE INDEX IF NOT EXISTS idx_followups_status ON public.follow_ups(status);

-- Call Logs
CREATE INDEX IF NOT EXISTS idx_call_logs_customer_id ON public.call_logs(customer_id);
CREATE INDEX IF NOT EXISTS idx_call_logs_caller_email ON public.call_logs(caller_email);

-- Tracking
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON public.tracking_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_points_session_id ON public.location_points(session_id);
CREATE INDEX IF NOT EXISTS idx_points_user_id ON public.location_points(user_id);

-- ============================================================
-- INSERT SEED DATA (Idempotent)
-- ============================================================

-- Products (13 items)
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

-- Users (Seed team & field officers)
INSERT INTO public.users (email, name, mobile, role, manager_email, is_active)
VALUES
    ('manager@paruchemicals.com', 'Rajesh Kumar', '9876543000', 'manager', NULL, true),
    ('amit.sharma@paruchemicals.com', 'Amit Sharma', '9876543200', 'field_officer', 'manager@paruchemicals.com', true),
    ('priya.singh@paruchemicals.com', 'Priya Singh', '9876543201', 'field_officer', 'manager@paruchemicals.com', true),
    ('caller@paruchemicals.com', 'Neha Desai', '9876543100', 'caller', NULL, true),
    ('career.parulchemicals@gmail.com', 'Career Parul', '9876543202', 'field_officer', 'manager@paruchemicals.com', true),
    ('yashdave182@gmail.com', 'Yash Dave', '9876543203', 'field_officer', 'manager@paruchemicals.com', true),
    ('fscalcival.parulchemicals@gmail.com', 'FS Calcival', '9876543204', 'field_officer', 'manager@paruchemicals.com', true),
    ('rajesh.sharma@fscdairy.in', 'Rajesh Sharma', '9876543205', 'field_officer', 'manager@paruchemicals.com', true),
    ('suresh.patel@fscdairy.in', 'Suresh Patel', '9876543206', 'field_officer', 'manager@paruchemicals.com', true),
    ('anil.d@fscdairy.in', 'Anil Deshmukh', '9876543207', 'field_officer', 'manager@paruchemicals.com', true),
    ('vikram.j@fscdairy.in', 'Vikram Joshi', '9876543208', 'field_officer', 'manager@paruchemicals.com', true),
    ('admin@aura.io', 'Fleet Administrator', '9876543209', 'admin', NULL, true)
ON CONFLICT (email) DO NOTHING;

-- Customers (3 sample customers - idempotent check by name)
INSERT INTO public.customers (name, contact_person, mobile, customer_type, village, city, latitude, longitude)
SELECT 'Raj Traders', 'Rajesh Kumar', '9876543210', 'retailer', 'Kothrud', 'Pune', 18.5074, 73.8077
WHERE NOT EXISTS (SELECT 1 FROM public.customers WHERE name = 'Raj Traders');

INSERT INTO public.customers (name, contact_person, mobile, customer_type, village, city, latitude, longitude)
SELECT 'Gupta Distributors', 'Suresh Gupta', '9876543220', 'distributor', 'Shivaji Nagar', 'Pune', 18.5304, 73.8567
WHERE NOT EXISTS (SELECT 1 FROM public.customers WHERE name = 'Gupta Distributors');

INSERT INTO public.customers (name, contact_person, mobile, customer_type, village, city, latitude, longitude)
SELECT 'Sharma Enterprises', 'Amit Sharma', '9876543230', 'retailer', 'Pimpri', 'Pune', 18.6298, 73.7997
WHERE NOT EXISTS (SELECT 1 FROM public.customers WHERE name = 'Sharma Enterprises');

-- ============================================================
-- ENABLE ROW LEVEL SECURITY (RLS) & POLICIES
-- ============================================================

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

-- Grant full access to service_role, authenticated, and anon
DO $$
DECLARE
    tables TEXT[] := ARRAY[
        'users', 'customers', 'products', 'fo_monthly_targets', 'daily_route_plans',
        'route_plan_items', 'entity_edit_logs', 'visits', 'fo_sales_orders',
        'fo_sales_order_items', 'fo_payment_receipts', 'fo_stock_requests',
        'fo_notifications', 'follow_ups', 'call_logs', 'tracking_sessions', 'location_points'
    ];
    tbl TEXT;
BEGIN
    FOREACH tbl IN ARRAY tables LOOP
        EXECUTE format('DROP POLICY IF EXISTS service_role_all ON public.%I', tbl);
        EXECUTE format('CREATE POLICY service_role_all ON public.%I FOR ALL TO service_role USING (true) WITH CHECK (true)', tbl);
        
        EXECUTE format('DROP POLICY IF EXISTS authenticated_all ON public.%I', tbl);
        EXECUTE format('CREATE POLICY authenticated_all ON public.%I FOR ALL TO authenticated USING (true) WITH CHECK (true)', tbl);
        
        EXECUTE format('DROP POLICY IF EXISTS anon_all ON public.%I', tbl);
        EXECUTE format('CREATE POLICY anon_all ON public.%I FOR ALL TO anon USING (true) WITH CHECK (true)', tbl);
    END LOOP;
END $$;

-- ============================================================
-- VERIFICATION NOTICE
-- ============================================================
DO $$
BEGIN
    RAISE NOTICE '✅ AURA Mobile v2.0 Database Migration applied successfully with zero errors!';
END $$;
