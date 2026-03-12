# Setup script for Agricultural Assistant Platform with uv

Write-Host "Agricultural Assistant Platform - Setup with uv" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""

# Step 1: Check Python version
Write-Host "Step 1: Checking Python version..." -ForegroundColor Cyan
$pythonVersion = python --version 2>&1
if ($pythonVersion -match "Python 3\.1[1-9]") {
    Write-Host "  OK: $pythonVersion" -ForegroundColor Green
} else {
    Write-Host "  WARNING: Python 3.11+ required. Current: $pythonVersion" -ForegroundColor Yellow
}
Write-Host ""

# Step 2: Install uv if not present
Write-Host "Step 2: Checking uv installation..." -ForegroundColor Cyan
if (Get-Command uv -ErrorAction SilentlyContinue) {
    $uvVersion = uv --version
    Write-Host "  OK: uv is installed: $uvVersion" -ForegroundColor Green
} else {
    Write-Host "  Installing uv..." -ForegroundColor Yellow
    pip install uv
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  OK: uv installed successfully!" -ForegroundColor Green
    } else {
        Write-Host "  ERROR: Failed to install uv" -ForegroundColor Red
        exit 1
    }
}
Write-Host ""

# Step 3: Create virtual environment with uv
Write-Host "Step 3: Creating virtual environment..." -ForegroundColor Cyan
if (Test-Path ".venv") {
    Write-Host "  INFO: Virtual environment already exists" -ForegroundColor Yellow
} else {
    uv venv
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  OK: Virtual environment created in .venv/" -ForegroundColor Green
    } else {
        Write-Host "  ERROR: Failed to create virtual environment" -ForegroundColor Red
        exit 1
    }
}
Write-Host ""

# Step 4: Install dependencies
Write-Host "Step 4: Installing dependencies with uv..." -ForegroundColor Cyan
uv pip install -r requirements.txt --index-strategy unsafe-best-match
if ($LASTEXITCODE -eq 0) {
    Write-Host "  OK: All dependencies installed!" -ForegroundColor Green
} else {
    Write-Host "  ERROR: Failed to install dependencies" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 5: Setup .env file
Write-Host "Step 5: Setting up environment file..." -ForegroundColor Cyan
if (Test-Path ".env") {
    Write-Host "  INFO: .env file already exists" -ForegroundColor Yellow
} else {
    Copy-Item ".env.example" ".env"
    Write-Host "  OK: Created .env file" -ForegroundColor Green
}
Write-Host ""

# Final instructions
Write-Host "================================================" -ForegroundColor Green
Write-Host "Setup Complete! Next steps:" -ForegroundColor Green
Write-Host ""
Write-Host "1. Edit .env and add your Gemini API key" -ForegroundColor Yellow
Write-Host "2. Activate virtual environment: .venv\Scripts\activate" -ForegroundColor Yellow
Write-Host "3. Run: .\run.ps1" -ForegroundColor Yellow
Write-Host ""
Write-Host "App URL: http://localhost:8000" -ForegroundColor Cyan
Write-Host "API Docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""
