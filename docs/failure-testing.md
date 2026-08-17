# GODDESS AI 2.0 — Chaos Testing & Failover Runbook

## Overview

GODDESS AI 2.0 implements automated fault injection and chaos testing across all infrastructure and external dependencies to guarantee safe fail-closed and graceful degradation behavior.

---

## Chaos Scenarios Tested (Scenarios A–I)

| Scenario | Fault Injected | Expected Behavior | Verification Status |
|---|---|---|---|
| **Scenario A** | PostgreSQL database unavailable / connection refused | `/health/live` remains operational; `/health/ready` reports DEGRADED; operations fail safely without fabricating success. | **PASS** |
| **Scenario B** | Redis server offline / network partitioned | Seamless automatic fallback to local in-memory state store (`FALLBACK_IN_MEMORY`); cooldowns, rate limits, and deduplication continue operating. | **PASS** |
| **Scenario C** | Gemini AI API total outage / quota exhaustion | Tier-1 deterministic regex rules continue blocking spam/scams; Co-Host gracefully skips AI replies without crashing stream loop. | **PASS** |
| **Scenario D** | YouTube Data API quota 403 / network failure | Automatic round-robin rotation across 4 API keys; exponential cooldown backoff; clean `CredentialUnavailableError` when all exhausted. | **PASS** |
| **Scenario E** | Abrupt WebSocket disconnect / client crash | Instant removal of connection from active connection manager; no dangling async listener tasks or memory leaks. | **PASS** |
| **Scenario F** | Module runtime crash / unhandled exception | Module failure isolated; EventBus catches and logs error; remaining modules and core engines continue uninterrupted. | **PASS** |
| **Scenario G** | Single stream failure / crash | Failure contained strictly to the affected stream; other 3 concurrent streams continue running without interference. | **PASS** |
| **Scenario H** | Database transaction crash | SQLAlchemy async transaction rolls back atomically; no orphaned or corrupted records created. | **PASS** |
| **Scenario I** | Extreme chat traffic burst (10x spike) | EventBus and queue buffers process burst with bounded queue depths and p99 latency < 250ms. | **PASS** |

---

## Running Failover & Chaos Suites

To execute the chaos and failover test suites:

```bash
pytest -v tests/test_failover/ tests/test_chaos/
```
