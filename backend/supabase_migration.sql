-- ============================================================
--  Supabase Migration: GPS Tracking Application SchemaWorking
--  Run this in the Supabase SQL Editor:
--  https://supabase.com/dashboard/project/erggjpdfkfaxpnxpieho/sql/new
-- ============================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ── 1. tracking_sessions ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.tracking_sessions (
    id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           TEXT        NOT NULL,
    started_at        TIMESTAMPTZ NOT NULL,
    ended_at          TIMESTAMPTZ,
    total_distance_km NUMERIC(12, 4) NOT NULL DEFAULT 0,
    status            TEXT        NOT NULL DEFAULT 'active'
                                  CHECK (status IN ('active', 'paused', 'completed')),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sessions_user_id    ON public.tracking_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_started_at ON public.tracking_sessions(started_at DESC);

-- ── 2. location_points ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.location_points (
    id           UUID             PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id   UUID             NOT NULL REFERENCES public.tracking_sessions(id) ON DELETE CASCADE,
    user_id      TEXT             NOT NULL,
    latitude     DOUBLE PRECISION NOT NULL,
    longitude    DOUBLE PRECISION NOT NULL,
    recorded_at  TIMESTAMPTZ      NOT NULL,
    accuracy_m   REAL,
    altitude_m   REAL,
    speed_mps    REAL,
    synced_at    TIMESTAMPTZ      DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_points_session_id  ON public.location_points(session_id);
CREATE INDEX IF NOT EXISTS idx_points_user_id     ON public.location_points(user_id);
CREATE INDEX IF NOT EXISTS idx_points_recorded_at ON public.location_points(recorded_at ASC);

-- Unique index to prevent duplicate location records
CREATE UNIQUE INDEX IF NOT EXISTS idx_points_id_unique ON public.location_points(id);

-- ── 3. Row Level Security (RLS) ───────────────────────────────
ALTER TABLE public.tracking_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.location_points   ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if re-running
DROP POLICY IF EXISTS "service_role_all_sessions" ON public.tracking_sessions;
DROP POLICY IF EXISTS "service_role_all_points" ON public.location_points;
DROP POLICY IF EXISTS "anon_all_sessions" ON public.tracking_sessions;
DROP POLICY IF EXISTS "anon_all_points" ON public.location_points;
DROP POLICY IF EXISTS "authenticated_all_sessions" ON public.tracking_sessions;
DROP POLICY IF EXISTS "authenticated_all_points" ON public.location_points;

-- Grant full access to service_role (FastAPI Backend)
CREATE POLICY "service_role_all_sessions" ON public.tracking_sessions
    FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "service_role_all_points" ON public.location_points
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- Allow authenticated and anon roles access for tracking operations
CREATE POLICY "anon_all_sessions" ON public.tracking_sessions
    FOR ALL TO anon USING (true) WITH CHECK (true);

CREATE POLICY "anon_all_points" ON public.location_points
    FOR ALL TO anon USING (true) WITH CHECK (true);

CREATE POLICY "authenticated_all_sessions" ON public.tracking_sessions
    FOR ALL TO authenticated USING (true) WITH CHECK (true);

CREATE POLICY "authenticated_all_points" ON public.location_points
    FOR ALL TO authenticated USING (true) WITH CHECK (true);
