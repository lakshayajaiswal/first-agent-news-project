# Supabase Database Schema Reference

## Tables & Relationships

### 1. `sources`
- `id`: UUID PRIMARY KEY DEFAULT `gen_random_uuid()`
- `name`: TEXT NOT NULL
- `category`: TEXT NOT NULL ('vtu', 'ai', 'development', 'cybersecurity')
- `url`: TEXT NOT NULL UNIQUE
- `source_type`: TEXT NOT NULL ('html', 'pdf', 'feed', 'api', 'json')
- `adapter_key`: TEXT NOT NULL
- `enabled`: BOOLEAN NOT NULL DEFAULT true
- `trust_level`: INTEGER NOT NULL DEFAULT 3 (1..5)
- `check_interval_minutes`: INTEGER NOT NULL DEFAULT 60
- `last_checked_at`: TIMESTAMPTZ
- `last_success_at`: TIMESTAMPTZ
- `consecutive_failures`: INTEGER NOT NULL DEFAULT 0
- `created_at`, `updated_at`: TIMESTAMPTZ NOT NULL DEFAULT `now()`

### 2. `articles`
- `id`: UUID PRIMARY KEY DEFAULT `gen_random_uuid()`
- `source_id`: UUID REFERENCES `sources(id)` ON DELETE SET NULL
- `title`: TEXT NOT NULL
- `canonical_url`: TEXT NOT NULL
- `source_url`: TEXT NOT NULL
- `published_at`: TIMESTAMPTZ
- `discovered_at`: TIMESTAMPTZ NOT NULL DEFAULT `now()`
- `content`: TEXT
- `content_hash`: TEXT NOT NULL
- `document_storage_path`: TEXT
- `document_mime_type`: TEXT
- `language`: TEXT NOT NULL DEFAULT 'en'
- `category`: TEXT NOT NULL ('vtu', 'ai', 'development', 'cybersecurity')
- `status`: TEXT NOT NULL ('candidate', 'accepted', 'rejected', 'error')
- `created_at`, `updated_at`: TIMESTAMPTZ NOT NULL DEFAULT `now()`

### 3. `events`
- `id`: UUID PRIMARY KEY DEFAULT `gen_random_uuid()`
- `primary_article_id`: UUID REFERENCES `articles(id)` ON DELETE SET NULL
- `event_key`: TEXT UNIQUE NOT NULL
- `event_title`: TEXT
- `first_seen_at`: TIMESTAMPTZ NOT NULL DEFAULT `now()`
- `last_seen_at`: TIMESTAMPTZ NOT NULL DEFAULT `now()`
- `article_count`: INTEGER NOT NULL DEFAULT 1

### 4. `article_events`
- `article_id`: UUID REFERENCES `articles(id)` ON DELETE CASCADE
- `event_id`: UUID REFERENCES `events(id)` ON DELETE CASCADE
- PRIMARY KEY (`article_id`, `event_id`)

### 5. `classifications`
- `id`: UUID PRIMARY KEY DEFAULT `gen_random_uuid()`
- `article_id`: UUID NOT NULL REFERENCES `articles(id)` ON DELETE CASCADE UNIQUE
- `relevance_score`: NUMERIC(5,4) (0.0 to 1.0)
- `importance_score`: INTEGER (1 to 10)
- `urgency`: TEXT NOT NULL ('low', 'medium', 'high', 'critical')
- `action_required`: BOOLEAN NOT NULL DEFAULT false
- `action_summary`: TEXT
- `confidence_score`: NUMERIC(5,4) (0.0 to 1.0)
- `decision`: TEXT NOT NULL ('accept', 'reject', 'needs_review')
- `reason`: TEXT NOT NULL
- `model_name`: TEXT NOT NULL
- `model_version`: TEXT

### 6. `summaries`
- `id`: UUID PRIMARY KEY DEFAULT `gen_random_uuid()`
- `article_id`: UUID NOT NULL REFERENCES `articles(id)` ON DELETE CASCADE UNIQUE
- `headline`: TEXT NOT NULL
- `what_happened`: TEXT NOT NULL
- `why_it_matters`: TEXT NOT NULL
- `action_required`: TEXT
- `key_points`: JSONB NOT NULL DEFAULT '[]'::jsonb
- `source_name`: TEXT NOT NULL
- `source_url`: TEXT NOT NULL
- `summary_version`: INTEGER NOT NULL DEFAULT 1
- `model_name`: TEXT NOT NULL

### 7. `notifications`
- `id`: UUID PRIMARY KEY DEFAULT `gen_random_uuid()`
- `article_id`: UUID REFERENCES `articles(id)` ON DELETE SET NULL
- `event_id`: UUID REFERENCES `events(id)` ON DELETE SET NULL
- `channel`: TEXT NOT NULL DEFAULT 'discord'
- `message_type`: TEXT NOT NULL ('urgent', 'daily_digest', 'weekly_digest')
- `discord_message_id`: TEXT
- `status`: TEXT NOT NULL ('pending', 'sent', 'failed')
- `attempt_count`: INTEGER NOT NULL DEFAULT 0
- `sent_at`: TIMESTAMPTZ
- `last_error`: TEXT
- CONSTRAINT `uq_notifications_delivery` UNIQUE (`article_id`, `channel`, `message_type`)

### 8. `fetch_runs`
- `id`: UUID PRIMARY KEY DEFAULT `gen_random_uuid()`
- `started_at`, `finished_at`: TIMESTAMPTZ
- `status`: TEXT ('running', 'success', 'partial', 'failed')
- `sources_attempted`, `sources_succeeded`, `sources_failed`: INTEGER
- `articles_discovered`, `articles_accepted`, `articles_rejected`, `duplicates_detected`: INTEGER
- `error_summary`: TEXT

### 9. `user_preferences`
- `id`: UUID PRIMARY KEY DEFAULT `gen_random_uuid()`
- `scheme`: TEXT NOT NULL DEFAULT '2025'
- `branch`: TEXT NOT NULL DEFAULT 'CSE'
- `semester`: TEXT NOT NULL DEFAULT '1'
- `ai_interest_level`, `development_interest_level`, `cybersecurity_interest_level`: INTEGER (1..5)
- `urgent_alerts_enabled`, `daily_digest_enabled`: BOOLEAN DEFAULT true
