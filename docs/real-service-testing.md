# GODDESS AI 2.0 — Real-Service Testing Guide

## 1. Safety Principles & Opt-In Rules

To prevent accidental quota depletion, API charges, or automated chatter on live public streams, all real-service tests are **FAIL-SAFE & DISABLED BY DEFAULT**.

Every real-service test requires explicit environment opt-in flags:

| Flag | Target Service | Requirement / Guard |
|---|---|---|
| `RUN_REAL_POSTGRES_TEST=true` | PostgreSQL Database | Active `DATABASE_URL` |
| `RUN_REAL_REDIS_TEST=true` | Redis Cache & PubSub | Active `REDIS_URL` |
| `RUN_REAL_GEMINI_TEST=true` | Google Gemini AI | Valid `GEMINI_API_KEY_1` |
| `RUN_REAL_YOUTUBE_TEST=true` | YouTube Data API v3 | `TEST_REAL_YOUTUBE_VIDEO_ID` & `YOUTUBE_API_KEY_1` |
| `RUN_REAL_WEBSOCKET_TEST=true` | Live WebSocket Telemetry | Running backend server |
| `RUN_RAILWAY_E2E_TEST=true` | Full 4-Stream Railway Stack | Production staging environment |

## 2. Executing Real-Service Validation

### 2.1 Gemini AI API Validation
```powershell
$env:RUN_REAL_GEMINI_TEST="true"
& "D:\GODDESS AI 2.0\backend\.venv\Scripts\pytest.exe" -v tests/test_real_service_e2e/test_real_gemini.py
```

### 2.2 YouTube Live Controlled Stream Validation
```powershell
$env:RUN_REAL_YOUTUBE_TEST="true"
$env:TEST_REAL_YOUTUBE_VIDEO_ID="dQw4w9WgXcQ"
& "D:\GODDESS AI 2.0\backend\.venv\Scripts\pytest.exe" -v tests/test_real_service_e2e/test_real_youtube.py
```

### 2.3 PostgreSQL & Redis Validation
```powershell
$env:RUN_REAL_POSTGRES_TEST="true"
$env:RUN_REAL_REDIS_TEST="true"
& "D:\GODDESS AI 2.0\backend\.venv\Scripts\pytest.exe" -v tests/test_real_service_e2e/test_real_postgres.py tests/test_real_service_e2e/test_real_redis.py
```

## 3. Guarantees Enforced During Real Tests
1. **Never use production public streams**: Only designated unlisted/private test streams.
2. **Never print secrets**: All logs, assertions, and test output mask credentials with safe aliases (`KEY-1`..`KEY-4`).
3. **No Historical Replay**: Reconnects and unpauses only consume newly arriving messages.
