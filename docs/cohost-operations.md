# Co-Host Live Stream Operations

## Safety & Override Hierarchy
```
Emergency Stop (Global or Stream)  [HIGHEST AUTHORITY]
       │
       ▼
Safe Mode (Disables Co-Host generation, suppresses chatter)
       │
       ▼
ProductionSafetyController (can_cohost / can_send_chat gates)
       │
       ▼
AIDecisionEngine & EngagementDecisionEngine
       │
       ▼
LiveChatWriter (LIVE) / Dashboard Telemetry (DRY_RUN)
```

## REST API Management
| Endpoint | Method | Permission | Purpose |
|---|---|---|---|
| `/api/v1/cohost/config/{stream_id}` | GET | `cohost.read` | View stream cohost settings |
| `/api/v1/cohost/config/{stream_id}` | PUT | `cohost.configure` | Update stream cohost configuration |
| `/api/v1/cohost/personality/{stream_id}` | GET | `cohost.read` | View persona attributes |
| `/api/v1/cohost/personality/{stream_id}` | PUT | `cohost.configure` | Update persona attributes |
| `/api/v1/cohost/knowledge/{stream_id}` | GET | `cohost.read` | View verified facts |
| `/api/v1/cohost/knowledge/{stream_id}` | POST | `cohost.configure` | Add or update verified fact |
| `/api/v1/cohost/knowledge/{stream_id}/{key}` | DELETE | `cohost.configure` | Delete verified fact |
| `/api/v1/cohost/awareness/{stream_id}` | GET | `cohost.read` | View stream awareness data |
| `/api/v1/cohost/awareness/{stream_id}` | PUT | `cohost.configure` | Update stream awareness data |
| `/api/v1/cohost/stats` | GET | `cohost.read` | Global engagement metrics |
| `/api/v1/cohost/test` | POST | `cohost.read` | Dry-run simulated message test |
