# AI Moderation Engine Architecture & Operations Guide

## 1. Overview

The **AI Moderation Engine** in GODDESS AI 2.0 provides safety-first, multi-tiered live chat analysis. It separates **analysis** from **action execution**, ensuring that raw AI outputs never directly execute destructive moderation actions without passing through the **Action Policy Gate**.

---

## 2. Multi-Tiered Architecture

```text
YouTube Live Chat
      ↓
CHAT_MESSAGE Event (Event Bus)
      ↓
Moderation Pre-Processor (Role extraction, text normalization)
      ↓
Tier 1: High-Speed Rule Engine (Flood burst, repeated messages, suspicious URLs, scam regex)
      ↓ (If rule matches: Immediate decision with evidence-calibrated confidence)
      ↓ (If rule uncertain: Contextual AI required)
Tier 2/3: Gemini AI Semantic Classifier (via GeminiAIManager with HIGH priority)
      ↓
Moderation Decision (Category, Confidence 0.0-1.0, Severity, Reason, Recommended Action)
      ↓
Action Policy Gate:
  ├── Master Enable Active?
  ├── Emergency Kill Switch Active? (Instantly halts automated actions)
  ├── Automatic Circuit Breaker Active? (Tripped on action storm bursts)
  ├── Safe Mode Active? (Restricts to rule-only actions)
  ├── User Exempt? (Channel Owner / Moderator / Member)
  ├── Confidence >= Configured Threshold? (e.g. >= 0.80)
  ├── User Action Cooldown Active? (10s default)
  └── Stream Rate Limit Exceeded? (Max 30/min)
      ↓
Moderation Action Approval or Rejection
      ↓
DRY_RUN / Execution Decision:
  ├── If DRY_RUN: Record action_status = DRY_RUN (Skip YouTube execution)
  └── If Live: YouTube Moderation Executor (Idempotency Key: stream_id:message_id:action)
      ↓
Audit Log & Event Bus Dispatch (MODERATION_DECISION_CREATED, MODERATION_ACTION_EXECUTED)
      ↓
WebSocket Broadcast to Dashboard Live Feed
```

---

## 3. Pre-Implementation Architectural Guarantees

### A. AI Failure != Safe
- An AI failure (timeout, quota limit, parse failure) is classified as `category = ANALYSIS_FAILED` with `confidence = 0.0`.
- The audit system clearly distinguishes:
  - `SAFE`: AI or rules verified the message is harmless.
  - `ANALYSIS_FAILED`: Analysis could not be completed.
  - Failures NEVER masquerade as safe, and NEVER trigger destructive automated actions.

### B. Calibrated Rule Confidence & URL Distinction
- Normal links (`youtube.com`, `google.com`, `github.com`, `twitch.tv`) are recognized and NOT classified as malicious.
- Only genuinely suspicious TLDs (`.xyz`, `.top`, `.tk`, `.ru`), raw IP addresses, and phishing invites trigger `MALICIOUS_LINK`.
- Flood and repetition rules produce evidence-calibrated confidence scores.

### C. Dry-Run Mode
- Per-stream toggle (`dry_run = True`).
- All rules, AI classification, confidence checks, and policy gates execute normally.
- If approved, records `action_status = DRY_RUN` in audit log and dashboard, bypassing YouTube API calls.

### D. Automatic Action Circuit Breaker
- In addition to manual kill switches, an automatic circuit breaker monitors action bursts (e.g. $\ge 10$ actions in $10$ seconds).
- When tripped, automated actions halt immediately while preservation of analysis and decision logging continues.
- Isolated per stream and requires explicit creator reset via dashboard or API (`POST /api/v1/moderation/circuit-breaker/reset/{stream_id}`).

---

## 4. REST API Endpoints

| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/moderation/config/{stream_id}` | Retrieve stream moderation settings |
| `PUT` | `/api/v1/moderation/config/{stream_id}` | Update settings (kill switch, safe mode, dry-run, automation) |
| `POST` | `/api/v1/moderation/circuit-breaker/reset/{stream_id}` | Reset tripped automatic circuit breaker |
| `GET` | `/api/v1/moderation/audit/{stream_id}` | Fetch recent audit records |
| `GET` | `/api/v1/moderation/stats` | Global moderation metrics |
| `POST` | `/api/v1/moderation/test` | Dry-run evaluate test message without executing actions |

---

## 5. Offline Testing

All unit and integration tests run **100% offline** with mock transports:
```powershell
cd "D:\GODDESS AI 2.0"
.\scripts\test.ps1
```
