# GODDESS AI 2.0 — AI Model Failover & Quota Management

## 1. Multi-Key Credential Pool

- Supports 1 to 4 rotated Gemini API keys (`GEMINI_API_KEY_1`..`4`).
- Round-robin load balancing across healthy keys.
- Automatic exponential cooldown on 429 quota exhaustion (starting at 300s up to 3600s).

## 2. Model Routing & Fallbacks

- **Primary Model**: `gemini-2.5-flash`
- **Fallback Model**: `gemini-2.5-flash-lite`
- **Overload Trigger**: HTTP 500, 502, 503, or 504 errors trigger automatic fallback to `gemini-2.5-flash-lite`.
- **Fail-Closed State**: If all keys are in cooldown, requests fail closed (`CredentialUnavailableError`) without unhandled crashes.
