-- ============================================================
-- AURA BizAnalyst Migration — Run in Supabase SQL Editor
-- ============================================================

-- 1. profiles table (role + caller assignment)
CREATE TABLE IF NOT EXISTS profiles (
  id          UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  full_name   TEXT,
  role        TEXT NOT NULL DEFAULT 'field_officer'
              CHECK (role IN ('admin', 'caller', 'field_officer')),
  caller_id   UUID REFERENCES profiles(id) ON DELETE SET NULL,
  created_at  TIMESTAMPTZ DEFAULT now()
);

-- Auto-create profile on user signup
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.profiles (id, full_name, role)
  VALUES (
    NEW.id,
    COALESCE(NEW.raw_user_meta_data->>'full_name', NEW.raw_user_meta_data->>'name', NEW.email),
    COALESCE(NEW.raw_user_meta_data->>'role', 'field_officer')
  )
  ON CONFLICT (id) DO NOTHING;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE PROCEDURE handle_new_user();

-- Backfill profiles for existing auth users
INSERT INTO profiles (id, full_name, role)
SELECT
  id,
  COALESCE(raw_user_meta_data->>'full_name', raw_user_meta_data->>'name', email),
  COALESCE(raw_user_meta_data->>'role', 'field_officer')
FROM auth.users
ON CONFLICT (id) DO NOTHING;

-- Enable RLS
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "profiles_own_read" ON profiles
  FOR SELECT USING (auth.uid() = id);

CREATE POLICY "profiles_admin_all" ON profiles
  FOR ALL USING (
    EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'admin')
  );

-- ============================================================
-- 2. customers table
-- ============================================================
CREATE TABLE IF NOT EXISTS customers (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name        TEXT NOT NULL,
  village     TEXT,
  taluka      TEXT,
  district    TEXT,
  pincode     TEXT,
  contact_no  TEXT,
  created_by  UUID REFERENCES auth.users(id),
  created_at  TIMESTAMPTZ DEFAULT now(),
  is_active   BOOLEAN DEFAULT true
);

CREATE INDEX IF NOT EXISTS idx_customers_name ON customers(name);
CREATE INDEX IF NOT EXISTS idx_customers_created_by ON customers(created_by);

ALTER TABLE customers ENABLE ROW LEVEL SECURITY;

-- All authenticated users can read customers
CREATE POLICY "customers_read_auth" ON customers
  FOR SELECT USING (auth.role() = 'authenticated');

-- Only authenticated users can insert (as themselves)
CREATE POLICY "customers_insert_auth" ON customers
  FOR INSERT WITH CHECK (auth.uid() = created_by);

-- Owner or admin can update
CREATE POLICY "customers_update" ON customers
  FOR UPDATE USING (
    auth.uid() = created_by
    OR EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'admin')
  );

-- ============================================================
-- 3. customer_visits table
-- ============================================================
CREATE TABLE IF NOT EXISTS customer_visits (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id          UUID NOT NULL REFERENCES auth.users(id),
  customer_id      UUID NOT NULL REFERENCES customers(id),
  checked_in_at    TIMESTAMPTZ NOT NULL,
  checked_out_at   TIMESTAMPTZ,
  duration_minutes INT,
  checkin_lat      FLOAT,
  checkin_lng      FLOAT,
  notes            TEXT,
  sync_status      TEXT DEFAULT 'synced',
  created_at       TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_cv_user_checkin ON customer_visits(user_id, checked_in_at DESC);
CREATE INDEX IF NOT EXISTS idx_cv_customer     ON customer_visits(customer_id);

ALTER TABLE customer_visits ENABLE ROW LEVEL SECURITY;

-- FO can read own visits
CREATE POLICY "visits_own_read" ON customer_visits
  FOR SELECT USING (auth.uid() = user_id);

-- FO can insert own visits
CREATE POLICY "visits_own_insert" ON customer_visits
  FOR INSERT WITH CHECK (auth.uid() = user_id);

-- FO can update own visits (for checkout)
CREATE POLICY "visits_own_update" ON customer_visits
  FOR UPDATE USING (auth.uid() = user_id);

-- Caller can read visits of their assigned FOs
CREATE POLICY "visits_caller_read" ON customer_visits
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM profiles fo
      WHERE fo.id = customer_visits.user_id
        AND fo.caller_id = auth.uid()
    )
  );

-- Admin can read all visits
CREATE POLICY "visits_admin_read" ON customer_visits
  FOR SELECT USING (
    EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'admin')
  );

