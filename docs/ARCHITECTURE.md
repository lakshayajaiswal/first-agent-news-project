# System Architecture Specification

## 1. Cloud-Hosted Pipeline

The Personal AI Intelligence Agent is designed to operate on scheduled cloud workers with Supabase PostgreSQL as the central system of record, Gemini API for semantic evaluation, and Discord for alert/digest delivery.

```
[ Scheduled Trigger ] (Every 1-3 hours)
        │
        ▼
[ Ingestion Worker ]
        │
        ├──▶ For each enabled Source in `sources`:
        │      ├─ Fetch raw payload (HTML / JSON / RSS)
        │      ├─ Extract discrete items
        │      ├─ Canonicalize URLs & strip tracking params
        │      └─ Compute SHA-256 content hash
        │
        ├──▶ Level 1 Exact Deduplication (Canonical URL / Hash check in Supabase)
        │      ├─ Duplicate? -> Record duplicate metric & skip LLM
        │      └─ New candidate? -> Proceed to AI Layer
        │
        ├──▶ Gemini AI Classifier (Relevance / Importance / Urgency)
        │      ├─ Evaluates candidate against 2025 scheme & user interests
        │      ├─ Output validated against strict JSON schema
        │      └─ Status -> 'accepted' or 'rejected'
        │
        ├──▶ Level 2/3 Near-Duplicate & Event Consolidation
        │      └─ Associates related articles under shared `events`
        │
        ├──▶ Gemini AI Summarizer (Accepted items only)
        │      ├─ Grounded factual extraction (headline, what happened, why it matters, actions)
        │      └─ Saved to `summaries` table
        │
        └──▶ Discord Notification Dispatcher
               ├─ Urgent/Critical alerts -> Immediate post
               └─ Standard updates -> Queued for Daily Digest
```

## 2. Component Isolation

- **Source Adapters**: Completely isolated. If VTU portal changes HTML structure, only the VTU adapter throws an error while AI, Dev, and Cybersecurity sources continue unaffected.
- **AI Processing**: All LLM outputs are strictly validated via Pydantic/Python dataclass schemas before database write. Malformed outputs trigger a single repair attempt and fail safely without crashing the run.
- **Notification Guarantees**: Database `notifications` table acts as a transactional delivery ledger with unique constraints preventing repeated message deliveries.
