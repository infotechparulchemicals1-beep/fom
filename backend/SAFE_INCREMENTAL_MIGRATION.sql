-- ============================================================
-- AURA Mobile v2.0 - Safe Incremental Migration
-- This script checks existing schema and only adds missing pieces
-- ============================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- Add missing columns to existing tables (safe)
-- ============================================================

-- Add mobile column to users table if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='users' AND column_name='mobile') 
    THEN
        ALTER TABLE public.users ADD COLUMN mobile TEXT;
        RAISE NOTICE 'Added mobile column to users table';
    END IF;
END $$;

-- Add manager_email column to users table if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='users' AND column_name='manager_email') 
    THEN
        ALTER TABLE public.users ADD COLUMN manager_email TEXT;
        RAISE NOTICE 'Added manager_email column to users table';
    END IF;
END $$;

-- Add is_active column to users table if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='users' AND column_name='is_active') 
    THEN
        ALTER TABLE public.users ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT true;
        RAISE NOTICE 'Added is_active column to users table';
    END IF;
END $$;

-- ============================================================
-- Create missing tables only
-- ============================================================

-- PRODUCTS TABLE
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

-- FO_MONTHLY_TARGETS TABLE
CREATE TABLE IF NOT EXISTS public.fo_monthly_targets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_email TEXT NOT NULL,
    month_year TEXT NOT NULL,
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

-- DAILY_ROUTE_PLANS TABLE
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

-- ROUTE_PLAN_ITEMS TABLE
CREATE TABLE IF NOT EXISTS public.route_plan_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    plan_id UUID NOT NULL REFERENCES public.daily_route_plans(id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES public.customers(id),
    planned_sequence INTEGER NOT NULL,
    planned_time TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'skipped')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ENTITY_EDIT_LOGS TABLE
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

-- Add visit verification columns if they don't exist
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='visits') THEN
        -- Add verified column
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                       WHERE table_name='visits' AND column_name='verified') 
        THEN
            ALTER TABLE public.visits ADD COLUMN verified BOOLEAN NOT NULL DEFAULT false;
            RAISE NOTICE 'Added verified column to visits table';
        END IF;
        
        -- Add verified_by column
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                       WHERE table_name='visits' AND column_name='verified_by') 
        THEN
            ALTER TABLE public.visits ADD COLUMN verified_by TEXT;
            RAISE NOTICE 'Added verified_by column to visits table';
        END IF;
        
        -- Add verified_at column
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                       WHERE table_name='visits' AND column_name='verified_at') 
        THEN
            ALTER TABLE public.visits ADD COLUMN verified_at TIMESTAMPTZ;
            RAISE NOTICE 'Added verified_at column to visits table';
        END IF;
        
        -- Add call_notes column
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                       WHERE table_name='visits' AND column_name='call_notes') 
        THEN
            ALTER TABLE public.visits ADD COLUMN call_notes TEXT;
            RAISE NOTICE 'Added call_notes column to visits table';
        END IF;
        
        -- Add second_pitch_status column
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                       WHERE table_name='visits' AND column_name='second_pitch_status') 
        THEN
            ALTER TABLE public.visits ADD COLUMN second_pitch_status TEXT CHECK (second_pitch_status IN ('not_pitched', 'pitched_interested', 'pitched_follow_up', 'pitched_converted'));
            RAISE NOTICE 'Added second_pitch_status column to visits table';
        END IF;
    END IF;
END $$;

-- FO_SALES_ORDERS TABLE
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

-- FO_SALES_ORDER_ITEMS TABLE
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

-- FO_PAYMENT_RECEIPTS TABLE
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
    reference_number TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- FO_STOCK_REQUESTS TABLE
CREATE TABLE IF NOT EXISTS public.fo_stock_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
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

-- FO_NOTIFICATIONS TABLE
CREATE TABLE IF NOT EXISTS public.fo_notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_email TEXT NOT NULL,
    notification_type TEXT NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    data JSONB,
    is_read BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- FOLLOW_UPS TABLE
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

