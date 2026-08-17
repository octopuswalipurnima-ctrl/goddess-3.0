# GODDESS AI 2.0 — Railway Deployment & Operations Playbook

## 1. Deploying to Railway

1. **Create Railway Project**: Connect the GitHub repository or deploy via Railway CLI.
2. **Add PostgreSQL & Redis Plugins**: Provision managed PostgreSQL and Redis plugins in the same Railway project.
3. **Configure Environment Variables**:
   - `DATABASE_URL`: Automatically linked from Postgres plugin.
   - `REDIS_URL`: Automatically linked from Redis plugin.
   - `SECRET_KEY`: Generate via `openssl rand -hex 32`.
   - `YOUTUBE_API_KEY_1`: Configure YouTube API Key.
   - `GEMINI_API_KEY_1`: Configure Gemini API Key.
   - `ENVIRONMENT`: `production`
   - `AUTH_ENABLED`: `true`
4. **Deploy Command**:
   Railway reads `railway.json` and `Procfile`:
   ```bash
   cd backend && alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1
   ```
5. **Health Checks**:
   - Liveness Probe: `GET /api/v1/health/live` (Timeout: 120s)
   - Readiness Probe: `GET /api/v1/health/ready`
