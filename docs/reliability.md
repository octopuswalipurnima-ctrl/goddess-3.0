# GODDESS AI 2.0 — Reliability & Resilience Architecture

## 1. Core Reliability Principles

### Multi-Tier Graceful Degradation
- **Database Outage**: When PostgreSQL is unreachable in development or local modes, the system seamlessly uses an asynchronous SQLite database (`sqlite+aiosqlite:///./goddess_local.db`).
- **Redis Outage**: When Redis is down or unconfigured, the system automatically falls back to an in-memory dictionary-backed transient state manager with zero dropped chat messages or unhandled exceptions.
- **Gemini API Outage**: If Gemini times out, runs out of quota, or fails, the Moderation Engine falls back to deterministic rule matching and `ANALYSIS_FAILED` fail-safe defaults (never approving questionable content blindly).
- **YouTube API Outage / Quota Limits**: The YouTube Engine automatically rotates through configured API keys upon receiving 403 quota errors and activates exponential backoff polling.

---

## 2. Crash Recovery & Startup Pipeline
Upon backend reboot or container redeployment, GODDESS AI 2.0 executes a 10-step startup sequence:
1. Environment validation (verifies minimum 32-character `SECRET_KEY` in production).
2. Structured logging & real-time secret masking initialization.
3. Asynchronous database ping and schema validation.
4. Redis state manager connection & fallback activation.
5. Persistent configuration recovery (`RecoveryManager` restores per-stream moderation rules, Co-Host personality, and module configurations).
6. Pluggable Module System discovery and lifecycle start.
7. Moderation Engine event bus subscription initialization.
8. Co-Host Engine event bus subscription initialization.
9. Audit pruning of records older than 30 days.
10. Readiness status transition to `READY`.

---

## 3. Idempotency & Multi-Stream Isolation
- **Idempotency Keys**: All moderation decisions and Co-Host replies generate deterministic idempotency keys (`idempotency_key = sha256(stream_id + message_id + action)`) preventing double-moderation or duplicate replies across concurrent threads.
- **Strict Multi-Stream Isolation**: State (rate limits, message context windows, moderation configs, module configurations) is strictly segmented by `stream_id`. Stream Alpha events can never bleed into Stream Beta.
