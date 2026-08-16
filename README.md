# GODDESS AI 2.0 🌟

> **Next-Generation YouTube Live Multi-Stream Orchestration, Real-Time Moderation, and AI Co-Host Platform**

---

## 📖 Overview

**GODDESS AI 2.0** is an enterprise-grade, asynchronous live streaming management platform built from scratch. It is engineered to monitor and orchestrate up to **4 simultaneous YouTube live streams** (handling 800+ aggregate concurrent viewers), provide **multi-tiered AI moderation**, power an interactive **Gemini AI Co-Host**, and support **Nightbot-style commands**, **Viewer XP/VIP progression**, and modular plug-and-play extensions.

---

## 🏛️ Architecture Highlights

- **Local-First Development**: Built, tested, and verified locally before deployment.
- **Asynchronous Backend**: Python 3.12 + FastAPI + Asyncio + Pydantic v2 Settings.
- **Centralized Credential Rotation**: Support for up to 4 rotated YouTube Data API keys and 4 rotated Gemini AI keys with quota-awareness.
- **Internal Event Bus**: Asynchronous publish/subscribe decoupled message pipeline.
- **Creator Dashboard**: Next.js 15 + TypeScript + Tailwind CSS with dark slate theme and real-time live telemetry.
- **Honest Status Diagnostics**: Component states clearly distinguish `HEALTHY`, `NOT_CONFIGURED`, `UNAVAILABLE`, and `ERROR`.

---

## 📂 Project Structure

```text
Goddess-AI-2.0/
│
├── backend/                  # Asynchronous FastAPI backend service
│   ├── app/
│   │   ├── api/v1/          # REST & WebSocket API routers
│   │   │   └── endpoints/   # Health check, WebSocket, Stream routers
│   │   ├── core/            # Config (Pydantic), Logging, Event Bus
│   │   └── main.py          # FastAPI application entrypoint
│   ├── tests/               # Pytest automated test suites
│   ├── requirements.txt     # Python dependency lockfile
│   └── pyproject.toml       # Python packaging and test configuration
│
├── frontend/                 # Next.js 15 Creator Dashboard
│   ├── src/
│   │   ├── app/             # Next.js App Router (Layout & Pages)
│   │   ├── components/      # Modular UI components (Health Grid, Controls, Nav)
│   │   └── lib/             # Typed API client and data models
│   ├── package.json
│   └── tailwind.config.ts
│
├── docs/                     # Comprehensive architecture and setup guides
│   ├── architecture.md      # Architectural design & event bus specs
│   ├── setup.md             # Beginner local setup instructions
│   └── roadmap.md           # 14-Phase development roadmap
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
*(Optional for Milestone 0: YouTube and Gemini API keys can be added to `.env` whenever available)*.

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
- Health Diagnostics: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

#### Frontend Dashboard (Port 3000)
```powershell
cd frontend
npm run dev
```
- Creator Dashboard: [http://localhost:3000](http://localhost:3000)

---

## 🧪 Running Automated Tests

To execute the backend Pytest test suite:
```powershell
cd backend
.venv\Scripts\pytest -v
```

---

## 🗺️ Milestone Roadmap

| Milestone | Phase | Description | Status |
| :--- | :--- | :--- | :--- |
| **Milestone 0** | Phase 0 & 1 | Local Foundation, FastAPI Core, Next.js Dashboard Shell, Honest Health Diagnostics, Pytest Suite | ✅ Completed |
| **Milestone 1** | Phase 2 | PostgreSQL Database Models, SQLAlchemy 2.0 Async, Redis State & Caching | ⏳ Next |
| **Milestone 2** | Phase 3 | Multi-Key YouTube Engine & 4-Stream Session Manager | ⏳ Upcoming |
| **Milestone 3** | Phase 4 | Centralized Gemini AI Engine & Rotation | ⏳ Upcoming |
| **Milestone 4** | Phase 5 | 3-Tier Moderation Engine (Rules + Behavioral + AI) | ⏳ Upcoming |
| **Milestone 5** | Phase 6 | AI Co-Host with Personality & Cooldown Engine | ⏳ Upcoming |
| **Milestone 6** | Phase 7-9 | Nightbot Commands, Viewer XP & VIP, Modular Switchboard | ⏳ Upcoming |
| **Milestone 7** | Phase 10-14 | Creator Dashboard Full Wireup, Hardening, Git & Railway Deployment | ⏳ Upcoming |

---

## 🔒 Security & Privacy

- **Zero Hardcoded Secrets**: Secrets and credentials reside strictly in local `.env`.
- **Automatic Secret Redaction**: All internal logs automatically mask API keys and sensitive tokens before writing to stdout.
- **Fail-Safe Operation**: If external APIs fail or are exhausted, Goddess AI degrades gracefully without crashing active live stream sessions.
