# Setup & Deployment Guide

## 1. Prerequisites
- Python 3.10+
- Supabase Project (PostgreSQL + Storage)
- Google AI Studio Gemini API Key
- Discord Webhook URL / Bot Token

## 2. Environment Variables
Create `.env` based on `.env.example`:
```bash
SUPABASE_URL="https://xyzcompany.supabase.co"
SUPABASE_SERVICE_ROLE_KEY="eyJhbGciOi..."
GEMINI_API_KEY="AIzaSy..."
DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
```

## 3. Database Migration Execution
In Supabase SQL Editor, execute in order:
1. `supabase/migrations/001_initial_schema.sql`
2. `supabase/migrations/002_storage_and_rls.sql`
3. `supabase/seed.sql`

## 4. Verification Commands
```bash
# Verify schema and table definitions
python3 src/main.py check-schema

# Verify configuration and environment status
python3 src/main.py status

# Run full unit and integration test suite
python3 -m unittest discover -s tests -t . -v
```
