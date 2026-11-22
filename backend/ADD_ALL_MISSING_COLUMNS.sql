-- ==============================================================================
-- Migration: Add Missing Columns for Check-In/Check-Out Locations & Route Plans
-- Target Database: Supabase PostgreSQL (Project: erggjpdfkfaxpnxpieho)
-- ==============================================================================

-- 1. Table: customer_visits (Used for direct sync of field visits)
ALTER TABLE public.customer_visits ADD COLUMN IF NOT EXISTS checkin_location TEXT;
ALTER TABLE public.customer_visits ADD COLUMN IF NOT EXISTS checkin_village_name TEXT;
ALTER TABLE public.customer_visits ADD COLUMN IF NOT EXISTS checkout_location TEXT;
ALTER TABLE public.customer_visits ADD COLUMN IF NOT EXISTS checkout_village_name TEXT;
ALTER TABLE public.customer_visits ADD COLUMN IF NOT EXISTS checkin_lat DOUBLE PRECISION;
ALTER TABLE public.customer_visits ADD COLUMN IF NOT EXISTS checkin_lng DOUBLE PRECISION;
ALTER TABLE public.customer_visits ADD COLUMN IF NOT EXISTS checkout_lat DOUBLE PRECISION;
ALTER TABLE public.customer_visits ADD COLUMN IF NOT EXISTS checkout_lng DOUBLE PRECISION;
ALTER TABLE public.customer_visits ADD COLUMN IF NOT EXISTS duration_minutes INTEGER;
ALTER TABLE public.customer_visits ADD COLUMN IF NOT EXISTS visit_village TEXT;
ALTER TABLE public.customer_visits ADD COLUMN IF NOT EXISTS customer_name TEXT;
ALTER TABLE public.customer_visits ADD COLUMN IF NOT EXISTS is_unknown_customer BOOLEAN DEFAULT FALSE;

-- 2. Table: visits (Legacy / mirror table for visits)
ALTER TABLE public.visits ADD COLUMN IF NOT EXISTS checkin_location TEXT;
ALTER TABLE public.visits ADD COLUMN IF NOT EXISTS checkin_village_name TEXT;
ALTER TABLE public.visits ADD COLUMN IF NOT EXISTS checkout_location TEXT;
ALTER TABLE public.visits ADD COLUMN IF NOT EXISTS checkout_village_name TEXT;
ALTER TABLE public.visits ADD COLUMN IF NOT EXISTS checkin_lat DOUBLE PRECISION;
ALTER TABLE public.visits ADD COLUMN IF NOT EXISTS checkin_lng DOUBLE PRECISION;
ALTER TABLE public.visits ADD COLUMN IF NOT EXISTS checkout_lat DOUBLE PRECISION;
ALTER TABLE public.visits ADD COLUMN IF NOT EXISTS checkout_lng DOUBLE PRECISION;

-- 3. Table: route_plan_items (Planned stops / villages for the officer)
ALTER TABLE public.route_plan_items ADD COLUMN IF NOT EXISTS village_name TEXT;
ALTER TABLE public.route_plan_items ADD COLUMN IF NOT EXISTS executed_visit_id UUID;
ALTER TABLE public.route_plan_items ADD COLUMN IF NOT EXISTS task_type TEXT DEFAULT 'order';
ALTER TABLE public.route_plan_items ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'fo_manual';

-- 4. Table: daily_route_plans (Header for daily route plan)
ALTER TABLE public.daily_route_plans ADD COLUMN IF NOT EXISTS is_edited BOOLEAN DEFAULT FALSE;
ALTER TABLE public.daily_route_plans ADD COLUMN IF NOT EXISTS revision_number INTEGER DEFAULT 1;
ALTER TABLE public.daily_route_plans ADD COLUMN IF NOT EXISTS last_edit_reason TEXT;
ALTER TABLE public.daily_route_plans ADD COLUMN IF NOT EXISTS submission_time TIMESTAMPTZ;

-- 5. Table: entity_edit_logs (Audit log when route plans or orders are modified)
ALTER TABLE public.entity_edit_logs ADD COLUMN IF NOT EXISTS user_id TEXT;
ALTER TABLE public.entity_edit_logs ADD COLUMN IF NOT EXISTS revision_number INTEGER DEFAULT 1;
ALTER TABLE public.entity_edit_logs ADD COLUMN IF NOT EXISTS previous_payload TEXT;
ALTER TABLE public.entity_edit_logs ADD COLUMN IF NOT EXISTS new_payload TEXT;
ALTER TABLE public.entity_edit_logs ADD COLUMN IF NOT EXISTS edited_at TIMESTAMPTZ DEFAULT now();
ALTER TABLE public.entity_edit_logs ADD COLUMN IF NOT EXISTS sync_status TEXT DEFAULT 'synced';

-- 6. Reload Supabase PostgREST Schema Cache Immediately
-- This notifies Supabase REST API to recognize all added columns right away without 400 cache errors.
NOTIFY pgrst, 'reload schema';
