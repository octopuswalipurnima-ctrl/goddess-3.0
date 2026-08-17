# GODDESS AI 2.0 — Operations & Runbook

## 1. Local Development Quickstart

### Backend
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### Frontend (Creator Dashboard)
```bash
cd frontend
npm install
npm run dev
```

---

## 2. Emergency Operations

### Triggering Stream Emergency Stop
If an issue occurs during a live stream:
1. Open the **Creator Control Center**.
2. Click **Emergency Halt** in the top navigation bar or under Moderation / Co-Host controls.
3. Automated YouTube actions and AI responses are immediately blocked for that stream.
4. Or trigger via API:
   ```bash
   curl -X PUT http://127.0.0.1:8000/api/v1/moderation/config/<stream_id> \
     -H "Authorization: Bearer <ADMIN_OR_OWNER_TOKEN>" \
     -H "Content-Type: application/json" \
     -d '{"kill_switch": true}'
   ```

### Resetting Tripped Circuit Breakers
If an unexpected action storm tripped the automated circuit breaker:
```bash
curl -X POST http://127.0.0.1:8000/api/v1/moderation/circuit-breaker/reset/<stream_id> \
  -H "Authorization: Bearer <ADMIN_OR_OWNER_TOKEN>"
```

---

## 3. Database Migration Management
- Create a new migration revision:
  ```bash
  alembic revision --autogenerate -m "description_of_change"
  ```
- Upgrade database to head:
  ```bash
  alembic upgrade head
  ```
- Downgrade database by 1 version:
  ```bash
  alembic downgrade -1
  ```
