# AI Co-Host Engine Architecture & Operations Guide

## 1. Overview

The **Interactive AI Co-Host Engine** in GODDESS AI 2.0 provides an engaging, personality-driven conversational partner for live streams. It operates **completely independently** from the AI Moderation Engine, with isolated state, policies, prompts, cooldowns, and metrics.

---

## 2. Co-Host Architecture

```text
YouTube Live Chat
        │
        ▼
CHAT_MESSAGE Event (Event Bus)
        │
        ├──────────────────────────────┐
        │                              │
        ▼                              ▼
Moderation Engine (Milestone 3)    Co-Host Engine (Milestone 4)
(Independent State, Policy, Audit)    │
                                      ▼
                              Message Pre-Processor (CoHostMessage)
                                      │
                                      ▼
                              Intent Detection (Rule-First + Calibrated Confidence)
                                      │
                              ┌───────┴────────┐
                              │                │
                              ▼                ▼
                           IGNORE          RESPOND
                                               │
                                               ▼
                                      Context Manager (Per-Stream [20] & Per-User [5])
                                               │
                                               ▼
                                      Personality Manager (Tone, Style, Safety Overrides)
                                               │
                                               ▼
                                      Gemini AI Engine (priority = NORMAL)
                                               │
                                               ▼
                                      Response Validator & Safety Filter (max 200 chars)
                                               │
                                               ▼
                                      Response Policy Gate:
                                        ├── Master Enabled? (Default: False)
                                        ├── Emergency Stop? (Default: False)
                                        ├── Intent Allowed? (Mentions, Questions, Relevant)
                                        ├── Confidence >= Minimum? (Default: 0.70)
                                        ├── Global Cooldown (5s default)
                                        ├── Per-User Cooldown (30s default)
                                        ├── Stream Rate Limit (12 responses/min)
                                        ├── Per-User Limit (3 responses/window)
                                        └── Duplicate Response Filter
                                               │
                                      ┌────────┴────────┐
                                      ▼                 ▼
                                   BLOCK              APPROVE
                                                         │
                                                    DRY RUN?
                                                         │
                                                  ┌──────┴──────┐
                                                  ▼             ▼
                                                 YES            NO
                                                  │             │
                                                  ▼             ▼
                                             ActionStatus:   YouTube Chat
                                               DRY_RUN      (Existing YouTube Engine)
                                                  │             │
                                                  └──────┬──────┘
                                                         │
                                                         ▼
                                                    Audit Log & Event Bus
                                                         │
                                                         ▼
                                                    Dashboard WebSocket
```

---

## 3. Operational Rules & Guardrails

- **Opt-In by Default**: Default config has `enabled = False`, `dry_run = True`, `emergency_stop = False`.
- **Bounded Context Memory**:
  - `context_window_size = 20` messages per stream.
  - `user_context_window_size = 5` interactions per user.
- **Length Constraint**: Responses are strictly limited to `max_response_length = 200` characters.
- **Priority Protection**: Co-Host uses `AIRequestPriority.NORMAL`, ensuring Moderation (`HIGH` priority) is never starved.
- **No Command Execution**: `COMMAND_REQUEST` intent is recognized for routing only. Gemini output is strictly treated as untrusted text. No shell, backend, or moderation commands are ever executed.
- **Multi-Stream Isolation**: Context, cooldowns, deduplication history, metrics, and persona settings are strictly partitioned by `stream_id`.

---

## 4. REST API Endpoints

| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/cohost/config/{stream_id}` | Retrieve stream Co-Host configuration and persona |
| `PUT` | `/api/v1/cohost/config/{stream_id}` | Update settings (enable, dry_run, emergency stop, persona, cooldowns) |
| `GET` | `/api/v1/cohost/audit/{stream_id}` | Fetch recent Co-Host audit records |
| `GET` | `/api/v1/cohost/stats` | Global Co-Host metrics |
| `POST` | `/api/v1/cohost/test` | Dry-run simulate a chat message evaluation and generated reply |

---

## 5. Offline Testing

All unit and integration tests run **100% offline** with mock transports:
```powershell
cd "D:\GODDESS AI 2.0"
.\scripts\test.ps1
```
