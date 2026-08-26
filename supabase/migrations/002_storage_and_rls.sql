-- ==============================================================================
-- Personal AI Intelligence Agent — Supabase PostgreSQL Schema
-- Migration: 002_storage_and_rls.sql
-- Description: Storage buckets setup, Row Level Security (RLS) policies
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. Storage Buckets Setup
-- ------------------------------------------------------------------------------
-- Recommended buckets:
-- - 'raw-documents': PDF files, original source snapshots
-- - 'source-artifacts': Extracted attachments and durable artifacts
-- ------------------------------------------------------------------------------

INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES 
    ('raw-documents', 'raw-documents', false, 52428800, ARRAY['application/pdf', 'text/html', 'application/json', 'text/plain']),
    ('source-artifacts', 'source-artifacts', false, 52428800, ARRAY['application/pdf', 'image/png', 'image/jpeg', 'application/json'])
ON CONFLICT (id) DO NOTHING;

-- ------------------------------------------------------------------------------
-- 2. Row Level Security (RLS) Policies
-- ------------------------------------------------------------------------------

-- Enable RLS across all tables
ALTER TABLE sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE articles ENABLE ROW LEVEL SECURITY;
ALTER TABLE events ENABLE ROW LEVEL SECURITY;
ALTER TABLE article_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE classifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE summaries ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE fetch_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_preferences ENABLE ROW LEVEL SECURITY;

-- ------------------------------------------------------------------------------
-- Service Role Policies (Full access for backend Python workers and ingestion jobs)
-- ------------------------------------------------------------------------------
CREATE POLICY "Service role full access on sources" ON sources
    FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access on articles" ON articles
    FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access on events" ON events
    FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access on article_events" ON article_events
    FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access on classifications" ON classifications
    FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access on summaries" ON summaries
    FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access on notifications" ON notifications
    FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access on fetch_runs" ON fetch_runs
    FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access on user_preferences" ON user_preferences
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ------------------------------------------------------------------------------
-- Read-Only Policies for Authenticated / Query Client Access
-- ------------------------------------------------------------------------------
CREATE POLICY "Authenticated users can read sources" ON sources
    FOR SELECT TO authenticated USING (true);

CREATE POLICY "Authenticated users can read accepted articles" ON articles
    FOR SELECT TO authenticated USING (status = 'accepted');

CREATE POLICY "Authenticated users can read events" ON events
    FOR SELECT TO authenticated USING (true);

CREATE POLICY "Authenticated users can read classifications" ON classifications
    FOR SELECT TO authenticated USING (true);

CREATE POLICY "Authenticated users can read summaries" ON summaries
    FOR SELECT TO authenticated USING (true);

CREATE POLICY "Authenticated users can read user_preferences" ON user_preferences
    FOR SELECT TO authenticated USING (true);
