-- ============================================================
-- Add photo_urls column to customer_visits table
-- Run this in Supabase SQL Editor: https://supabase.com/dashboard/project/erggjpdfkfaxpnxpieho/sql
-- ============================================================

ALTER TABLE customer_visits 
ADD COLUMN IF NOT EXISTS photo_urls JSONB DEFAULT '[]'::jsonb;
