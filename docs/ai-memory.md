# GODDESS AI 2.0 — AI Memory & Context Architecture

## 1. Bounded Context Structure

To prevent memory leaks and maintain stream isolation:
- **Stream Context**: Maximum 20 messages per stream via `collections.deque(maxlen=20)`.
- **Viewer Context**: Maximum 5 messages per viewer via `collections.deque(maxlen=5)`.
- **Stream Isolation**: Context dictionaries are keyed by `stream_id`. Messages from `STREAM_A` never cross to `STREAM_B`.
- **Zero Raw Secrets**: Context managers scrub secrets and never store API keys, tokens, or passwords.
- **Eviction**: Contexts are automatically cleared on stream termination (`clear_context(stream_id)`).
