# GODDESS AI 2.0 — Production Safety Controller

## Overview

The `ProductionSafetyController` (`app.core.safety_controller`) is the single authority governing operational safety states, emergency halts, safe mode gates, and mutation permissions.

## States:
1. `NORMAL`: Standard live operation according to stream config.
2. `DEGRADED`: Non-critical service failure; non-destructive operations permitted.
3. `SAFE_MODE`: Read-only analysis and logging permitted; automated YouTube actions blocked.
4. `EMERGENCY_STOP`: Absolute halt on outgoing external actions; idempotent.
5. `SHUTTING_DOWN`: Graceful process termination.

## Safe Action Gating Methods:
- `can_moderate(stream_id)`
- `can_cohost(stream_id)`
- `can_send_chat(stream_id)`
- `can_execute_command(stream_id)`
- `can_reconnect(stream_id)`
