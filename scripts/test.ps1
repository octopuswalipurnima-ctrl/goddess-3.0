# ==============================================================================
# GODDESS AI 2.0 - Test Suite Runner
# ==============================================================================

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Running GODDESS AI 2.0 Automated Tests                  " -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Cyan

Write-Host "`n[1/1] Running Pytest Backend Test Suite..." -ForegroundColor Green
& "$root\backend\.venv\Scripts\pytest.exe" -v "$root\backend\tests"

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n[SUCCESS] All backend unit tests passed successfully!" -ForegroundColor Green
} else {
    Write-Host "`n[FAILURE] Backend tests failed with exit code $LASTEXITCODE" -ForegroundColor Red
}
