# Personal AI Intelligence Agent 🤖⚡

A cloud-hosted personal information and intelligence agent built with Python, Supabase PostgreSQL, Gemini API, and Discord.

The agent monitors, filters, deduplicates, and summarizes updates across four dedicated domains:
1. **VTU Engineering (2025 Scheme)** — Academic circulars, examination timetables, results, revaluation, and scheme notices.
2. **Artificial Intelligence** — Foundation model releases, capability advancements, developer tooling, and applied research.
3. **Software Development** — Languages, frameworks, developer tooling, and major open-source ecosystem updates.
4. **Cybersecurity** — Critical CVEs, active exploitation advisories, ransomware alerts, and critical patches.

---

## 🏗️ Architecture & Component Status

| Phase | Milestone | Status | Description |
|---|---|---|---|
| **Phase 1** | **Project Foundation & Schema** | **Completed ✅** | Base collector interface, source registry, Supabase migrations, storage layer, deduplication engine, settings, logging, test suite |
| Phase 2 | Extraction, Deduplication & AI Classifier | *Pending* | HTML/PDF parser, Level 1–3 deduplication, Gemini 2.5 structured relevance & urgency classification |
| Phase 3 | Grounded Summarizer & Discord Delivery | *Pending* | Strict factual summarization, urgent alerts, and daily digest webhook delivery |
| Phase 4 | Full Source Adapters | *Pending* | VTU, AI, Dev, and Cybersecurity collectors |
| Phase 5 | Scheduling & Observability | *Pending* | Cloud worker scheduler, automated retries, rate limits, health dashboards |
| Phase 6 | Discord Slash Commands | *Pending* | `/ask`, `/vtu`, `/ai`, `/coding`, `/cyber`, `/today`, `/health` |

---

## 📁 Repository Structure

```
ai-intelligence-agent/
├── .env.example               # Environment variables template
├── pyproject.toml             # Python packaging, dependencies, and pytest configuration
├── README.md                  # System overview and setup instructions
├── src/
│   ├── config/
│   │   ├── settings.py        # Strongly-typed environment configuration
│   │   └── logging_config.py  # Structured JSON logger with secret masking
│   ├── storage/
│   │   ├── models.py          # Domain entities (Source, Article, Classification, etc.)
│   │   ├── supabase_client.py # Supabase client and in-memory mock repository
│   │   └── schema_validator.py# Migration integrity verification
│   ├── normalization/
│   │   ├── url.py             # URL canonicalization & tracking parameter stripper
│   │   └── content.py         # Text sanitization & SHA-256 fingerprinting
│   ├── deduplication/
│   │   └── matcher.py         # Exact (URL/Hash) & near-title Jaccard deduplication
│   ├── collectors/
│   │   ├── base.py            # BaseCollector abstract interface (fetch/extract/normalize)
│   │   ├── registry.py        # Source registry, factory & health tracking
│   │   └── models.py          # RawSourceItem & NormalizedCandidate models
│   ├── ai/
│   │   ├── schemas.py         # ClassifierOutput & SummarizerOutput validation schemas
│   │   ├── classifier.py      # Classifier prompt contract & system instructions
│   │   └── summarizer.py      # Grounded summarizer prompt contract
│   ├── discord/
│   │   └── formatter.py       # Daily digest & Urgent alert formatting
│   └── main.py                # CLI entry point for diagnostics and execution
├── supabase/
│   ├── migrations/
│   │   ├── 001_initial_schema.sql  # Core tables, constraints, indexes & triggers
│   │   └── 002_storage_and_rls.sql # Storage buckets & Row Level Security policies
│   └── seed.sql               # Monitored source registry and default preferences
├── tests/
│   ├── fixtures/              # Sample VTU circular, AI release, and CVE payloads
│   ├── unit/                  # 100% passing unit tests
│   ├── integration/           # Database entity lifecycle tests
│   └── e2e/                   # System smoke tests
└── docs/
    ├── ARCHITECTURE.md        # Technical architecture specifications
    ├── DATABASE_SCHEMA.md     # Full PostgreSQL table documentation
    └── SETUP_GUIDE.md         # Deployment and configuration guide
```

---

## 🛠️ Quick Start & Testing

### 1. Environment Setup
```bash
cp .env.example .env
```

### 2. Verify Schema Integrity
```bash
python3 src/main.py check-schema
```

### 3. Check System Status
```bash
python3 src/main.py status
```

### 4. Run Test Suite
```bash
python3 -m unittest discover -s tests -t . -v
```

---

## 🗄️ Supabase PostgreSQL Schema Overview

- `sources`: Monitored portals with trust level (1–5), check interval, and failure counters.
- `articles`: Discovered items with canonical URL, content hash, category, and status.
- `events`: Deduplicated real-world event grouping multiple source articles.
- `article_events`: Relational mapping between articles and events.
- `classifications`: AI relevance score (0..1), importance (1..10), urgency (`low`|`medium`|`high`|`critical`), and decision.
- `summaries`: Grounded headline, what happened, why it matters, action required, and key points.
- `notifications`: Delivery tracking for Discord with unique constraints to prevent duplicate alerts.
- `fetch_runs`: Execution logs, discovered vs accepted counts, and error summaries.
- `user_preferences`: User scheme (`2025`), branch (`CSE`), semester, and interest levels.

---

## 🔐 Security & Idempotency Rules

1. **No Hardcoded Secrets**: All keys (`GEMINI_API_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `DISCORD_WEBHOOK_URL`) reside in environment variables.
2. **Secret Masking**: Logging system automatically masks credential fields.
3. **Idempotent Delivery**: Unique database constraints `(article_id, channel, message_type)` guarantee no duplicate notifications.
4. **Deterministic Deduplication**: Level 1 URL and content hash checks prevent redundant LLM calls.
