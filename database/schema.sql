-- Create query_records table in Supabase
-- Copy and paste this into Supabase SQL Editor to execute
-- Note: Update DB_TABLE_NAME in .env if using a different table name
-- Default table name: query_records

CREATE TABLE IF NOT EXISTS public.query_records (
    id BIGSERIAL PRIMARY KEY,
    city TEXT NOT NULL,
    aqi INTEGER,
    level TEXT,
    dominentpol TEXT,
    query_type TEXT DEFAULT 'single',
    source TEXT DEFAULT 'search',
    user_country TEXT,                      -- User's country (from IP geolocation)
    device_type TEXT,
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Migration: Add new columns to existing table (safe to run multiple times)
ALTER TABLE public.query_records ADD COLUMN IF NOT EXISTS dominentpol TEXT;
ALTER TABLE public.query_records ADD COLUMN IF NOT EXISTS query_type TEXT DEFAULT 'single';
ALTER TABLE public.query_records ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'search';
ALTER TABLE public.query_records ADD COLUMN IF NOT EXISTS user_country TEXT;
ALTER TABLE public.query_records ADD COLUMN IF NOT EXISTS device_type TEXT;

-- Create indexes for faster queries
-- Note: Index names follow pattern idx_{TABLE_NAME}_{COLUMN}
CREATE INDEX IF NOT EXISTS idx_query_records_city ON public.query_records(city);
CREATE INDEX IF NOT EXISTS idx_query_records_created ON public.query_records(created_at);
CREATE INDEX IF NOT EXISTS idx_query_records_level ON public.query_records(level);
CREATE INDEX IF NOT EXISTS idx_query_records_dominentpol ON public.query_records(dominentpol);
CREATE INDEX IF NOT EXISTS idx_query_records_query_type ON public.query_records(query_type);
CREATE INDEX IF NOT EXISTS idx_query_records_source ON public.query_records(source);
CREATE INDEX IF NOT EXISTS idx_query_records_user_country ON public.query_records(user_country);
CREATE INDEX IF NOT EXISTS idx_query_records_device_type ON public.query_records(device_type);

-- Disable RLS for public access (required for API inserts)
ALTER TABLE public.query_records DISABLE ROW LEVEL SECURITY;

-- Grant permissions to anon and authenticated roles
GRANT SELECT, INSERT, UPDATE, DELETE ON public.query_records TO anon, authenticated;

-- =============================================
-- Daily AQI Subscription (EPIC 4.0)
-- =============================================

CREATE TABLE IF NOT EXISTS public.email_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username TEXT NOT NULL,
    email TEXT NOT NULL,
    city TEXT NOT NULL,
    alert_time TIME NOT NULL,
    timezone TEXT NOT NULL DEFAULT 'Asia/Kuala_Lumpur',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT email_subscriptions_email_format CHECK (
        email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
    )
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_email_subscriptions_email_city_time
    ON public.email_subscriptions (email, city, alert_time)
    WHERE is_active = TRUE;

CREATE INDEX IF NOT EXISTS idx_email_subscriptions_active_time
    ON public.email_subscriptions (is_active, alert_time);

CREATE TABLE IF NOT EXISTS public.notification_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subscription_id UUID NOT NULL REFERENCES public.email_subscriptions(id) ON DELETE CASCADE,
    scheduled_for TIMESTAMPTZ NOT NULL,
    sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status TEXT NOT NULL,
    error_message TEXT,
    payload_summary JSONB
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_notification_logs_subscription_schedule
    ON public.notification_logs (subscription_id, scheduled_for);

CREATE INDEX IF NOT EXISTS idx_notification_logs_status_schedule
    ON public.notification_logs (status, scheduled_for);

ALTER TABLE public.email_subscriptions DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.notification_logs DISABLE ROW LEVEL SECURITY;

GRANT SELECT, INSERT, UPDATE, DELETE ON public.email_subscriptions TO anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.notification_logs TO anon, authenticated;
