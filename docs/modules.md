# Modular Extension & Plugin System Architecture

## 1. Overview

The **Modular Plugin System** in GODDESS AI 2.0 provides a secure, decoupled extension layer built on top of the Core Platform (YouTube, Gemini, Moderation, and Co-Host). Modules can be independently registered, loaded, enabled, disabled, started, stopped, configured per stream, and health-monitored without risking core system stability.

---

## 2. Core Architecture

```text
Core Platform (YouTube, Gemini, Moderation, Co-Host)
        │
        ▼
EventBus (Internal Decoupled Message Pipeline)
        │
        ├─────────────────────────────────────────────────┐
        ▼                                                 ▼
Core Service Handlers                             ModuleManager (Extension Layer)
                                                          │
                                         ┌────────────────┴────────────────┐
                                         │                                 │
                                         ▼                                 ▼
                                   ModuleRegistry                 Isolated Dispatcher
                                (Topological Order &               (Exception Catching &
                                 Cycle Prevention)                  State Management)
                                         │                                 │
                     ┌───────────────────┼───────────────────┬─────────────┴─────────────┐
                     ▼                   ▼                   ▼                           ▼
              CommandsModule       WelcomeModule     StreamStatsModule       ViewerInteractionModule
```

---

## 3. Module Lifecycle States

```text
DISCOVERED ──> REGISTERED ──> LOADED ──> ENABLED ──> RUNNING ──> STOPPED ──> DISABLED
     │              │           │           │           │           │           │
     └──────────────┴───────────┴───────────┴───────────┴───────────┴───────────┘
                                        │
                                        ▼
                                     FAILED
```

- **Strict Transition Gates**: Modules cannot bypass lifecycle states (e.g. jumping directly from `REGISTERED` to `RUNNING` is disallowed).
- **Failure Isolation**: An unhandled exception inside any module's event callback marks that module as `FAILED`, updates its health record, and dispatches `MODULE_FAILED` on EventBus. It **never** crashes EventBus or halts other modules or core services.

---

## 4. Built-In Modules

| Module ID | Category | Description | Default State |
| :--- | :--- | :--- | :--- |
| `commands` | `interaction` | Safe prefix chat commands (`!help`, `!discord`, `!socials`, `!rules`) with per-command & per-user cooldowns. Strictly zero shell execution. | Disabled per stream |
| `welcome` | `interaction` | Greets first-time and returning viewers with customizable template and anti-spam cooldown. | Disabled per stream |
| `stream_stats` | `stats` | Live stream telemetry (messages processed, msg/min rate, moderation decisions, co-host replies, uptime). | Enabled |
| `viewer_interaction`| `interaction` | Bounded memory tracker of viewer message counts and first/last active timestamps (LRU eviction at 1,000 users). | Enabled |

---

## 5. Security & Permission Guardrails

- **No Raw Secrets**: Modules are never given raw API keys, database passwords, or secret tokens.
- **No Arbitrary Code Execution**: Commands and configs are strictly data-driven with Pydantic validation (no `eval`, `exec`, or shell spawning).
- **Capability Declarations**: Modules must declare required capabilities (`CHAT_READ`, `CHAT_WRITE`, `STREAM_READ`, `MODERATION_READ`, `COHOST_READ`, `AI_REQUEST`, `CONFIG_READ`, `CONFIG_WRITE`).
