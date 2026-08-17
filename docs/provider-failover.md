# GODDESS AI 2.0 — Provider Failover & Rotation Policy

## 1. Multi-Key Credential Pools

### YouTube Data API v3 (4 Key Slots)
- **Primary Slot (`KEY-1`)**: Used by default for polling and moderation.
- **Failover Logic**:
  - Quota exhaustion (HTTP 403 / 429) &rarr; exponential backoff cooldown (min 300s).
  - Automatically transitions to next slot: `KEY-1` &rarr; `KEY-2` &rarr; `KEY-3` &rarr; `KEY-4`.
  - All keys exhausted &rarr; graceful fallback to read-only safe polling without chat writes.

### Google Gemini AI API (4 Key Slots)
- **Primary Model**: `gemini-2.5-flash`
- **Fallback Model**: `gemini-2.5-flash-lite`
- **Rotation Behavior**:
  - Rate limit / Quota &rarr; Rotate `KEY-1` &rarr; `KEY-2` &rarr; `KEY-3` &rarr; `KEY-4`.
  - 503 Service Unavailable &rarr; Switch to `gemini-2.5-flash-lite`.
  - Complete Outage &rarr; Tier 1 deterministic moderation stays 100% operational; AI Co-Host gracefully enters `NO_RESPONSE` without hallucination.

## 2. Zero-Secret Observability
- All rotation logs and telemetry references use safe aliases: `KEY-1`, `KEY-2`, `KEY-3`, `KEY-4`.
- Raw API keys are never rendered in exceptions, logs, audit trails, or WebSockets.
