# YouTube Engine Architecture & Operations Guide

## 1. Overview

The **YouTube Engine** in GODDESS AI 2.0 provides centralized, quota-aware orchestration for up to **4 simultaneous YouTube live streams**. It operates as an asynchronous event producer, isolating raw YouTube Data API interactions and publishing normalized events (`STREAM_CONNECTED`, `CHAT_MESSAGE`, `STREAM_ENDED`) to the internal `EventBus`.

---

## 2. Multi-Key Credential Rotation

- **Configuration Slots**: Supports up to 4 rotated keys (`YOUTUBE_API_KEY_1`, `YOUTUBE_API_KEY_2`, `YOUTUBE_API_KEY_3`, `YOUTUBE_API_KEY_4`).
- **Quota Failover**: When YouTube returns HTTP 403 (`quotaExceeded`) or HTTP 429 (`rateLimitExceeded`), the manager automatically marks the active key into `COOLDOWN` (default: 5 minutes for quota errors) and switches immediately to the next available credential.
- **Recovery**: When a key's cooldown timestamp expires, it is automatically restored to `AVAILABLE` on the next request.
- **Secret Redaction**: Raw keys are never written to log files or returned in API responses. Safe identifiers (e.g. `youtube-key-1`) are used everywhere.

---

## 3. Multi-Stream Isolation Architecture

```text
StreamManager (Capacity: 4 concurrent streams)
  │
  ├── StreamSession [Stream A] (LIVE)
  │     └── LiveChatReader (Polling Loop + 5,000 Message Dedup Buffer)
  │
  ├── StreamSession [Stream B] (LIVE)
  │     └── LiveChatReader (Polling Loop + 5,000 Message Dedup Buffer)
  │
  ├── StreamSession [Stream C] (STANDBY)
  │
  └── StreamSession [Stream D] (STANDBY)
```

- **Fault Isolation**: An error or network drop in Stream A only affects Stream A. Streams B, C, and D continue executing uninterrupted.
- **Duplicate Protection**: Creating a second session for an already active stream ID is rejected with `DuplicateStreamError`.
- **Capacity Enforcement**: Adding more than 4 concurrent streams is rejected with `MaxStreamsReachedError`.

---

## 4. Live Chat Reader & Deduplication

- **Polling Rate**: Dynamically respects `pollingIntervalMillis` returned by YouTube Live Chat API (clamped to $\ge 1.0$s safe minimum).
- **Deduplication Buffer**: LRU cache storing the latest 5,000 message IDs. Overlapping poll batches and reconnects will never republish duplicate `CHAT_MESSAGE` events.
- **Exponential Backoff**: When network drops occur, the reader retries with backoff delays (1s, 2s, 4s, 8s, up to 30s max).
- **Clean Teardown**: When a stream ends, background tasks are cancelled cleanly with zero task leaks.

---

## 5. REST & WebSub Endpoints

| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/streams` | List active stream sessions and real-time metrics |
| `GET` | `/api/v1/streams/{stream_id}` | Get specific stream session detail |
| `POST` | `/api/v1/streams` | Connect and start a new live stream session |
| `POST` | `/api/v1/streams/{stream_id}/stop` | Disconnect and stop live stream session |
| `POST` | `/api/v1/streams/{stream_id}/chat` | Post a text message to YouTube live chat (max 200 chars) |
| `GET` | `/api/v1/streams/webhook` | WebSub (PubSubHubbub) challenge verification |
| `POST` | `/api/v1/streams/webhook` | WebSub Atom XML notification ingestion |

---

## 6. Testing Offline Without Real API Keys

All automated unit and integration tests run **100% offline** using mock transports:
```powershell
cd "D:\GODDESS AI 2.0"
.\scripts\test.ps1
```
