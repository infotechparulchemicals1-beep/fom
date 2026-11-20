-- ============================================================
-- Migration: Add Actual Reverse-Geocoded Location Fields to Visits
-- Enables storing verified village and area address alongside raw GPS
-- ============================================================

ALTER TABLE public.visits ADD COLUMN IF NOT EXISTS checkin_location TEXT;
ALTER TABLE public.visits ADD COLUMN IF NOT EXISTS checkin_village_name TEXT;
ALTER TABLE public.visits ADD COLUMN IF NOT EXISTS checkout_location TEXT;
ALTER TABLE public.visits ADD COLUMN IF NOT EXISTS checkout_village_name TEXT;

COMMENT ON COLUMN public.visits.checkin_location IS 'Actual verified address/area resolved from GPS at check-in';
COMMENT ON COLUMN public.visits.checkin_village_name IS 'Actual village/town resolved from GPS at check-in';
COMMENT ON COLUMN public.visits.checkout_location IS 'Actual verified address/area resolved from GPS at check-out';
COMMENT ON COLUMN public.visits.checkout_village_name IS 'Actual village/town resolved from GPS at check-out';

-- Also add to customer_visits view or table if used directly
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'customer_visits') THEN
        ALTER TABLE public.customer_visits ADD COLUMN IF NOT EXISTS checkin_location TEXT;
        ALTER TABLE public.customer_visits ADD COLUMN IF NOT EXISTS checkin_village_name TEXT;
        ALTER TABLE public.customer_visits ADD COLUMN IF NOT EXISTS checkout_location TEXT;
        ALTER TABLE public.customer_visits ADD COLUMN IF NOT EXISTS checkout_village_name TEXT;
    END IF;
END $$;
