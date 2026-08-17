# GODDESS AI 2.0 — Railway Production Runbook

## 1. Deployment Overview

- **Platform**: Railway (NIXPACKS Builder)
- **Start Command**: `cd backend && alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1`
- **Healthcheck Path**: `/api/v1/health/live`
- **Healthcheck Timeout**: 120 seconds
- **Restart Policy**: `ON_FAILURE` (Max retries: 5)

## 2. Mandatory Production Environment Variables
| Variable | Example / Description |
|---|---|
| `ENVIRONMENT` | `production` |
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@host:port/db` |
| `REDIS_URL` | `redis://default:pass@host:port/0` |
| `SECRET_KEY` | 32+ character cryptographically secure key |
| `CORS_ORIGINS` | `["https://dashboard.goddessai.app"]` |
| `YOUTUBE_API_KEY_1` | Primary YouTube API key |
| `GEMINI_API_KEY_1` | Primary Gemini API key |
| `AUTH_ENABLED` | `true` |
| `AUTH_DEV_BYPASS` | `false` |
| `DEBUG` | `false` |

## 3. Operational Health Probes
- **Liveness**: `GET /api/v1/health/live` (returns 200 if process is up).
- **Readiness**: `GET /api/v1/health/ready` (returns 200 only if DB and dependencies are ready).
- **Diagnostics**: `GET /api/v1/health/detailed` (full zero-secret component health).
