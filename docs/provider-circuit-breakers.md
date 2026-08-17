# GODDESS AI 2.0 — Provider Circuit Breakers

## 1. Circuit Breaker Architecture

Circuit breakers protect against retry storms, cascading downtime, and quota burning across external APIs and core infrastructure:

```
        Success
   ┌───────────────┐
   │               ▼
┌──────┐ Failure ┌──────┐ Cooldown Elapsed ┌───────────┐
│CLOSED│────────►│ OPEN │─────────────────►│ HALF_OPEN │
└──────┘         └──────┘                  └───────────┘
   ▲                                             │
   └─────────────────────────────────────────────┘
                Trial Successes
```

## 2. Configured Breaker Thresholds
| Breaker | Failure Threshold | Cooldown Window | Half-Open Successes |
|---|---|---|---|
| `youtube` | 5 consecutive failures | 30.0 seconds | 2 |
| `gemini` | 5 consecutive failures | 20.0 seconds | 2 |
| `redis` | 3 consecutive failures | 15.0 seconds | 2 |
| `postgres` | 3 consecutive failures | 15.0 seconds | 2 |
