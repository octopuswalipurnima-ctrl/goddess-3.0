# GODDESS AI 2.0 🌟

> **Next-Generation YouTube Live Multi-Stream Orchestration, Real-Time Moderation, AI Co-Host, Pluggable Extension Platform & Production Persistence**

---

## 📖 Overview

**GODDESS AI 2.0** is an enterprise-grade, asynchronous live streaming management platform built from scratch. It is engineered to monitor and orchestrate up to **4 simultaneous YouTube live streams** (handling 800+ aggregate concurrent viewers), provide **multi-tiered AI moderation**, power an interactive **Gemini AI Co-Host**, run **pluggable extension modules** (Chat Commands, Viewer Welcome, Live Stats, Viewer Interaction), maintain an asynchronous **PostgreSQL & Redis persistence and reliability layer**, and offer a unified **Creator Control Center** with real-time WebSocket telemetry and emergency fail-safes.

---

## 🏛️ Architecture Highlights

- **Local-First Development**: Built, tested, and verified locally before deployment.
- **YouTube Live & Chat Engine**: Multi-key rotation (up to 4 keys), quota-aware failover, message deduplication, and isolated stream sessions.
- **Gemini AI Engine**: 4-key rotation, token-bucket rate limiter, priority request queue (`HIGH`/`NORMAL`/`LOW`), model router (`gemini-2.5-flash` with `gemini-2.5-flash-lite` fallback), and empty-response classification.
- **3-Tier AI Moderation Engine**: High-speed deterministic rules + contextual Gemini AI semantic analysis (`priority=HIGH`) + Action Policy safety gates (kill switch, safe mode, owner/mod exemptions, per-user cooldowns, idempotency).
- **Interactive AI Co-Host Engine**: Rule-first intent detection, bounded short-term memory (20 stream msgs, 5 user msgs), personality framing, Gemini AI (`priority=NORMAL`), max 200-char length capping, anti-spam cooldowns (5s global, 30s user), and DRY_RUN mode.
- **Modular Plugin / Extension System**: Standardized lifecycle (`DISCOVER` &rarr; `REGISTER` &rarr; `LOAD` &rarr; `ENABLE` &rarr; `RUNNING`), dependency graphs, failure isolation, and built-in modules (`commands`, `welcome`, `stream_stats`, `viewer_interaction`).
- **Security & RBAC Layer**: PBKDF2 password hashing, HS256 JWT tokens, 4-tier RBAC (`OWNER`, `ADMIN`, `OPERATOR`, `VIEWER`), security response headers, request IDs, rate limiting, and zero credential leakage.
- **Production Persistence & Reliability Layer**: PostgreSQL async (SQLAlchemy 2.x + asyncpg) source of truth, Alembic migrations, typed repositories, transient Redis state manager with safe in-memory fallback, restart recovery, and bounded audit retention.
- **Creator Control Center**: Next.js 15 + TypeScript + Tailwind CSS with dark slate theme, 4-stream live overview, focused stream controls, moderation feed, co-host switchboard, module manager, AI/YouTube/Persistence diagnostics, bounded activity timeline, emergency confirmation dialogs, and creator authentication.
- **Honest Status Diagnostics**: Component states clearly distinguish `HEALTHY`, `DEGRADED`, `NOT_CONFIGURED`, `UNAVAILABLE`, and `ERROR` across `/health`, `/health/live`, and `/health/ready`.

---

## 📂 Project Structure

```text
Goddess-AI-2.0/
│
├── backend/                  # Asynchronous FastAPI backend service
│   ├── alembic/             # Alembic database migrations & environment
│   ├── app/
│   │   ├── api/v1/          # REST & WebSocket API routers (Auth, Health, Streams, Moderation, Co-Host, Modules, Dashboard, WS)
│   │   ├── auth/            # Security & Auth subsystem (RBAC, JWT, Hashing, Middleware, Dependencies)
│   │   ├── core/            # Config, Logging, Event Bus, Redis State Manager, Rate Limiter
│   │   ├── db/              # SQLAlchemy 2.0 async base, session, models, repositories, recovery, retention
│   │   ├── services/        # Subsystem services (YouTube, Gemini, Moderation, Co-Host)
│   │   ├── modules/         # Modular Extension System (Commands, Welcome, Stats, Interaction)
│   │   └── main.py          # FastAPI application entrypoint with lifespan manager
│   ├── tests/               # Pytest automated test suites (182 unit, security, & integration tests)
│   ├── requirements.txt     # Python dependency lockfile
│   ├── alembic.ini          # Alembic configuration
│   └── pyproject.toml       # Python packaging and test configuration
│
├── frontend/                 # Next.js 15 Creator Control Center
│   ├── src/
│   │   ├── app/             # Next.js App Router (Layout & Pages)
│   │   ├── components/      # Modular UI components (Auth, Health, 4-Stream, Controls, Moderation, Co-Host, Modules, Diagnostics, Timeline, Emergency)
│   │   └── lib/             # Centralized WebSocket manager, typed API clients, and Auth context
│   ├── package.json
│   └── tailwind.config.ts
│
├── docs/                     # Comprehensive architecture and setup guides
│   ├── architecture.md      # Architectural design & event bus specs
│   ├── security.md          # Security architecture, zero-leakage policies & headers
│   ├── authentication.md    # RBAC matrix, token lifecycle & endpoints
│   ├── deployment.md        # Railway & cloud production deployment guide
│   ├── operations.md        # Operations runbook & emergency procedures
│   ├── reliability.md       # Failover, recovery & resilience guide
│   ├── persistence.md       # PostgreSQL, Redis, recovery, and retention guide
│   ├── youtube.md           # YouTube engine & credential rotation guide
│   ├── gemini.md            # Gemini AI engine & model router guide
│   ├── moderation.md        # 3-tier moderation engine & safety gates guide
│   ├── cohost.md            # Interactive AI co-host & personality guide
│   ├── modules.md           # Pluggable module system guide
│   ├── dashboard.md         # Creator control center guide
│   ├── setup.md             # Beginner local setup instructions
│   └── roadmap.md           # Master development roadmap
│
├── scripts/                  # Developer helper scripts
│   ├── dev.ps1              # One-click start for backend + frontend
│   └── test.ps1             # One-click test runner
│
├── .env.example              # Environment variables template
├── railway.json              # Railway production deployment configuration
├── .gitignore                # Git ignore rules protecting secrets & builds
└── README.md                 # Project root documentation
```

