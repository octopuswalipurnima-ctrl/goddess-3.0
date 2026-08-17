# GODDESS AI 2.0 — Milestone 11 Repository & AI Subsystem Audit

## 1. Executive Summary

Milestone 11 aims to unify, harden, and elevate the AI intelligence layer across GODDESS AI 2.0 while auditing real-service integration boundaries (YouTube, Google Gemini, PostgreSQL, Redis, WebSocket).

Baseline verified:
- **296 backend tests** passing.
- Frontend Next.js production build passing.
- 0 hardcoded secrets.

---

## 2. Existing AI & Orchestration Components

| Subsystem / File | Existing Functionality | Status & Capabilities | Gaps / Milestone 11 Enhancements |
|---|---|---|---|
| `app/services/gemini/client.py` | Google GenAI SDK wrapper | Async request dispatch, error sanitization | Add explicit timeout & token usage tracking |
| `app/services/gemini/credentials.py` | Multi-key pool manager | 1–4 API keys, rotation on 403/429, exponential backoff cooldowns | Unified per-stream token/request accounting |
| `app/services/gemini/queue.py` | Priority async queue | `HIGH` (Moderation) vs `NORMAL` (Co-Host) priority | Bounded capacity overflow protection & strict fail-closed rejection |
| `app/services/gemini/router.py` | Model Router | `gemini-2.5-flash` (primary) $\to$ `gemini-2.5-flash-lite` (fallback) | Overload detection & fallback metrics export |
| `app/services/moderation/` | 3-Tier Moderation Engine | Tier 1 regex rules, Tier 2 context, Tier 3 Gemini classification | Structured decision results, confidence thresholds, human override |
| `app/services/cohost/` | AI Co-Host Engine | Intent detection, persona prompt generation, DRY_RUN vs LIVE | Per-viewer context ($\le 5$), stream context ($\le 20$), duplicate prevention |
| `app/core/safety_controller.py` | Central Safety Controller | States: `NORMAL`, `DEGRADED`, `SAFE_MODE`, `EMERGENCY_STOP` | Direct integration with AI Decision Engine |
| `app/services/youtube/stream_supervisor.py` | 4-Stream Supervisor | Lifecycle management (`DISCOVERING` $\to$ `LIVE` $\to$ `ENDED`) | Stream-scoped AI decision execution |

---

## 3. Identified Architecture Enhancements for Milestone 11

1. **Centralized AI Decision Engine (`app/services/ai/decision_engine.py`)**:
   - Standardized pipeline: `ChatMessage` $\to$ `EventBus` $\to$ `SafetyController` $\to$ `ContextManager` $\to$ `IntentDetector` $\to$ `Moderation` $\to$ `AIDecisionEngine` $\to$ `PolicyEngine` $\to$ `SafetyController` $\to$ Execution.
   - Structured `AIDecision` schema (`action`, `confidence`, `reason`, `category`, `priority`, `stream_id`, `should_reply`, `should_moderate`, `fallback_used`).
2. **Context & Memory Limits**:
   - Stream context bounded to $\le 20$ messages; viewer context bounded to $\le 5$ messages with TTL and LRU eviction.
   - Strict stream isolation (`STREAM_A` $\ne$ `STREAM_B`). Zero raw credentials in context memory.
3. **Fail-Closed Principle**:
   - When Gemini is unavailable, overloaded, or unconfigured, Co-Host fails closed (`NO_RESPONSE`) without inventing fake answers. Deterministic Tier-1 moderation rules remain 100% active.
4. **Real Service Integration Boundary Audit**:
   - Deep review and operator-gated test harness for YouTube, Gemini, PostgreSQL, Redis, and WebSocket.
