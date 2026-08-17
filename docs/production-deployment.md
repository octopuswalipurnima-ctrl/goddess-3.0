# GODDESS AI 2.0 — Production Deployment Architecture

## 1. Overview & Operational Principles

GODDESS AI 2.0 is designed for production deployment on containerized and PaaS platforms (such as Railway, AWS, GCP, or bare-metal Linux).

### Core Invariants:
1. $\text{SAFE STOP} > \text{UNSAFE AUTOMATION}$
2. $\text{FAIL CLOSED} > \text{FABRICATED ACTION}$
3. $\text{STREAM ISOLATION} > \text{SHARED STATE}$
4. **Zero Raw Secret Exposure**: Credentials never appear in logs, traces, exceptions, models, or WebSocket frames.
5. **Zero Historical Chat Replay**: Reconnects and restarts discard historical backlogs and process only live inbound events.

---

## 2. Infrastructure Architecture

```mermaid
flowchart TD
    subgraph Railway["Railway Cloud Platform"]
        WebProcess["Uvicorn Async Web Worker (PORT Binding)"]
        AlembicStep["Alembic Migration Runner (alembic upgrade head)"]
        LiveProbe["Liveness Probe (/api/v1/health/live)"]
        ReadyProbe["Readiness Probe (/api/v1/health/ready)"]
    end

    subgraph DataServices["Managed Data Layer"]
        Postgres["PostgreSQL 16 (asyncpg pooled)"]
        Redis["Redis 7 (Distributed state / Cooldowns)"]
    end

    subgraph ExternalProviders["External APIs"]
        YouTube["YouTube Data API v3 (Up to 4 Keys)"]
        Gemini["Google Gemini API (gemini-2.5-flash)"]
    end

    WebProcess --> Postgres
    WebProcess --> Redis
    WebProcess --> YouTube
    WebProcess --> Gemini
    AlembicStep --> Postgres
```

---

## 3. Environment Variable Specification

| Variable | Required in Prod | Example / Format | Purpose |
|---|---|---|---|
| `ENVIRONMENT` | Yes | `production` | Enables strict validation & disables dev bypasses |
| `SECRET_KEY` | Yes | 32+ character hex string | Signs HS256 JWT tokens |
| `DATABASE_URL` | Yes | `postgresql+asyncpg://...` | PostgreSQL async persistence connection |
| `REDIS_URL` | Optional | `redis://default:...@...:6379/0` | Distributed transient state & cooldown cache |
| `YOUTUBE_API_KEY_1..4` | Yes (min 1) | `AIzaSy...` | Quota-rotated YouTube API access |
| `GEMINI_API_KEY_1..4` | Yes (min 1) | `AIzaSy...` | Quota-rotated Google Gemini API access |
| `CORS_ORIGINS` | Yes | `["https://dashboard.example.com"]` | Strict allowed origins |
| `AUTH_ENABLED` | Yes | `true` | Enforces JWT & RBAC security |
| `RATE_LIMIT_ENABLED` | Yes | `true` | Enforces multi-tier IP & token rate limits |
| `DEBUG` | Yes | `false` | Disables debug stack traces |