---

## 🚀 Quick Start Guide (Local Development)

### 1. Prerequisites
- **Python**: Version 3.11 or 3.12
- **Node.js**: Version 20+ LTS
- **Git**: Installed locally

### 2. Environment Setup
Copy the environment template:
```powershell
cp .env.example .env
```
*(Optional: Configure `DATABASE_URL` and `REDIS_URL` for production PostgreSQL/Redis instances; all automated tests run 100% offline with in-memory SQLite and local fail-safe state)*.

### 3. Run Everything with One Command
Run the helper script from PowerShell:
```powershell
.\scripts\dev.ps1
```

Or run services individually:

#### Backend (Port 8000)
```powershell
cd backend
.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
- Interactive API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Dashboard Overview API: [http://localhost:8000/api/v1/dashboard/overview](http://localhost:8000/api/v1/dashboard/overview)
- Health Diagnostics: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)
- Liveness Probe: [http://localhost:8000/api/v1/health/live](http://localhost:8000/api/v1/health/live)
- Readiness Probe: [http://localhost:8000/api/v1/health/ready](http://localhost:8000/api/v1/health/ready)

#### Frontend Dashboard (Port 3000)
```powershell
cd frontend
npm run dev
```
- Creator Control Center: [http://localhost:3000](http://localhost:3000)

---

## 🧪 Running Automated Tests

To execute the full Pytest test suite (396 tests across all components):
```powershell
.\scripts\test.ps1
```

---

## 🗺️ Milestone Roadmap

| Milestone | Phase | Description | Status |
| :--- | :--- | :--- | :--- |
| **Milestone 0** | Phase 0 | Local Foundation, FastAPI Core, Next.js Dashboard Shell, Honest Health Diagnostics, Pytest Suite | ✅ Completed |
| **Milestone 1** | Phase 3 | YouTube Live Engine, 4-Key Quota Rotation, Isolated Stream Sessions, Chat Deduplication | ✅ Completed |
| **Milestone 2** | Phase 4 | Centralized Gemini AI Engine, 4-Key Rotation, Rate Limiter, Priority Queue, Flash/Flash-Lite Router | ✅ Completed |
| **Milestone 3** | Phase 5 | 3-Tier Moderation Engine (Rules + Behavioral + Gemini Classification), Kill Switch, Safe Mode | ✅ Completed |
| **Milestone 4** | Phase 6 | Interactive AI Co-Host Engine (Intents, 20-Msg Context, Persona, Cooldowns, Normal Priority) | ✅ Completed |
| **Milestone 5** | Phase 7 | Modular Module System (BaseModule, Registry, Manager, Commands, Welcome, Stats, Interaction) | ✅ Completed |
| **Milestone 6** | Phase 8 | Creator Control Center & Real-Time Dashboard (4-Stream Overview, Stream Controls, Diagnostics) | ✅ Completed |
| **Milestone 7** | Phase 9 | Production Persistence & Reliability Layer (PostgreSQL, Repositories, Redis, Recovery, Retention) | ✅ Completed |
| **Milestone 8** | Phase 10 | Production Security, Authentication, Deployment & End-to-End Reliability | ✅ Completed |
| **Milestone 9** | Phase 11 | Production Readiness, Multi-Stream Load Testing & Reliability Engine (218 tests) | ✅ Completed |
| **Milestone 10A** | Phase 12 | YouTube & Gemini Multi-Key Credential & Quota Management (239 tests) | ✅ Completed |
| **Milestone 10B** | Phase 13 | Real YouTube Live Integration & Reconnection Engine (267 tests) | ✅ Completed |
| **Milestone 10C** | Phase 14 | Production Live Operations, Stream Supervisor & Creator Control Center (296 tests) | ✅ Completed |
| **Milestone 11** | Phase 15 | Production AI Intelligence Layer & Real-Service Integration Audit (324 tests) | ✅ Completed |
| **Milestone 12** | Phase 16 | Production Deployment, Real-Service E2E Validation & Operational Hardening (339 tests) | ✅ Completed |
| **Milestone 13** | Phase 17 | Adaptive Co-Host Intelligence & Engagement Layer (370 tests) | ✅ Completed |
| **Milestone 14** | Phase 18 | Production Creator Control Center, Operational Observability & Real-Service Validation (396 tests) | ✅ Completed |


