# Run the Agricultural Assistant Platform using uv

Write-Host "🚀 Starting Agricultural Assistant Platform with uv..." -ForegroundColor Green
Write-Host ""

# Check if uv is installed
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "❌ uv is not installed!" -ForegroundColor Red
    Write-Host "Install it with: pip install uv" -ForegroundColor Yellow
    Write-Host "Or visit: https://github.com/astral-sh/uv" -ForegroundColor Yellow
    exit 1
}

# Sync dependencies with uv
Write-Host "📦 Installing dependencies with uv..." -ForegroundColor Cyan
uv pip install -r requirements.txt --index-strategy unsafe-best-match

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to install dependencies" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Dependencies installed successfully!" -ForegroundColor Green
Write-Host ""

# Check if .env exists
if (-not (Test-Path ".env")) {
    Write-Host "⚠️  .env file not found! Creating from template..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "✅ Created .env file - PLEASE ADD YOUR GEMINI_API_KEY!" -ForegroundColor Yellow
    Write-Host ""
}

# Run the application
Write-Host "🌾 Starting FastAPI server..." -ForegroundColor Green
Write-Host "📍 Server will be available at: http://localhost:8000" -ForegroundColor Cyan
Write-Host "📚 API docs at: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Gray
Write-Host ""

uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
