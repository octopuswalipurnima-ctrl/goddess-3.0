# GODDESS AI 2.0 — Production Launch Runbook

## 1. Pre-Flight Launch Sequence
1. Verify Railway environment configuration:
   - `ENVIRONMENT=production`
   - `DEBUG=false`
   - `SECRET_KEY` (32+ characters, cryptographically secure)
   - `DATABASE_URL` (PostgreSQL asyncpg connection string)
   - `REDIS_URL` (Redis connection string)
   - `YOUTUBE_API_KEY_1`..`4` (YouTube Data API v3 keys)
   - `GEMINI_API_KEY_1`..`4` (Google Gemini AI keys)
   - `CORS_ORIGINS` (Dashboard URL)
2. Execute migration deployment: `alembic upgrade head`.
3. Launch backend process: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1`.
4. Monitor `/api/v1/health/detailed` to confirm all components are `HEALTHY`.
5. Access Creator Control Center dashboard.
