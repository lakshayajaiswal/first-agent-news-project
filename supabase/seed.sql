-- ==============================================================================
-- Personal AI Intelligence Agent — Supabase Seed Data
-- Seed: seed.sql
-- Description: Baseline source registry and initial user preferences
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. Initial User Preferences (VTU 2025 Scheme focus)
-- ------------------------------------------------------------------------------
INSERT INTO user_preferences (
    scheme,
    branch,
    semester,
    ai_interest_level,
    development_interest_level,
    cybersecurity_interest_level,
    urgent_alerts_enabled,
    daily_digest_enabled
) VALUES (
    '2025',
    'CSE',
    '1',
    4,
    4,
    5,
    true,
    true
) ON CONFLICT DO NOTHING;

-- ------------------------------------------------------------------------------
-- 2. Monitored Sources Registry
-- ------------------------------------------------------------------------------

-- VTU Sources (Official primary portal & circulars)
INSERT INTO sources (name, category, url, source_type, adapter_key, enabled, trust_level, check_interval_minutes)
VALUES
    ('VTU Official Circulars', 'vtu', 'https://vtu.ac.in/en/category/administration-circulars/', 'html', 'vtu_circulars_adapter', true, 5, 60),
    ('VTU Examination Notifications', 'vtu', 'https://vtu.ac.in/en/category/examination-notifications/', 'html', 'vtu_exams_adapter', true, 5, 60),
    ('VTU Academic Calendar & Scheme', 'vtu', 'https://vtu.ac.in/en/academic-calendar/', 'html', 'vtu_academic_adapter', true, 5, 120)
ON CONFLICT (url) DO NOTHING;

-- AI Sources (Model releases, major developer tools & research)
INSERT INTO sources (name, category, url, source_type, adapter_key, enabled, trust_level, check_interval_minutes)
VALUES
    ('Google AI & Gemini Updates', 'ai', 'https://blog.google/technology/ai/rss/', 'feed', 'rss_feed_adapter', true, 5, 120),
    ('OpenAI News & Releases', 'ai', 'https://openai.com/news/rss.xml', 'feed', 'rss_feed_adapter', true, 5, 120),
    ('Hugging Face Blog & Models', 'ai', 'https://huggingface.co/blog/feed.xml', 'feed', 'rss_feed_adapter', true, 4, 180),
    ('Anthropic Research & Announcements', 'ai', 'https://www.anthropic.com/news', 'html', 'html_feed_adapter', true, 5, 120)
ON CONFLICT (url) DO NOTHING;

-- Development Sources (Languages, frameworks, developer tooling, GitHub releases)
INSERT INTO sources (name, category, url, source_type, adapter_key, enabled, trust_level, check_interval_minutes)
VALUES
    ('GitHub Blog & Platform Changelog', 'development', 'https://github.blog/feed/', 'feed', 'rss_feed_adapter', true, 5, 120),
    ('Python Software Foundation Releases', 'development', 'https://blog.python.org/feeds/posts/default', 'feed', 'rss_feed_adapter', true, 5, 180),
    ('Node.js Technical Releases', 'development', 'https://nodejs.org/en/feed/blog.xml', 'feed', 'rss_feed_adapter', true, 4, 180),
    ('Hacker News Top Stories (Filtered)', 'development', 'https://news.ycombinator.com/rss', 'feed', 'hacker_news_adapter', true, 3, 60)
ON CONFLICT (url) DO NOTHING;

-- Cybersecurity Sources (Critical CVEs, active exploits, advisories)
INSERT INTO sources (name, category, url, source_type, adapter_key, enabled, trust_level, check_interval_minutes)
VALUES
    ('CISA Known Exploited Vulnerabilities', 'cybersecurity', 'https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json', 'json', 'cisa_kev_adapter', true, 5, 60),
    ('The Hacker News Cybersecurity', 'cybersecurity', 'https://feeds.feedburner.com/TheHackersNews', 'feed', 'rss_feed_adapter', true, 4, 120),
    ('BleepingComputer Security Alerts', 'cybersecurity', 'https://www.bleepingcomputer.com/feed/', 'feed', 'rss_feed_adapter', true, 4, 120),
    ('NIST NVD High Severity Vulnerabilities', 'cybersecurity', 'https://nvd.nist.gov/feeds/xml/cve/misc/nvd-rss.xml', 'feed', 'nist_nvd_adapter', true, 5, 60)
ON CONFLICT (url) DO NOTHING;
