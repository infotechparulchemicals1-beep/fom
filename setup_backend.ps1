# Setup and run FastAPI backend on Windows PowerShell
Write-Host "=== Setting up FastAPI backend ===" -ForegroundColor Cyan

Set-Location -Path "$PSScriptRoot\backend"

if (-not (Test-Path "venv")) {
    Write-Host "Creating Python virtual environment..." -ForegroundColor Yellow
    python -m venv venv
}

Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"

Write-Host "Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt

if (-not (Test-Path ".env")) {
    Write-Host "Creating .env from .env.example..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
}

Write-Host "Starting FastAPI development server on http://localhost:8000 ..." -ForegroundColor Green
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
