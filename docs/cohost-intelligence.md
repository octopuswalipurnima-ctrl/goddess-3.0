# AI Co-Host Adaptive Intelligence Architecture

## Overview
GODDESS AI 2.0 provides an intelligent, stream-aware AI Co-Host designed to assist live streamers without behaving like a generic chatbot. The system evaluates chat messages deterministically before deciding whether a response is required, enforce strict multi-stream isolation, uses verified creator knowledge bases, and applies anti-repetition lexical similarity algorithms.

## Core Safety Invariants
1. **SAFE STOP > UNSAFE AUTOMATION**: Global or per-stream Emergency Stop and Safe Mode take absolute precedence over Co-Host operations.
2. **FAIL CLOSED > FABRICATED ACTION**: If Gemini fails, rate limits, or unknown facts are requested, the Co-Host produces `NO_RESPONSE` rather than synthetic or hallucinated replies.
3. **Bounded Context**: Stream history is strictly capped at $\le 20$ messages; viewer history is strictly capped at $\le 5$ messages.
4. **Bounded Output**: Co-Host responses are strictly bounded to $\le 200$ characters.
5. **Anti-Repetition Window**: Similarity checking maintains a bounded sliding window of $\le 30$ responses per stream with Jaccard token overlap similarity ($\ge 0.70$).
6. **Multi-Stream Isolation**: Personalities, awareness state, creator knowledge, context windows, cooldowns, and deduplication states are isolated across `STREAM_A`, `STREAM_B`, `STREAM_C`, and `STREAM_D`.

## Processing Pipeline
```
ChatMessage
   │
   ▼
1. Bounded Context Ingestion (Stream <= 20, Viewer <= 5)
   │
   ▼
2. Rule Intent Detection (QUESTION, MENTION, GREETING, NOISE, COMMAND)
   │
   ▼
3. Deterministic Engagement Decision (Relevance, Priority, Cooldowns, Rate Limits)
   │
   ├── [NO_RESPONSE / IGNORE] ──► Discard (No Gemini Call, Cost = 0)
   │
   ▼ [ANSWER / ACKNOWLEDGE / ENCOURAGE]
4. SafetyController Pre-Flight (can_cohost check)
   │
   ▼
5. Context Assembly (Persona + Stream Awareness + Creator Knowledge + Dialogue History)
   │
   ▼
6. Gemini Invocation (Model Router + Quota Fallback)
   │
   ▼
7. Lexical Similarity Check (Jaccard Overlap >= 0.70)
   ├── [High Similarity] ──► 1x Regeneration with Variation Directive
   │
   ▼
8. Response Policy Verification (Length <= 200, Zero Secret Leaks, Moderation Safety)
   │
   ▼
9. SafetyController Dispatch Gate (can_send_chat check)
   │
   ├── [LIVE] ────► LiveChatWriter -> YouTube API
   └── [DRY_RUN] ─► Audit Log / Dashboard Telemetry
```