-- CALL_LOGS TABLE
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

-- ============================================================
-- Create indexes (all with IF NOT EXISTS)
-- ============================================================

-- Users indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON public.users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON public.users(role);
CREATE INDEX IF NOT EXISTS idx_users_manager_email ON public.users(manager_email);

-- Products indexes
CREATE INDEX IF NOT EXISTS idx_products_code ON public.products(product_code);
CREATE INDEX IF NOT EXISTS idx_products_brand ON public.products(brand);
CREATE INDEX IF NOT EXISTS idx_products_active ON public.products(is_active);

-- FO Monthly Targets indexes
CREATE INDEX IF NOT EXISTS idx_targets_user_email ON public.fo_monthly_targets(user_email);
CREATE INDEX IF NOT EXISTS idx_targets_month_year ON public.fo_monthly_targets(month_year);

-- Daily Route Plans indexes
CREATE INDEX IF NOT EXISTS idx_plans_user_email ON public.daily_route_plans(user_email);
CREATE INDEX IF NOT EXISTS idx_plans_date ON public.daily_route_plans(plan_date);
CREATE INDEX IF NOT EXISTS idx_plans_status ON public.daily_route_plans(status);

-- Route Plan Items indexes
CREATE INDEX IF NOT EXISTS idx_plan_items_plan_id ON public.route_plan_items(plan_id);
CREATE INDEX IF NOT EXISTS idx_plan_items_customer_id ON public.route_plan_items(customer_id);
CREATE INDEX IF NOT EXISTS idx_plan_items_sequence ON public.route_plan_items(planned_sequence);

-- Entity Edit Logs indexes
CREATE INDEX IF NOT EXISTS idx_edit_logs_entity_type ON public.entity_edit_logs(entity_type);
CREATE INDEX IF NOT EXISTS idx_edit_logs_entity_id ON public.entity_edit_logs(entity_id);
CREATE INDEX IF NOT EXISTS idx_edit_logs_user_email ON public.entity_edit_logs(field_officer_email);
CREATE INDEX IF NOT EXISTS idx_edit_logs_timestamp ON public.entity_edit_logs(edit_timestamp DESC);

-- Visits indexes (only if table exists)
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='visits') THEN
        CREATE INDEX IF NOT EXISTS idx_visits_verified ON public.visits(verified);
        CREATE INDEX IF NOT EXISTS idx_visits_second_pitch ON public.visits(second_pitch_status);
        RAISE NOTICE 'Created indexes on visits table';
    END IF;
END $$;

-- Sales Orders indexes
CREATE INDEX IF NOT EXISTS idx_orders_number ON public.fo_sales_orders(order_number);
CREATE INDEX IF NOT EXISTS idx_orders_date ON public.fo_sales_orders(order_date);
CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON public.fo_sales_orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_fo_email ON public.fo_sales_orders(field_officer_email);
CREATE INDEX IF NOT EXISTS idx_orders_visit_id ON public.fo_sales_orders(visit_id);
CREATE INDEX IF NOT EXISTS idx_orders_discount_percent ON public.fo_sales_orders(discount_percent);

-- Sales Order Items indexes
CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON public.fo_sales_order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON public.fo_sales_order_items(product_id);

-- Payment Receipts indexes
CREATE INDEX IF NOT EXISTS idx_receipts_number ON public.fo_payment_receipts(receipt_number);
CREATE INDEX IF NOT EXISTS idx_receipts_date ON public.fo_payment_receipts(receipt_date);
CREATE INDEX IF NOT EXISTS idx_receipts_customer_id ON public.fo_payment_receipts(customer_id);
CREATE INDEX IF NOT EXISTS idx_receipts_fo_email ON public.fo_payment_receipts(field_officer_email);
CREATE INDEX IF NOT EXISTS idx_receipts_payment_method ON public.fo_payment_receipts(payment_method);

