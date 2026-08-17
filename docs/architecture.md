# Goddess AI 2.0 - System Architecture

## 1. Architectural Principles

1. **Local-First & Multi-Stream Isolation**:
   - Up to 4 simultaneous YouTube live streams are managed via isolated `StreamSession` instances.
   - A failure or network disconnect on Stream A never impacts Streams B, C, or D.

2. **Decoupled Asynchronous Event Bus**:
   - Components interact through an internal pub/sub event bus (`app.core.events.EventBus`).
   - Events include `STREAM_STARTED`, `CHAT_MESSAGE`, `MODERATION_TRIGGERED`, `AI_RESPONSE`, `MODULE_FAILED`, etc.
   - Subscriber failures are caught in isolation, preventing cascading crashes.

3. **Quota-Aware Credential Management**:
   - Support for up to 4 YouTube Data API keys and 4 Gemini AI keys.
   - Keys rotate with cooldowns upon encountering rate limits (HTTP 429) or quota errors.

4. **3-Tier AI Moderation Engine**:
   - Fast deterministic rules &rarr; Gemini contextual analysis &rarr; Action Policy safety gates.
   - Fail-Safe: Gemini failure produces `ANALYSIS_FAILED` ($conf=0.0$), never false `SAFE`.
   - Emergency kill switch, safe mode, owner/mod exemptions, and automatic circuit breaker.

5. **AI Co-Host Engine**:
   - Rule-first intent classification ($0.0 \to 1.0$).
   - Bounded context: $20$ messages stream context, $5$ interactions per user.
   - Strict length constraint ($\le 200$ chars) and anti-spam cooldowns.

6. **Pluggable Modular System**:
   - Standardized lifecycle state machine with topological dependency resolution.
   - Complete failure isolation for external modules.

7. **Creator Control Center & Real-Time Dashboard**:
   - Centralized shared WebSocket connection with exponential backoff.
   - 4-stream live overview, granular stream controls, and emergency confirmation dialogs.
   - Honest component health diagnostics.

---

## 2. Component Topology

```text
+-------------------------------------------------------------------------+
|                      GODDESS AI 2.0 CREATOR PLATFORM                    |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                 Next.js 15 Creator Control Center                 |  |
|  |   - 4-Stream Overview       - Stream Controls   - Moderation Feed |  |
|  |   - AI Co-Host Feed         - Module Center     - Emergency Modal |  |
|  |   - AI/YouTube Diagnostics  - Shared WebSocket  - Activity Log    |  |
|  +-------------------------------------------------------------------+  |
|                                     │ (REST & Central WS)               |
|                                     ▼                                   |
|  +-------------------------------------------------------------------+  |
|  |                 FastAPI Core Application Layer                    |  |
|  |   - /dashboard/overview, /health, /streams, /moderation, /cohost  |  |
|  |   - /modules, /ws                                                 |  |
|  +-------------------------------------------------------------------+  |
|                                     │                                   |
|                                     ▼                                   |
|  +-------------------------------------------------------------------+  |
|  |                 Internal Async Event Bus                          |  |
|  +-------------------------------------------------------------------+  |
|        │                  │                   │                         |
|        ▼                  ▼                   ▼                         |
|  +------------+   +---------------+   +------------------+              |
|  | Stream A   |   | Stream B      |   | Stream C & D     |              |
|  | - Chat     |   | - Chat        |   | - Chat           |              |
|  | - Mod      |   | - Mod         |   | - Mod            |              |
|  | - AI Host  |   | - AI Host     |   | - AI Host        |              |
|  +------------+   +---------------+   +------------------+              |
|        │                  │                   │                         |
|        ▼                  ▼                   ▼                         |
|  +-------------------------------------------------------------------+  |
|  |                     Core & Extension Engines                      |  |
|  |   - YouTube Engine (4 Keys, Quota Rotation, Chat Deduplication)   |  |
|  |   - Gemini AI Engine (4 Keys, Rate Limiter, Priority Queue)       |  |
|  |   - AI Moderation Engine (3-Tier, Action Policy, Circuit Breaker) |  |
|  |   - AI Co-Host Engine (Intents, Bounded Memory, Anti-Spam)        |  |
|  |   - Modular Module System (Commands, Welcome, Stats, Interaction) |  |
|  +-------------------------------------------------------------------+  |
+-------------------------------------------------------------------------+
```
