# GODDESS AI 2.0 — Stream Supervisor Architecture

## Overview

The `StreamSupervisor` (`app.services.youtube.stream_supervisor`) orchestrates up to 4 simultaneous YouTube Live streams.

```mermaid
flowchart TD
    Supervisor["StreamSupervisor (Max 4 concurrent)"]
    StreamA["Stream A SupervisorSession"]
    StreamB["Stream B SupervisorSession"]
    StreamC["Stream C SupervisorSession"]
    StreamD["Stream D SupervisorSession"]

    Supervisor --> StreamA
    Supervisor --> StreamB
    Supervisor --> StreamC
    Supervisor --> StreamD

    StreamA -->|Session & ChatReader| LiveYT_A["YouTube Live Stream A"]
    StreamB -->|Session & ChatReader| LiveYT_B["YouTube Live Stream B"]
    StreamC -->|Session & ChatReader| LiveYT_C["YouTube Live Stream C"]
    StreamD -->|Session & ChatReader| LiveYT_D["YouTube Live Stream D"]
```

## Features:
- Automatic attach from WebSub live stream discovery.
- Strict isolation: failure on Stream A never crashes or degrades Stream B, C, or D.
- Bounded jittered exponential backoff for reconnects ($1\text{s} \to 2\text{s} \to 4\text{s} \to 8\text{s} \to 16\text{s} \to 30\text{s}$).
- Clean resource deallocation and metric finalization upon broadcast end.
