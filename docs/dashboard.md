# Creator Control Center & Real-Time Dashboard Architecture

## 1. Overview

The **Creator Control Center** in GODDESS AI 2.0 provides an enterprise-grade, non-programmer streamer-friendly control interface for monitoring and orchestrating up to **4 simultaneous YouTube live streams**. It combines high-speed initial REST hydration with low-latency WebSocket event streaming.

---

## 2. Component Architecture

```text
Next.js 15 Creator Dashboard (Frontend)
├── Centralized Shared WebSocket Client (Auto-reconnect with exponential backoff)
├── Typed API Client Layer (health, streams, moderation, cohost, modules, dashboard)
│
└── Control Center UI Components:
    ├── GlobalSystemHealth (Honest subsystem telemetry from /api/v1/health)
    ├── FourStreamOverview (Streams A, B, C, D with live status, chat rate, viewers)
    ├── StreamControlCenter (Selected stream controls: Stop, Moderation, Co-Host, Modules)
    ├── ModerationCenter (Metrics + Live audit feed with EXECUTED/BLOCKED/DRY_RUN status)
    ├── CoHostCenter (Metrics + Live intent/response feed)
    ├── ModuleCenter (Pluggable modules: status, health, capabilities, enable/disable)
    ├── AIDiagnostics (Gemini credentials count, cooldowns, queue size - 0 secrets)
    ├── YouTubeDiagnostics (YouTube credentials count, cooldowns, active streams - 0 secrets)
    ├── ActivityTimeline (Central bounded live event timeline <= 100 items)
    └── EmergencyControls (Prominent Kill Switch, Emergency Stop with confirmation)
```

---

## 3. Real-Time Synchronization Model

1. **Initial Hydration**: On component mount, the frontend queries `GET /api/v1/dashboard/overview` and `GET /api/v1/health` to populate baseline telemetry.
2. **Centralized WebSocket (`dashboardWs`)**:
   - Single persistent WebSocket connection to `/api/v1/ws`.
   - Broadcasts connection states: `CONNECTED`, `RECONNECTING`, `DISCONNECTED`.
   - Auto-reconnect with exponential backoff ($1s \to 2s \to 4s \to \dots \to 30s$).
   - Fallback polling ensures dashboard remains functional even when offline or disconnected.
3. **Bounded Memory**: Activity feed is strictly bounded to latest 100 events, preventing unbounded browser memory growth.
4. **Security & Zero Secret Exposure**: Credential views only show slot identifiers (e.g. `gemini-key-1`, `youtube-key-1`) and never raw API keys or tokens.

---

## 4. Emergency Master Controls

Emergency operations require explicit confirmation via a confirmation modal dialog before execution:
- **Moderation Kill Switch**: Instantly engages the emergency kill switch for the stream.
- **Co-Host Emergency Stop**: Halts public AI responses immediately.
- **Stop Stream Session**: Terminates background polling tasks and cleans up the stream session.
