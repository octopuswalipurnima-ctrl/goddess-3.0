# GODDESS AI 2.0 — Security Architecture & Policy

## Overview
GODDESS AI 2.0 is built with security-first architecture to protect live broadcast operations, API keys, credentials, creator controls, and real-time WebSocket communication.

---

## 1. Absolute Security Rules (Zero-Tolerance)
1. **Never store API keys in PostgreSQL or SQLite.**
2. **Never store OAuth access/refresh tokens in PostgreSQL or SQLite.**
3. **Never store secrets, tokens, or credentials in Redis.**
4. **Never expose secrets or API keys through REST APIs or `/health` diagnostics.**
5. **Never expose secrets or API keys through WebSocket payloads.**
6. **Never print API keys, tokens, or passwords in application logs (Secret Redaction Filter active).**
7. **Never return raw Authorization headers or secrets in error traces.**
8. **Never log request bodies containing credentials (`/auth/login`, `/auth/users`).**
9. **Never execute shell/system commands originating from YouTube live chat.**
10. **Never allow Gemini AI output to execute backend commands or arbitrary code.**
11. **Never allow a pluggable module to bypass core safety gates or moderation policies.**
12. **Never allow a viewer to access creator-only dashboard APIs.**
13. **Never allow unprivileged users to toggle emergency controls (`kill_switch`, `safe_mode`).**
14. **Never disable moderation safety gates through untrusted or unauthenticated requests.**
15. **Never trust client-side authorization alone; every REST and WebSocket request is authorized on the backend.**

---

## 2. Authentication & Authorization
- **Password Hashing**: PBKDF2-HMAC-SHA256 with 100,000 iterations and a 32-byte cryptographically secure per-user salt. Constant-time comparison prevents timing attacks.
- **JWT Tokens**: Explicitly locked to `HS256`. Validates `sub`, `role`, `permissions`, `exp`, `iat`, `iss`, and `aud`. Tokens signed with `none` or unauthorized algorithms are rejected immediately.
- **Role-Based Access Control (RBAC)**:
  - `OWNER`: Full platform administration, user management, and emergency controls.
  - `ADMIN`: Full operational access, moderation configuration, and emergency controls.
  - `OPERATOR`: Operational access to manage streams, moderation settings, Co-Host, and modules.
  - `VIEWER`: Strictly read-only access to dashboard metrics, logs, and public feeds.

---

## 3. Defense-in-Depth HTTP Security Headers
All HTTP responses include:
- `X-Content-Type-Options: nosniff` (prevents MIME-type sniffing)
- `X-Frame-Options: DENY` (clickjacking protection)
- `Referrer-Policy: strict-origin-when-cross-origin` (prevents referrer leakage)
- `X-XSS-Protection: 1; mode=block` (legacy XSS filtering)

---

## 4. Request Correlation & Auditing
- Every HTTP request receives a unique `X-Request-ID` (UUID or preserved client trace).
- `X-Request-ID` is logged across all subsystem operations and returned in response headers for end-to-end distributed tracing.

---

## 5. Rate Limiting & DoS Protection
- **Auth Endpoint (`/api/v1/auth/login`)**: 10 requests per minute per IP.
- **Emergency Endpoint (`/api/v1/moderation/emergency-stop`)**: 20 requests per minute per IP.
- **General APIs**: 120 requests per minute per IP.
- Backed by Redis with automatic, thread-safe local in-memory fallback.

---

## 6. WebSocket Security
- Connection requires valid JWT token via `?token=<JWT>` or initial `AUTH` handshake.
- Max 5 concurrent connections per user to prevent connection exhaustion.
- Message rate limiting (30 messages/sec) protects against client-side flooding.
- Stream-level subscription filtering isolates multi-stream events.
