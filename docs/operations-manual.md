# GODDESS AI 2.0 — Production Operations Manual

## 1. Operating Procedures

### 1.1 Pre-Flight Check
Before going live:
1. Verify `/api/v1/health/detailed` reports `overall_status: "HEALTHY"`.
2. Confirm at least 1 healthy YouTube credential (`KEY-1`..`KEY-4`) and 1 healthy Gemini API credential.
3. Review audit log `/api/v1/operations/audit` for any lingering degraded state.

### 1.2 Attaching a Stream
1. Open the Creator Control Center dashboard.
2. Under the appropriate slot (`STREAM_A` through `STREAM_D`), click **Attach Stream**.
3. Provide the YouTube `video_id` (e.g. `dQw4w9WgXcQ`).
4. The `StreamSupervisor` will establish connection, verify live chat polling, and start telemetry tracking.

### 1.3 Triggering Emergency Stop
If erratic chat behavior, severe API errors, or unexpected moderation actions occur:
1. **Global Emergency**: Click the red **GLOBAL EMERGENCY STOP** button at the top of the dashboard or `POST /api/v1/operations/emergency-stop`.
2. **Single Stream Emergency**: Click the red stop icon on that specific stream card.
3. All outgoing live chat messages, Co-Host responses, and destructive actions will instantly cease.

### 1.4 Recovering from Outages & Clearing Emergency Stop
1. Inspect AI / Provider diagnostics to verify credential availability and error codes.
2. Click **CLEAR EMERGENCY STOP** or `POST /api/v1/operations/emergency-stop/clear`.
3. The system returns to normal operation. **No past suppressed messages are replayed**, guaranteeing zero spam bursts.

## 2. Zero-Secret Observability Guarantee
- All API diagnostics redact credentials into safe aliases: `KEY-1`, `KEY-2`, `KEY-3`, `KEY-4`.
- Audit logs automatically strip authorization headers and API key patterns.
- WebSocket feeds contain zero private authentication tokens.
