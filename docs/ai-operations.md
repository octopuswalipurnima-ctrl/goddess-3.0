# GODDESS AI 2.0 — AI Live Operations & Human Override Playbook

## 1. Operating Modes

| Mode | Moderation Behavior | Co-Host Behavior | Outgoing YouTube Chat |
|---|---|---|---|
| **NORMAL** | Active (Tier 1 + 2 + 3) | Active (Live replies) | Enabled |
| **SAFE_MODE** | Dry Run (LOG only) | Read-only evaluation | Blocked |
| **EMERGENCY_STOP** | Halted | Halted | Blocked |
| **DEGRADED** | Tier 1 Active | Fail closed / Bounded | Controlled |

## 2. Human Operator Override Procedures

1. **Global Emergency Stop**:
   - UI: Click "Global Emergency Stop" button in Creator Control Center header.
   - API: `POST /api/v1/streams/global-emergency-stop`
2. **Per-Stream Safe Mode**:
   - UI: Toggle "Safe Mode" on the target stream card.
   - API: `POST /api/v1/streams/{stream_id}/safe-mode`
3. **Per-Stream Co-Host Toggle**:
   - UI: Toggle "Co-Host Active" switch in Stream Settings.
   - API: `PATCH /api/v1/streams/{stream_id}/config`
