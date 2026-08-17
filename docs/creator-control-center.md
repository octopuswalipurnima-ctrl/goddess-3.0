# GODDESS AI 2.0 — Creator Control Center & Operational Observability

## 1. Overview
The Creator Control Center serves as the unified operational command and observability platform for GODDESS AI 2.0. It provides real-time telemetry, 4-stream lifecycle management (`STREAM_A` through `STREAM_D`), live AI health diagnostics, multi-key provider rotation status, bounded audit logging, and immediate fail-safe controls.

## 2. Core Safety Invariants
1. **SAFE STOP > UNSAFE AUTOMATION**: `ProductionSafetyController` is the supreme authoritative gatekeeper.
2. **FAIL CLOSED > FABRICATED ACTION**: In the event of provider outages or degraded health, the system safely suppresses actions rather than hallucinating or inventing responses.
3. **STRICT STREAM ISOLATION**: Stream metrics, moderation states, and Co-Host context remain strictly isolated across `STREAM_A`, `STREAM_B`, `STREAM_C`, and `STREAM_D`.
4. **ZERO SECRET LEAKAGE**: API keys, bearer tokens, passwords, and private identifiers are never rendered in logs, API responses, or WebSockets. Safe aliases (`KEY-1`, `KEY-2`, `KEY-3`, `KEY-4`) are used throughout.
5. **BOUNDED RESOURCE BOUNDS**: Audit logs and latency tracker windows are strictly bounded in memory to prevent exhaustion.

## 3. Architecture & Components

```
+-------------------------------------------------------------------------+
|                       CREATOR CONTROL CENTER                            |
|  +---------------------+  +---------------------+  +-----------------+  |
|  | Operations Overview |  |  4-Stream Overview  |  | Safety Controls |  |
|  +---------------------+  +---------------------+  +-----------------+  |
|  | AI Operations Panel |  | Provider Health Pnl |  | Audit Log Panel |  |
|  +---------------------+  +---------------------+  +-----------------+  |
+------------------------------------+------------------------------------+
                                     | (REST / WebSocket Telemetry)
                                     v
+-------------------------------------------------------------------------+
|                        BACKEND OPERATIONS DOMAIN                        |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                     OperationsManager                             |  |
|  |  Coordinates safety, supervisor, cohost, and moderation actions   |  |
|  +-------------------------------------------------------------------+  |
|         |                     |                    |            |       |
|         v                     v                    v            v       |
|  +--------------+    +----------------+   +------------+  +-----------+ |
|  | SafetyCtrl   |    | StreamSupervisor|  | Cohost/Mod |  | Audit/Tele| |
|  +--------------+    +----------------+   +------------+  +-----------+ |
+-------------------------------------------------------------------------+
```

## 4. Operational Controls & REST Endpoints
| Endpoint | Method | Required Permission | Description |
|---|---|---|---|
| `/api/v1/operations/overview` | GET | `system.read` | High-level system overview |
| `/api/v1/operations/streams` | GET | `stream.read` | 4-stream operational telemetry |
| `/api/v1/operations/ai` | GET | `ai.read` | Gemini latency (p50/p95/p99) & health |
| `/api/v1/operations/providers` | GET | `system.read` | YouTube & Gemini credential pool health |
| `/api/v1/operations/audit` | GET | `audit.read` | Chronological redacted audit trail |
| `/api/v1/operations/emergency-stop` | POST | `moderation.emergency` | Global emergency stop |
| `/api/v1/operations/emergency-stop/clear` | POST | `moderation.emergency` | Clear global emergency stop |
| `/api/v1/operations/safe-mode/enable` | POST | `system.control` | Global Safe Mode enable |
| `/api/v1/operations/safe-mode/disable` | POST | `system.control` | Global Safe Mode disable |
| `/api/v1/operations/streams/{id}/attach` | POST | `stream.attach` | Supervise YouTube stream |
| `/api/v1/operations/streams/{id}/detach` | POST | `stream.detach` | Detach YouTube stream |
| `/api/v1/operations/streams/{id}/safe-mode/enable` | POST | `stream.safe_mode` | Stream-level safe mode |
| `/api/v1/operations/streams/{id}/emergency-stop` | POST | `moderation.emergency` | Stream-level emergency stop |