-- Stock Requests indexes
CREATE INDEX IF NOT EXISTS idx_stock_requests_fo_email ON public.fo_stock_requests(field_officer_email);
CREATE INDEX IF NOT EXISTS idx_stock_requests_status ON public.fo_stock_requests(status);
CREATE INDEX IF NOT EXISTS idx_stock_requests_date ON public.fo_stock_requests(request_date);

-- Notifications indexes
CREATE INDEX IF NOT EXISTS idx_notifications_user_email ON public.fo_notifications(user_email);
CREATE INDEX IF NOT EXISTS idx_notifications_read ON public.fo_notifications(is_read);
CREATE INDEX IF NOT EXISTS idx_notifications_created ON public.fo_notifications(created_at DESC);

-- Follow-ups indexes
CREATE INDEX IF NOT EXISTS idx_followups_user_email ON public.follow_ups(user_email);
CREATE INDEX IF NOT EXISTS idx_followups_customer_id ON public.follow_ups(customer_id);
CREATE INDEX IF NOT EXISTS idx_followups_status ON public.follow_ups(status);
CREATE INDEX IF NOT EXISTS idx_followups_due_date ON public.follow_ups(due_date);

-- Call Logs indexes
CREATE INDEX IF NOT EXISTS idx_call_logs_customer_id ON public.call_logs(customer_id);
CREATE INDEX IF NOT EXISTS idx_call_logs_caller_email ON public.call_logs(caller_email);
CREATE INDEX IF NOT EXISTS idx_call_logs_date ON public.call_logs(call_date);
CREATE INDEX IF NOT EXISTS idx_call_logs_outcome ON public.call_logs(call_outcome);

-- ============================================================
-- Insert seed data (only if tables are empty)
-- ============================================================

-- Insert sample products
INSERT INTO public.products (product_code, product_name, brand, category, pack_size_liters, unit_price, mrp, tax_rate, is_active)
SELECT * FROM (VALUES
    ('10L-CARBO', '10 LITRE PLASTIC CARBO', 'standard', 'PLASTIC', 10.00, 1000.00, 1000.00, 18.00, true),
    ('20L-CARBO', '20 litre Carbo', 'standard', 'carbo', 20.00, 5000.00, 5000.00, 18.00, true),
    ('5L-CARBO-ARH', '5 LITRE PLASTIC CARBO (ARH )', 'standard', 'REGULAR', 5.00, 550.00, 550.00, 18.00, true),
    ('20L-STEEL-BARNI', '20 LTR STEEL BARNI', 'standard', 'Premium', 20.00, 3100.00, 3100.00, 18.00, true),
    ('5L-PLASTIC-JAR', '5 LTR PLASTIC JAR', 'standard', 'Regular', 5.00, 485.00, 485.00, 18.00, true),
    ('10L-STEEL-BARNI', '10 LTR STEEL BARNI', 'standard', 'Premium', 10.00, 1500.00, 1500.00, 18.00, true),
    ('2L-PLASTIC-JAR', '2 LTR PLASTIC JAR', 'standard', 'Regular', 2.00, 300.00, 300.00, 18.00, true),
    ('1L-PET-BOTTLE', '1 LITRE PET BOTTLE', 'standard', 'PET BOTTLE', 1.00, 110.00, 110.00, 18.00, true),
    ('5L-PLASTIC-CARBO', '5 litre plastic carbo', 'standard', 'Regular', 5.00, 520.00, 520.00, 18.00, true),
    ('10L-PLASTIC-JAR', '10 litre plastic Jar', 'standard', 'premium', 10.00, 1000.00, 1000.00, 18.00, true),
    ('5L-STEEL-BARNI', '5 LTR STEEL BARNI', 'standard', 'Premium', 5.00, 800.00, 800.00, 18.00, true),
    ('1L-PLASTIC-JAR', '1 LTR PLASTIC JAR', 'standard', 'Regular', 1.00, 105.00, 105.00, 18.00, true),
    ('20L-PLASTIC-CAN', '20 LITRE PLASTIC CAN', 'standard', 'STANDARD', 20.00, 3280.00, 3280.00, 18.00, true)
) AS v(product_code, product_name, brand, category, pack_size_liters, unit_price, mrp, tax_rate, is_active)
WHERE NOT EXISTS (SELECT 1 FROM public.products WHERE products.product_code = v.product_code);

