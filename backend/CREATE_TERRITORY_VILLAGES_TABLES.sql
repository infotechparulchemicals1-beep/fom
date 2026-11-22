-- ==============================================================================
-- Migration: Officer Assigned Villages & Village Approval Requests
-- Target Database: Supabase PostgreSQL (Project: erggjpdfkfaxpnxpieho)
-- ==============================================================================

-- 1. Table: officer_assigned_villages (Territory villages assigned to each field officer)
CREATE TABLE IF NOT EXISTS public.officer_assigned_villages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    officer_email TEXT NOT NULL,
    officer_name TEXT,
    village_name TEXT NOT NULL,
    taluka TEXT,
    district TEXT DEFAULT 'Gujarat',
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT uq_officer_village UNIQUE (officer_email, village_name)
);

CREATE INDEX IF NOT EXISTS idx_oav_email ON public.officer_assigned_villages(officer_email);
CREATE INDEX IF NOT EXISTS idx_oav_village ON public.officer_assigned_villages(village_name);

-- 2. Table: village_approval_requests (Requests by officers for villages outside territory)
CREATE TABLE IF NOT EXISTS public.village_approval_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    officer_email TEXT NOT NULL,
    officer_name TEXT,
    village_name TEXT NOT NULL,
    taluka TEXT,
    reason TEXT,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    created_at TIMESTAMPTZ DEFAULT now(),
    reviewed_by TEXT,
    reviewed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_var_status ON public.village_approval_requests(status);
CREATE INDEX IF NOT EXISTS idx_var_email ON public.village_approval_requests(officer_email);

-- Enable RLS and permissive policies for anon & authenticated roles
ALTER TABLE public.officer_assigned_villages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.village_approval_requests ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow all on officer_assigned_villages" ON public.officer_assigned_villages;
CREATE POLICY "Allow all on officer_assigned_villages"
    ON public.officer_assigned_villages FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Allow all on village_approval_requests" ON public.village_approval_requests;
CREATE POLICY "Allow all on village_approval_requests"
    ON public.village_approval_requests FOR ALL USING (true) WITH CHECK (true);

-- Reload PostgREST schema cache
NOTIFY pgrst, 'reload schema';
