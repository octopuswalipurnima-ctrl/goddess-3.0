# ==============================================================================
# GODDESS AI 2.0 - Local Development Startup Script
# ==============================================================================
# Starts FastAPI Backend (Port 8000) and Next.js Frontend (Port 3000) concurrently.
# ==============================================================================

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Starting GODDESS AI 2.0 Local Development Environment   " -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Cyan

# Check for .env file
if (-not (Test-Path "$root\.env")) {
    Write-Host "[INFO] No .env file found. Copying .env.example -> .env..." -ForegroundColor Yellow
    Copy-Item "$root\.env.example" "$root\.env"
}

# Set Node PATH
$env:Path = "C:\Program Files\nodejs;" + $env:Path

Write-Host "`n[1/2] Launching FastAPI Backend on http://localhost:8000..." -ForegroundColor Green
$backendProcess = Start-Process -FilePath "$root\backend\.venv\Scripts\python.exe" `
    -ArgumentList "-m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload" `
    -WorkingDirectory "$root\backend" `
    -PassThru

Write-Host "[2/2] Launching Next.js Dashboard on http://localhost:3000..." -ForegroundColor Green
$frontendProcess = Start-Process -FilePath "C:\Program Files\nodejs\npm.cmd" `
    -ArgumentList "run dev" `
    -WorkingDirectory "$root\frontend" `
    -PassThru

Write-Host "`n==========================================================" -ForegroundColor Cyan
Write-Host "  Goddess AI 2.0 Services are now RUNNING!              " -ForegroundColor Green
Write-Host "  - Creator Dashboard: http://localhost:3000             " -ForegroundColor White
Write-Host "  - Backend API Docs:  http://localhost:8000/docs        " -ForegroundColor White
Write-Host "  - Health Endpoint:   http://localhost:8000/api/v1/health" -ForegroundColor White
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Press Ctrl+C or close the terminal to exit.`n" -ForegroundColor Yellow

try {
    # Keep script open while processes are running
    Wait-Process -Id $backendProcess.Id, $frontendProcess.Id
} finally {
    Stop-Process -Id $backendProcess.Id -ErrorAction SilentlyContinue
    Stop-Process -Id $frontendProcess.Id -ErrorAction SilentlyContinue
}
