-- ==============================================================================
-- Personal AI Intelligence Agent — Supabase PostgreSQL Schema
-- Migration: 001_initial_schema.sql
-- Description: Core tables, constraints, indexes, triggers for ingestion & AI agent
-- ==============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ------------------------------------------------------------------------------
-- 1. Table: sources
-- Purpose: Configured monitored sources across VTU, AI, Dev, Cybersecurity
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('vtu', 'ai', 'development', 'cybersecurity')),
    url TEXT NOT NULL UNIQUE,
    source_type TEXT NOT NULL CHECK (source_type IN ('html', 'pdf', 'feed', 'api', 'json')),
    adapter_key TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT true,
    trust_level INTEGER NOT NULL DEFAULT 3 CHECK (trust_level BETWEEN 1 AND 5),
    check_interval_minutes INTEGER NOT NULL DEFAULT 60,
    last_checked_at TIMESTAMPTZ,
    last_success_at TIMESTAMPTZ,
    consecutive_failures INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sources_category_enabled ON sources(category, enabled);
CREATE INDEX IF NOT EXISTS idx_sources_adapter_key ON sources(adapter_key);

-- ------------------------------------------------------------------------------
-- 2. Table: articles
-- Purpose: Discovered source items (raw ingestion records)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS articles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID REFERENCES sources(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    canonical_url TEXT NOT NULL,
    source_url TEXT NOT NULL,
    published_at TIMESTAMPTZ,
    discovered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    content TEXT,
    content_hash TEXT NOT NULL,
    document_storage_path TEXT,
    document_mime_type TEXT,
    language TEXT NOT NULL DEFAULT 'en',
    category TEXT NOT NULL CHECK (category IN ('vtu', 'ai', 'development', 'cybersecurity')),
    status TEXT NOT NULL DEFAULT 'candidate' CHECK (status IN ('candidate', 'accepted', 'rejected', 'error')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Required Indexes from Documentation
CREATE INDEX IF NOT EXISTS idx_articles_canonical_url ON articles(canonical_url);
CREATE INDEX IF NOT EXISTS idx_articles_content_hash ON articles(content_hash);
CREATE INDEX IF NOT EXISTS idx_articles_published_at_desc ON articles(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_category_published_at ON articles(category, published_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_source_discovered_at ON articles(source_id, discovered_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_status ON articles(status);

-- ------------------------------------------------------------------------------
-- 3. Table: events
-- Purpose: Deduplicated real-world event grouping multiple articles
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    primary_article_id UUID REFERENCES articles(id) ON DELETE SET NULL,
    event_key TEXT UNIQUE NOT NULL,
    event_title TEXT,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    article_count INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_events_event_key ON events(event_key);
CREATE INDEX IF NOT EXISTS idx_events_last_seen ON events(last_seen_at DESC);

-- ------------------------------------------------------------------------------
-- 4. Table: article_events
-- Purpose: Many-to-many / Many-to-one relationship between articles and events
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS article_events (
    article_id UUID REFERENCES articles(id) ON DELETE CASCADE,
    event_id UUID REFERENCES events(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (article_id, event_id)
);

CREATE INDEX IF NOT EXISTS idx_article_events_event_id ON article_events(event_id);

-- ------------------------------------------------------------------------------
-- 5. Table: classifications
-- Purpose: AI relevance, importance, urgency, and actionability analysis
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS classifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    article_id UUID NOT NULL REFERENCES articles(id) ON DELETE CASCADE UNIQUE,
    relevance_score NUMERIC(5,4) NOT NULL CHECK (relevance_score BETWEEN 0.0 AND 1.0),
    importance_score INTEGER NOT NULL CHECK (importance_score BETWEEN 1 AND 10),
    urgency TEXT NOT NULL CHECK (urgency IN ('low', 'medium', 'high', 'critical')),
    action_required BOOLEAN NOT NULL DEFAULT false,
    action_summary TEXT,
    confidence_score NUMERIC(5,4) NOT NULL CHECK (confidence_score BETWEEN 0.0 AND 1.0),
    decision TEXT NOT NULL CHECK (decision IN ('accept', 'reject', 'needs_review')),
    reason TEXT NOT NULL,
    model_name TEXT NOT NULL,
    model_version TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_classifications_decision ON classifications(decision);
CREATE INDEX IF NOT EXISTS idx_classifications_urgency ON classifications(urgency);
CREATE INDEX IF NOT EXISTS idx_classifications_importance ON classifications(importance_score DESC);

-- ------------------------------------------------------------------------------
-- 6. Table: summaries
-- Purpose: Grounded AI summaries generated for accepted items
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    article_id UUID NOT NULL REFERENCES articles(id) ON DELETE CASCADE UNIQUE,
    headline TEXT NOT NULL,
    what_happened TEXT NOT NULL,
    why_it_matters TEXT NOT NULL,
    action_required TEXT,
    key_points JSONB NOT NULL DEFAULT '[]'::jsonb,
    source_name TEXT NOT NULL,
    source_url TEXT NOT NULL,
    summary_version INTEGER NOT NULL DEFAULT 1,
    model_name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------------------------
-- 7. Table: notifications
-- Purpose: Delivery tracking and idempotency for Discord alerts and digests
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    article_id UUID REFERENCES articles(id) ON DELETE SET NULL,
    event_id UUID REFERENCES events(id) ON DELETE SET NULL,
    channel TEXT NOT NULL DEFAULT 'discord' CHECK (channel IN ('discord')),
    message_type TEXT NOT NULL CHECK (message_type IN ('urgent', 'daily_digest', 'weekly_digest')),
    discord_message_id TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'failed')),
    attempt_count INTEGER NOT NULL DEFAULT 0,
    sent_at TIMESTAMPTZ,
    last_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Unique constraint guarantees one delivery per article per channel per message type
    CONSTRAINT uq_notifications_delivery UNIQUE (article_id, channel, message_type)
);

CREATE INDEX IF NOT EXISTS idx_notifications_status ON notifications(status);
CREATE INDEX IF NOT EXISTS idx_notifications_message_type ON notifications(message_type);

-- ------------------------------------------------------------------------------
-- 8. Table: fetch_runs
-- Purpose: Run logs, health metrics, and pipeline auditability
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fetch_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'success', 'partial', 'failed')),
    sources_attempted INTEGER NOT NULL DEFAULT 0,
    sources_succeeded INTEGER NOT NULL DEFAULT 0,
    sources_failed INTEGER NOT NULL DEFAULT 0,
    articles_discovered INTEGER NOT NULL DEFAULT 0,
    articles_accepted INTEGER NOT NULL DEFAULT 0,
    articles_rejected INTEGER NOT NULL DEFAULT 0,
    duplicates_detected INTEGER NOT NULL DEFAULT 0,
    error_summary TEXT
);

CREATE INDEX IF NOT EXISTS idx_fetch_runs_started_at ON fetch_runs(started_at DESC);

-- ------------------------------------------------------------------------------
-- 9. Table: user_preferences
-- Purpose: User settings, scheme context (2025), and notification controls
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scheme TEXT NOT NULL DEFAULT '2025',
    branch TEXT NOT NULL DEFAULT 'CSE',
    semester TEXT NOT NULL DEFAULT '1',
    ai_interest_level INTEGER NOT NULL DEFAULT 3 CHECK (ai_interest_level BETWEEN 1 AND 5),
    development_interest_level INTEGER NOT NULL DEFAULT 3 CHECK (development_interest_level BETWEEN 1 AND 5),
    cybersecurity_interest_level INTEGER NOT NULL DEFAULT 3 CHECK (cybersecurity_interest_level BETWEEN 1 AND 5),
    urgent_alerts_enabled BOOLEAN NOT NULL DEFAULT true,
    daily_digest_enabled BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Trigger for auto-updating updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER trg_sources_updated_at
    BEFORE UPDATE ON sources
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_articles_updated_at
    BEFORE UPDATE ON articles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_user_preferences_updated_at
    BEFORE UPDATE ON user_preferences
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
