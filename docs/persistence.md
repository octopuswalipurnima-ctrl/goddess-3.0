# Production Persistence & Reliability Layer

## 1. Overview

GODDESS AI 2.0 uses a strict separation between **persistent data** (PostgreSQL) and **transient runtime state** (Redis / local memory). This architecture guarantees system survivability across restarts, crashes, container redeployments (e.g. Railway), and temporary database or Redis outages without data corruption or duplicate moderation/Co-Host actions.

---

## 2. Core Separation of Concerns

```text
+-------------------------------------------------------------------------+
|                      GODDESS AI 2.0 PERSISTENCE TOPOLOGY                 |
|                                                                         |
|  +---------------------------+       +-------------------------------+  |
|  |   PostgreSQL Database     |       |         Redis Cache           |  |
|  | (Persistent Source Truth) |       |   (Transient State Only)      |  |
|  +---------------------------+       +-------------------------------+  |
|  | - streams                 |       | - distributed cooldowns       |  |
|  | - stream_configs          |       | - rate limit counters         |  |
|  | - moderation_audit_records|       | - transient idempotency locks |  |
|  | - cohost_configs          |       | - short-lived distributed TTLs|  |
|  | - cohost_audit_records    |       +-------------------------------+  |
|  | - module_configs          |                       │                  |
|  | - creator_settings        |                       ▼                  |
|  +---------------------------+       +-------------------------------+  |
|               │                      | Safe In-Memory Local Fallback |  |
|               ▼                      | (Fail-Safe if Redis is Down)  |  |
|  +---------------------------+       +-------------------------------+  |
|  |     Repository Layer      |                                          |
|  | - BaseRepository          |                                          |
|  | - StreamRepository        |                                          |
|  | - ModerationRepository    |                                          |
|  | - CoHostRepository        |                                          |
|  | - ModuleRepository        |                                          |
|  | - CreatorSettingsRepo     |                                          |
|  +---------------------------+                                          |
|               │                                                         |
|               ▼                                                         |
|  +---------------------------+                                          |
|  |    Recovery & Retention   |                                          |
|  | - RecoveryManager         |                                          |
|  | - AuditRetentionManager   |                                          |
|  +---------------------------+                                          |
+-------------------------------------------------------------------------+
```

---

## 3. Database Layer (PostgreSQL & SQLAlchemy 2.0 Async)

- **SQLAlchemy 2.x DeclarativeBase**: Models inherit from `app.db.base.Base` and `TimestampMixin` (`created_at`, `updated_at` with UTC timestamps).
- **Async Engine**: Production uses `postgresql+asyncpg://` with connection pooling (`QueuePool`), `pool_pre_ping=True`, configurable pool sizes, and acquisition timeouts. Local testing supports `sqlite+aiosqlite:///:memory:`.
- **Alembic Migrations**: Fully asynchronous migrations managed in `alembic/versions/`. Reversible migrations with explicit schema generation.
- **Repository Abstraction**: All database interactions pass through typed repositories (`StreamRepository`, `ModerationRepository`, `CoHostRepository`, `ModuleRepository`, `CreatorSettingsRepository`), avoiding N+1 queries and raw session leaks.

---

## 4. Transient State & Fail-Safe Redis

- **Distributed Cooldowns**: Enforces user and global cooldowns across distributed instances with millisecond TTL precision.
- **Idempotency Locks**: Atomic `set(..., nx=True, px=...)` checking prevents duplicate action execution.
- **Graceful Degradation**: If Redis is unconfigured or unreachable, `RedisStateManager` seamlessly transitions to thread-safe local in-memory caching with TTL eviction. Critical safety gates fail conservatively to prevent duplicate destructive actions.

---

## 5. Restart Recovery & Retention

- **Restart Recovery**: Upon server start, `RecoveryManager` restores persistent stream configs, moderation policies, Co-Host personality/cooldown settings, and module preferences without replaying historical actions.
- **Audit Retention**: `AuditRetentionManager` provides bounded batch pruning (default: 500 records/batch) for moderation and Co-Host logs older than the configured retention period (`audit_retention_days = 30`), protecting disk capacity while preserving active configurations.

---

## 6. Zero Secret Storage Policy

- **No Secrets in Database**: API keys (YouTube, Gemini), OAuth tokens, passwords, and private keys are **NEVER** stored in database tables, Redis, logs, or API payloads.
- **No Secrets in Redis**: Redis only stores transient boolean flags, counters, and hash keys.
