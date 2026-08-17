# GODDESS AI 2.0 — Creator Control Center

## Overview

The Creator Control Center provides a real-time command interface for supervising up to 4 YouTube Live streams, adjusting AI Co-Host settings, managing moderation filters, tracking multi-key quota rotation, and invoking emergency controls.

## API Surface:
- `GET /api/v1/dashboard/overview`: Aggregated telemetry and dependency health.
- `GET /api/v1/streams/supervised`: List supervised stream summaries.
- `POST /api/v1/streams/attach`: Attach a new stream.
- `POST /api/v1/streams/{stream_id}/detach`: Detach and stop a stream.
- `POST /api/v1/streams/{stream_id}/reconnect`: Trigger controlled reconnect.
- `POST /api/v1/streams/{stream_id}/emergency-stop`: Halt stream actions.
- `POST /api/v1/streams/{stream_id}/clear-emergency-stop`: Resume stream.
- `POST /api/v1/streams/{stream_id}/safe-mode`: Enable stream safe mode.
- `POST /api/v1/streams/{stream_id}/clear-safe-mode`: Disable stream safe mode.
- `POST /api/v1/streams/global-emergency-stop`: Global emergency halt.
- `POST /api/v1/streams/clear-global-emergency-stop`: Clear global emergency halt.
