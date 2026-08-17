# GODDESS AI 2.0 🌟

> **Next-Generation YouTube Live Multi-Stream Orchestration, Real-Time Moderation, and AI Co-Host Platform**

---

## 📖 Overview

**GODDESS AI 2.0** is an enterprise-grade, asynchronous live streaming management platform built from scratch. It is engineered to monitor and orchestrate up to **4 simultaneous YouTube live streams** (handling 800+ aggregate concurrent viewers), provide **multi-tiered AI moderation**, power an interactive **Gemini AI Co-Host**, and support **Nightbot-style commands**, **Viewer XP/VIP progression**, and modular plug-and-play extensions.

---

## 🏛️ Architecture Highlights

- **Local-First Development**: Built, tested, and verified locally before deployment.
- **YouTube Live & Chat Engine**: Multi-key rotation (up to 4 keys), quota-aware failover, message deduplication, and isolated stream sessions.
- **Gemini AI Engine**: 4-key rotation, token-bucket rate limiter, priority request queue (`HIGH`/`NORMAL`/`LOW`), model router (`gemini-2.5-flash` with `gemini-2.5-flash-lite` fallback), and empty-response classification.
- **Asynchronous Backend**: Python 3.12 + FastAPI + Asyncio + Pydantic v2 Settings.
- **Internal Event Bus**: Asynchronous publish/subscribe decoupled message pipeline.
- **Creator Dashboard**: Next.js 15 + TypeScript + Tailwind CSS with dark slate theme and real-time live telemetry.
- **Honest Status Diagnostics**: Component states clearly distinguish `HEALTHY`, `NOT_CONFIGURED`, `UNAVAILABLE`, `DEGRADED`, and `ERROR`.

---

## 📂 Project Structure

```text
Goddess-AI-2.0/
│
├── backend/                  # Asynchronous FastAPI backend service
│   ├── app/
│   │   ├── api/v1/          # REST & WebSocket API routers
│   │   │   └── endpoints/   # Health, WebSocket, Stream, and AI routers
│   │   ├── core/            # Config (Pydantic), Logging, Event Bus
│   │   ├── services/        # Subsystem services
│   │   │   ├── youtube/     # YouTube Engine (Credentials, Client, Sessions, Chat, Detection)
│   │   │   └── gemini/      # Gemini AI Engine (Credentials, Rate Limiter, Queue, Router, Client, Manager)
│   │   └── main.py          # FastAPI application entrypoint
│   ├── tests/               # Pytest automated test suites (51 unit & integration tests)
│   ├── requirements.txt     # Python dependency lockfile
│   └── pyproject.toml       # Python packaging and test configuration
│
├── frontend/                 # Next.js 15 Creator Dashboard
│   ├── src/
│   │   ├── app/             # Next.js App Router (Layout & Pages)
│   │   ├── components/      # Modular UI components (Health Grid, Controls, Nav, Streams)
│   │   └── lib/             # Typed API client and data models
│   ├── package.json
│   └── tailwind.config.ts
│
├── docs/                     # Comprehensive architecture and setup guides
│   ├── architecture.md      # Architectural design & event bus specs
│   ├── youtube.md           # YouTube engine & credential rotation guide
│   ├── gemini.md            # Gemini AI engine & model router guide
│   ├── setup.md             # Beginner local setup instructions
│   └── roadmap.md           # Master development roadmap
│
├── scripts/                  # Developer helper scripts
│   ├── dev.ps1              # One-click start for backend + frontend
│   └── test.ps1             # One-click test runner
│
├── .env.example              # Environment variables template
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
*(Optional: Add up to 4 YouTube and 4 Gemini API keys in `.env` for live external operations; all automated tests run 100% offline with mocks)*.

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
- Streams REST API: [http://localhost:8000/api/v1/streams](http://localhost:8000/api/v1/streams)
- AI Test API: [http://localhost:8000/api/v1/ai/test](http://localhost:8000/api/v1/ai/test)
- Health Diagnostics: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

#### Frontend Dashboard (Port 3000)
```powershell
cd frontend
npm run dev
```
- Creator Dashboard: [http://localhost:3000](http://localhost:3000)

---

## 🧪 Running Automated Tests

To execute the full Pytest test suite (51 tests across all components):
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
| **Milestone 3** | Phase 5 | 3-Tier Moderation Engine (Rules + Behavioral + Gemini Classification) | ⏳ Next |
| **Milestone 4** | Phase 6 | Interactive AI Co-Host with Personality & Anti-Spam Cooldowns | ⏳ Upcoming |
| **Milestone 5** | Phase 7 | Nightbot-Style Custom Command Engine & Permissions | ⏳ Upcoming |
| **Milestone 6** | Phase 8 & 9 | Viewer XP/VIP Progression & Modular Switchboard | ⏳ Upcoming |
| **Milestone 7** | Phase 1-2, 10-14 | PostgreSQL/Redis Persistence, Creator Dashboard Hardening, GitHub & Railway Deployment | ⏳ Upcoming |
