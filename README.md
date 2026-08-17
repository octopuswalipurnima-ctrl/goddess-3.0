# GODDESS AI 2.0 🌟

> **Next-Generation YouTube Live Multi-Stream Orchestration, Real-Time Moderation, AI Co-Host, and Pluggable Extension Platform**

---

## 📖 Overview

**GODDESS AI 2.0** is an enterprise-grade, asynchronous live streaming management platform built from scratch. It is engineered to monitor and orchestrate up to **4 simultaneous YouTube live streams** (handling 800+ aggregate concurrent viewers), provide **multi-tiered AI moderation**, power an interactive **Gemini AI Co-Host**, run **pluggable extension modules** (Chat Commands, Viewer Welcome, Live Stats, Viewer Interaction), and offer a unified **Creator Control Center** with real-time WebSocket telemetry and emergency fail-safes.

---

## 🏛️ Architecture Highlights

- **Local-First Development**: Built, tested, and verified locally before deployment.
- **YouTube Live & Chat Engine**: Multi-key rotation (up to 4 keys), quota-aware failover, message deduplication, and isolated stream sessions.
- **Gemini AI Engine**: 4-key rotation, token-bucket rate limiter, priority request queue (`HIGH`/`NORMAL`/`LOW`), model router (`gemini-2.5-flash` with `gemini-2.5-flash-lite` fallback), and empty-response classification.
- **3-Tier AI Moderation Engine**: High-speed deterministic rules + contextual Gemini AI semantic analysis (`priority=HIGH`) + Action Policy safety gates (kill switch, safe mode, owner/mod exemptions, per-user cooldowns, idempotency).
- **Interactive AI Co-Host Engine**: Rule-first intent detection, bounded short-term memory (20 stream msgs, 5 user msgs), personality framing, Gemini AI (`priority=NORMAL`), max 200-char length capping, anti-spam cooldowns (5s global, 30s user), and DRY_RUN mode.
- **Modular Plugin / Extension System**: Standardized lifecycle (`DISCOVER` &rarr; `REGISTER` &rarr; `LOAD` &rarr; `ENABLE` &rarr; `RUNNING`), dependency graphs, failure isolation, and built-in modules (`commands`, `welcome`, `stream_stats`, `viewer_interaction`).
- **Creator Control Center**: Next.js 15 + TypeScript + Tailwind CSS with dark slate theme, 4-stream live overview, focused stream controls, moderation feed, co-host switchboard, module manager, AI/YouTube diagnostics, bounded activity timeline, and emergency confirmation dialogs.
- **Honest Status Diagnostics**: Component states clearly distinguish `HEALTHY`, `DEGRADED`, `NOT_CONFIGURED`, `UNAVAILABLE`, and `ERROR`.

---

## 📂 Project Structure

```text
Goddess-AI-2.0/
│
├── backend/                  # Asynchronous FastAPI backend service
│   ├── app/
│   │   ├── api/v1/          # REST & WebSocket API routers
│   │   │   └── endpoints/   # Health, Dashboard, Stream, AI, Moderation, Co-Host, Modules, WS
│   │   ├── core/            # Config (Pydantic), Logging, Event Bus
│   │   ├── services/        # Subsystem services
│   │   │   ├── youtube/     # YouTube Engine (Credentials, Client, Sessions, Chat, Detection)
│   │   │   ├── gemini/      # Gemini AI Engine (Credentials, Rate Limiter, Queue, Router, Client, Manager)
│   │   │   ├── moderation/  # AI Moderation Engine (Rules, Classifier, Policy, Actions, Audit, Manager)
│   │   │   └── cohost/      # AI Co-Host Engine (Intents, Context, Persona, Generator, Policy, Cooldowns, Deduplication, Audit, Manager)
│   │   ├── modules/         # Modular Extension System
│   │   │   ├── base.py      # BaseModule contract and lifecycle state machine
│   │   │   ├── registry.py  # Module registry and topological dependency resolution
│   │   │   ├── manager.py   # Module manager with isolated EventBus routing
│   │   │   ├── commands/    # Safe prefix chat commands (!help, !discord, !socials, !rules)
│   │   │   ├── welcome/     # New/returning viewer welcome greetings
│   │   │   ├── stream_stats/# Live stream telemetry counters
│   │   │   └── viewer_interaction/ # Interaction tracking foundation
│   │   └── main.py          # FastAPI application entrypoint
│   ├── tests/               # Pytest automated test suites (125 unit & integration tests)
│   ├── requirements.txt     # Python dependency lockfile
│   └── pyproject.toml       # Python packaging and test configuration
│
├── frontend/                 # Next.js 15 Creator Control Center
│   ├── src/
│   │   ├── app/             # Next.js App Router (Layout & Pages)
│   │   ├── components/      # Modular UI components (Global Health, 4-Stream Overview, Stream Controls, Moderation Center, Co-Host Center, Module Center, Diagnostics, Timeline, Emergency Controls)
│   │   └── lib/             # Centralized WebSocket manager and typed API clients
│   ├── package.json
│   └── tailwind.config.ts
│
├── docs/                     # Comprehensive architecture and setup guides
│   ├── architecture.md      # Architectural design & event bus specs
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
- Dashboard Overview API: [http://localhost:8000/api/v1/dashboard/overview](http://localhost:8000/api/v1/dashboard/overview)
- Modules API: [http://localhost:8000/api/v1/modules](http://localhost:8000/api/v1/modules)
- Health Diagnostics: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

#### Frontend Dashboard (Port 3000)
```powershell
cd frontend
npm run dev
```
- Creator Control Center: [http://localhost:3000](http://localhost:3000)

---

## 🧪 Running Automated Tests

To execute the full Pytest test suite (125 tests across all components):
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
| **Milestone 7** | Phase 9-14 | PostgreSQL/Redis Persistence, Security Hardening, GitHub & Railway Deployment | ⏳ Upcoming |
