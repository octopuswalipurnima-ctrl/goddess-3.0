# Gemini AI Engine Architecture & Operations Guide

## 1. Overview

The **Gemini AI Engine** in GODDESS AI 2.0 provides centralized, asynchronous, rate-limited, and quota-rotated generative AI capabilities. It isolates low-level Google Gemini REST API v1beta communication and provides a normalized `AIRequest` &rarr; `AIResponse` pipeline for upcoming modules (AI Moderation, AI Co-Host, Custom Commands).

---

## 2. Multi-Key Credential Management

- **Configuration Slots**: Supports up to 4 rotated keys (`GEMINI_API_KEY_1`, `GEMINI_API_KEY_2`, `GEMINI_API_KEY_3`, `GEMINI_API_KEY_4`).
- **Safe Identifiers**: Safe IDs (`gemini-key-1` .. `4`) are used throughout diagnostics and logs with zero raw key leakage.
- **Failover & Cooldowns**: When a 403 (`quotaExceeded`) or 429 (`rateLimitExceeded`) is encountered, the key is placed in cooldown (default: 5 minutes for quota errors) and the manager automatically rotates to the next available key.
- **Automatic Cooldown Recovery**: When a key's cooldown timestamp expires, it is automatically restored to `AVAILABLE` on subsequent requests.

---

## 3. Request Lifecycle Pipeline

```text
AI Request (AIRequest with stream_id, priority, prompt)
      ↓
[EventBus: AI_REQUEST_CREATED]
      ↓
Priority Request Queue (HIGH -> NORMAL -> LOW, max size: 100, max concurrency: 2)
      ↓
Token Bucket Rate Limiter (capacity: 5, refill: 0.5 req/s)
      ↓
Credential Selector (Round-robin across available keys)
      ↓
Model Router (Primary: gemini-2.5-flash -> Fallback: gemini-2.5-flash-lite)
      ↓
Async Gemini Client (HTTPX POST /v1beta/models/{model}:generateContent)
      ↓
Response Validation & Emptiness Classification
      ↓
Normalized AIResponse (SUCCESS, EMPTY_RESPONSE, TIMEOUT, RATE_LIMITED, etc.)
      ↓
[EventBus: AI_REQUEST_COMPLETED / AI_REQUEST_FAILED]
```

---

## 4. Model Routing & Fallback Policies

| Error Type | Behavior | Fallback Action |
| :--- | :--- | :--- |
| **503 Service Unavailable / Overloaded** | Model capacity issue | Fall back to `gemini-2.5-flash-lite` |
| **Model Not Found (404)** | Model name error | Fall back to `gemini-2.5-flash-lite` |
| **Empty Candidate Parts** | Generation blocked/empty | Fall back to `gemini-2.5-flash-lite` or return `EMPTY_RESPONSE` |
| **Quota Exceeded (403)** | Credential limit reached | Rotate to next key (`gemini-key-X`), keep same model |
| **Rate Limited (429)** | Frequency spike | Delay with backoff, rotate key, keep same model |
| **Invalid Request (400)** | Bad prompt structure | Return `INVALID_REQUEST` immediately without retry |
| **Unauthorized (401)** | Bad API key | Return `AUTH_ERROR` immediately |

---

## 5. Multi-Stream Isolation

- Every request mandates a `stream_id`.
- Requests, responses, and token usages are mapped to their originating `stream_id`.
- Errors or delays in Stream A never contaminate or block requests from Stream B, C, or D.

---

## 6. Development Testing Endpoint

| Method | Path | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/ai/test` | Submit test prompt to verify rate limiter, model router, and response formatting |
| `GET` | `/api/v1/health` | Inspect honest Gemini credential states and queue metrics |

---

## 7. Testing Offline Without Real API Keys

All automated unit and integration tests execute **100% offline** using mock transports and fake responses:
```powershell
cd "D:\GODDESS AI 2.0"
.\scripts\test.ps1
```
