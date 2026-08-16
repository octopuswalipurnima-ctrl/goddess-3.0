# Goddess AI 2.0 - Local Development Setup Guide

This guide is designed for beginners to set up and run Goddess AI 2.0 locally on Windows.

---

## 1. Prerequisites

Make sure you have:
- **Python 3.11 or 3.12**
- **Node.js (LTS)**
- **Git**

---

## 2. Setting Up Environment Variables

1. Copy the template `.env.example` to create your private `.env` file:
   ```powershell
   Copy-Item .env.example .env
   ```
2. Open `.env` in any text editor.
3. In Milestone 0, no API keys are strictly required to start the application. The system gracefully reports unconfigured components as `NOT_CONFIGURED`.

---

## 3. Starting the Project

### Method A: One-Click Startup (Recommended)
Run the development script:
```powershell
.\scripts\dev.ps1
```

### Method B: Manual Step-by-Step

**Terminal 1 (Backend):**
```powershell
cd backend
.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
- API Docs: `http://localhost:8000/docs`
- Health Endpoint: `http://localhost:8000/api/v1/health`

**Terminal 2 (Frontend):**
```powershell
cd frontend
npm run dev
```
- Creator Dashboard: `http://localhost:3000`

---

## 4. Running Tests

Run backend tests using:
```powershell
.\scripts\test.ps1
```
Or directly:
```powershell
cd backend
.venv\Scripts\pytest -v
```
