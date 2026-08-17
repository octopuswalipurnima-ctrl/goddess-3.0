# GODDESS AI 2.0 — Action Idempotency & Mutation Protection

## 1. Overview

The `ActionIdempotencyManager` ([`backend/app/core/idempotency.py`](file:///D:/GODDESS%20AI%202.0/backend/app/core/idempotency.py)) provides bounded deduplication across all mutation vectors:
- Chat command executions (`!help`, `!rules`, etc.)
- Moderation enforcement actions (delete, timeout, ban)
- AI Co-Host reply generation and live chat writes
- Emergency Stop and Safe Mode toggles

## 2. Bounded Storage & Sliding Window
- In-memory key tracking is bounded to 5,000 action IDs with a 300-second sliding expiration window.
- When Redis is connected, idempotency registrations are automatically mirrored with distributed TTLs.
- Duplicate action IDs immediately return previously computed results without triggering secondary API calls or chat writes.
