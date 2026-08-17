# GODDESS AI 2.0 — Load Testing & Multi-Stream Simulation

## Overview

GODDESS AI 2.0 includes a deterministic, offline multi-stream load simulation framework designed to stress test the system under realistic multi-stream chat traffic without calling external YouTube or Gemini APIs.

The framework supports simulating up to **4 simultaneous YouTube streams** with **200 viewers each** (800 total concurrent simulated viewers).

---

## Architecture & Components

The load simulator framework is located in `backend/tests/load/`:

| Module | Purpose |
|---|---|
| `viewers.py` | Generates deterministic pools of viewers (`SimulatedViewer`, `ViewerPool`) with realistic role distributions (Owner: 1, Mods: 5, VIPs: 10, Regulars: 184). |
| `traffic.py` | Generates synthetic chat messages across 8 traffic profiles: `NORMAL`, `BURST`, `MODERATION_HEAVY`, `COHOST_HEAVY`, `COMMAND_HEAVY`, `CHURN`, `DUPLICATE`, `MIXED`. |
| `metrics.py` | Tracks message throughput, p50/p95/p99/mean/min/max latencies, error counts, queue depths, cache sizes, and isolation violations. |
| `scenarios.py` | Declarative scenario definitions (`Standard4StreamScenario`, `Burst4StreamScenario`, `ModerationHeavyScenario`). |
| `simulator.py` | Orchestrates asynchronous concurrent execution across all 4 streams, driving events through EventBus, Moderation, Co-Host, and Module pipelines. |

---

## Traffic Profiles

1. **`NORMAL`**: Standard chat velocity (90% general chat, 5% co-host mentions, 3% commands, 2% spam/links).
2. **`BURST`**: 10x traffic spike simulating a sudden raid or viral stream highlight.
3. **`MODERATION_HEAVY`**: High volume of malicious links, ALL-CAPS flood, and banned phrases to stress Tier-1 regex and Tier-2 AI moderation.
4. **`COHOST_HEAVY`**: High frequency of `@goddess` conversational mentions and personality queries.
5. **`COMMAND_HEAVY`**: Rapid execution of `!help`, `!stats`, `!rules`, and custom module commands.
6. **`CHURN`**: Rapid viewer joins, leaves, and chat activity churn.
7. **`DUPLICATE`**: Repeated identical messages simulating copypasta and spam raids.
8. **`MIXED`**: Balanced realistic mix of all profiles.

---

## Running Load Tests

To execute the load testing suite:

```bash
pytest -v tests/test_load/
```

### Key Assertions Tested

- **Zero Cross-Stream Contamination**: Stream A messages and viewer contexts never leak into Stream B, C, or D.
- **Throughput & Latency**: Processes 800-message concurrent multi-stream traffic with p99 latency < 250ms.
- **Consumer Isolation**: A failing consumer or module on one stream does not impact execution on other streams.
- **Spam Burst Suppression**: Duplicate spam bursts are throttled without dropping legitimate chat messages.