-- Insert sample users
INSERT INTO public.users (email, name, mobile, role, manager_email, is_active)
SELECT * FROM (VALUES
    ('manager@paruchemicals.com', 'Rajesh Kumar', '9876543000', 'manager', NULL, true),
    ('amit.sharma@paruchemicals.com', 'Amit Sharma', '9876543200', 'field_officer', 'manager@paruchemicals.com', true),
    ('priya.singh@paruchemicals.com', 'Priya Singh', '9876543201', 'field_officer', 'manager@paruchemicals.com', true),
    ('caller@paruchemicals.com', 'Neha Desai', '9876543100', 'caller', NULL, true)
) AS v(email, name, mobile, role, manager_email, is_active)
WHERE NOT EXISTS (SELECT 1 FROM public.users WHERE users.email = v.email);

-- ============================================================
-- Enable RLS and create policies
-- ============================================================

-- Enable RLS on new tables
ALTER TABLE public.products ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fo_monthly_targets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.daily_route_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.route_plan_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.entity_edit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fo_sales_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fo_sales_order_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fo_payment_receipts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fo_stock_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fo_notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.follow_ups ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.call_logs ENABLE ROW LEVEL SECURITY;

-- Create service_role policies (full access)
DO $$
DECLARE
    tbl TEXT;
    tables TEXT[] := ARRAY[
        'products', 'fo_monthly_targets', 'daily_route_plans', 'route_plan_items',
        'entity_edit_logs', 'fo_sales_orders', 'fo_sales_order_items', 
        'fo_payment_receipts', 'fo_stock_requests', 'fo_notifications',
        'follow_ups', 'call_logs'
    ];
BEGIN
    FOREACH tbl IN ARRAY tables
    LOOP
        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = tbl) THEN
            EXECUTE format('DROP POLICY IF EXISTS service_role_all_%I ON public.%I', tbl, tbl);
            EXECUTE format('CREATE POLICY service_role_all_%I ON public.%I FOR ALL TO service_role USING (true) WITH CHECK (true)', tbl, tbl);
            
            EXECUTE format('DROP POLICY IF EXISTS authenticated_all_%I ON public.%I', tbl, tbl);
            EXECUTE format('CREATE POLICY authenticated_all_%I ON public.%I FOR ALL TO authenticated USING (true) WITH CHECK (true)', tbl, tbl);
            
            EXECUTE format('DROP POLICY IF EXISTS anon_all_%I ON public.%I', tbl, tbl);
            EXECUTE format('CREATE POLICY anon_all_%I ON public.%I FOR ALL TO anon USING (true) WITH CHECK (true)', tbl, tbl);
        END IF;
    END LOOP;
END $$;

-- ============================================================
-- Completion message
-- ============================================================

DO $$
DECLARE
    table_count INT;
    product_count INT;
    user_count INT;
BEGIN
    SELECT COUNT(*) INTO table_count FROM information_schema.tables 
    WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
    
    SELECT COUNT(*) INTO product_count FROM public.products;
    SELECT COUNT(*) INTO user_count FROM public.users;
    
    RAISE NOTICE '✅ AURA Mobile v2.0 - Safe Migration Completed!';
    RAISE NOTICE '📊 Total tables in database: %', table_count;
    RAISE NOTICE '📦 Products in catalog: %', product_count;
    RAISE NOTICE '👥 Users in system: %', user_count;
    RAISE NOTICE '🚀 Backend is ready!';
END $$;
