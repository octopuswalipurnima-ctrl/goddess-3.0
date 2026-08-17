# GODDESS AI 2.0 — Production Deployment Guide

## Overview
GODDESS AI 2.0 is designed for high-availability deployment on Railway, Docker, Kubernetes, or bare-metal Linux servers.

---

## 1. Production Architecture
```
[ YouTube Live Streams (x4) ]  <--->  [ GODDESS AI 2.0 Backend (FastAPI) ]  <--->  [ Next.js Dashboard ]
                                                    |
                                  +-----------------+-----------------+
                                  |                                   |
                         [ PostgreSQL DB ]                    [ Redis Cache ]
                      (Persistent Config & Audits)         (Cooldowns & Deduplication)
```

---

## 2. Deploying on Railway

### Prerequisites
1. PostgreSQL database provisioned on Railway.
2. Redis instance provisioned on Railway (optional; automatic local in-memory fallback if absent).
3. YouTube Data API v3 and Google Gemini API keys.

### Deployment Configuration (`railway.json`)
The root `railway.json` defines the deployment lifecycle:
- **Build**: Uses Nixpacks for Python 3.12 / Node.js build.
- **Deploy Start Command**:
  ```bash
  cd backend && alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1
  ```
- **Healthcheck Path**: `/api/v1/health/live`
- **Restart Policy**: `ON_FAILURE` (Max retries: 5)

---

## 3. Environment Variables

| Variable | Required | Example |
|---|:---:|---|
| `ENVIRONMENT` | Yes | `production` |
| `SECRET_KEY` | Yes | `64_char_hex_secret_key` |
| `DATABASE_URL` | Yes | `postgresql+asyncpg://user:pass@host:5432/db` |
| `REDIS_URL` | Optional | `redis://default:pass@host:6379/0` |
| `YOUTUBE_API_KEYS` | Yes | `AIzaSy...,AIzaSy...` |
| `GEMINI_API_KEYS` | Yes | `AIzaSy...,AIzaSy...` |
| `CORS_ORIGINS` | Yes | `["https://dashboard.yourdomain.com"]` |
| `BOOTSTRAP_CREATOR_USERNAME` | Yes | `creator` |
| `BOOTSTRAP_CREATOR_PASSWORD` | Yes | `InitialStrongPassword!` |

---

## 4. Health Probes
- **Liveness Probe**: `GET /api/v1/health/live` — Returns HTTP 200 if process is active.
- **Readiness Probe**: `GET /api/v1/health/ready` — Returns HTTP 200 (`READY`) or HTTP 503 (`NOT_READY`) if database is unreachable.
- **Honest Diagnostics**: `GET /api/v1/health` — Full subsystem breakdown with zero secret exposure.
