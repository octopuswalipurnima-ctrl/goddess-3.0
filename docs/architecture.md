# Goddess AI 2.0 - System Architecture

## 1. Architectural Principles

1. **Local-First & Multi-Stream Isolation**:
   - Up to 4 simultaneous YouTube live streams are managed via isolated `StreamSession` instances.
   - A failure or network disconnect on Stream A never impacts Streams B, C, or D.

2. **Decoupled Asynchronous Event Bus**:
   - Components interact through an internal pub/sub event bus (`app.core.events.EventBus`).
   - Events include `STREAM_STARTED`, `CHAT_MESSAGE`, `MODERATION_TRIGGERED`, `AI_RESPONSE`, etc.
   - Subscriber failures are caught in isolation, preventing cascading crashes.

3. **Quota-Aware Credential Management**:
   - Support for up to 4 YouTube Data API keys and 4 Gemini AI keys.
   - Keys rotate with cooldowns upon encountering rate limits (HTTP 429) or quota errors.

4. **Honest Component Health Diagnostics**:
   - Subsystems report honest states: `HEALTHY`, `NOT_CONFIGURED`, `UNAVAILABLE`, `ERROR`.
   - Never report false positive health.

---

## 2. Component Topology

```text
+-------------------------------------------------------------+
|                      GODDESS AI 2.0                         |
|                                                             |
|  +-------------------------------------------------------+  |
|  |                 FastAPI Application                   |  |
|  |   - REST API (/api/v1/health, /api/v1/streams)        |  |
|  |   - WebSocket Hub (/api/v1/ws)                        |  |
|  +-------------------------------------------------------+  |
|                             |                               |
|                             v                               |
|  +-------------------------------------------------------+  |
|  |              Internal Async Event Bus                 |  |
|  +-------------------------------------------------------+  |
|        |                  |                   |             |
|        v                  v                   v             |
|  +------------+   +---------------+   +------------------+  |
|  | Stream A   |   | Stream B      |   | Stream C & D     |  |
|  | - Chat     |   | - Chat        |   | - Chat           |  |
|  | - Mod      |   | - Mod         |   | - Mod            |  |
|  | - AI Host  |   | - AI Host     |   | - AI Host        |  |
|  +------------+   +---------------+   +------------------+  |
|                             |                               |
|        +--------------------+---------------------+         |
|        |                    |                     |         |
|        v                    v                     v         |
|  +------------+     +---------------+     +--------------+  |
|  | PostgreSQL |     | Redis State   |     | Gemini Engine|  |
|  | (Milestone1|     | (Milestone 1) |     | (Milestone 3)|  |
|  +------------+     +---------------+     +--------------+  |
+-------------------------------------------------------------+
```
