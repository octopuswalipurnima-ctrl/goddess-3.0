# GODDESS AI 2.0 — Authentication & RBAC Guide

## 1. Overview
GODDESS AI 2.0 provides secure multi-role access control designed for single-streamer setups up to multi-operator production teams.

---

## 2. Roles & Permissions Matrix

| Permission Token | OWNER | ADMIN | OPERATOR | VIEWER | Description |
|---|:---:|:---:|:---:|:---:|---|
| `dashboard.read` | ✅ | ✅ | ✅ | ✅ | View Creator Control Center overview & metrics |
| `dashboard.write` | ✅ | ✅ | ❌ | ❌ | Modify global dashboard layout and defaults |
| `stream.read` | ✅ | ✅ | ✅ | ✅ | Inspect active live stream sessions |
| `stream.control` | ✅ | ✅ | ✅ | ❌ | Connect, start, stop streams & send chat |
| `moderation.read` | ✅ | ✅ | ✅ | ✅ | View moderation stats, audits & test tool |
| `moderation.configure` | ✅ | ✅ | ✅ | ❌ | Adjust thresholds, rules, & spam filters |
| `moderation.emergency` | ✅ | ✅ | ❌ | ❌ | Toggle Kill Switch, Safe Mode, Circuit Breaker |
| `cohost.read` | ✅ | ✅ | ✅ | ✅ | Inspect Co-Host responses, metrics & persona |
| `cohost.configure` | ✅ | ✅ | ✅ | ❌ | Modify persona, cooldowns, & prompts |
| `modules.read` | ✅ | ✅ | ✅ | ✅ | Inspect registered pluggable modules |
| `modules.configure` | ✅ | ✅ | ✅ | ❌ | Enable, disable, start, stop & configure modules |
| `users.manage` | ✅ | ❌ | ❌ | ❌ | Create, update, and manage user credentials |
| `system.admin` | ✅ | ❌ | ❌ | ❌ | Full platform admin and diagnostic controls |

---

## 3. Endpoints

### `POST /api/v1/auth/login`
Authenticates a user and issues a signed JWT token.
- **Request**: `{"username": "creator", "password": "secure_password"}`
- **Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "id": 1,
    "username": "creator",
    "role": "OWNER",
    "permissions": ["dashboard.read", "stream.control", ...]
  }
}
```

### `GET /api/v1/auth/me`
Retrieves current authenticated user's session profile and effective permissions.
- **Header**: `Authorization: Bearer <access_token>`

### `POST /api/v1/auth/logout`
Terminates user session client-side.

### `POST /api/v1/auth/users`
Creates a new user account (Requires `OWNER` role / `users.manage` permission).

---

## 4. Development Bypass
In local testing environments where authentication is not required, set `AUTH_DEV_BYPASS=true` in `.env`.
When active, requests without an Authorization header are treated as `OWNER` role with full permissions. In production (`ENVIRONMENT=production`), bypass is strictly locked down.
