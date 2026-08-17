# GODDESS AI 2.0 — Incident Response & Creator Runbook

## 1. Incident Center Dashboard Overview

The Incident Center ([`frontend/src/components/dashboard/IncidentCenter.tsx`](file:///D:/GODDESS%20AI%202.0/frontend/src/components/dashboard/IncidentCenter.tsx)) gives creators real-time visual alerts during live streams:
- **CRITICAL (Red)**: Global Emergency Stop active or primary provider hard failure.
- **WARNING (Yellow)**: Stream in Safe Mode, rate limiting active, or circuit breaker in open state.
- **INFO (Blue)**: Clean state transitions, successful stream self-healing, or key rotation.

## 2. Standard Operating Procedures (SOPs)

### 2.1 Chat Surge / Phishing Raid
1. Click **SAFE MODE** on the affected stream to instantly suppress automated AI replies.
2. Tier 1 deterministic moderation rules continue running in the background.
3. Once chat normalizes, click **DISABLE SAFE MODE**.

### 2.2 Provider API Hard Outage
1. Circuit breaker trips to `OPEN` automatically; AI Co-Host enters safe `NO_RESPONSE` without hallucinations.
2. System retries via `HALF_OPEN` state once provider recovers.
3. Zero suppressed chat messages are replayed upon reconnection.
