# Create .env file by copying from .env.example
Copy-Item .env.example .env -Force
Write-Host "✅ Created .env file"
Write-Host ""
Write-Host "⚠️  IMPORTANT: Edit .env and add your Gemini API key!"
Write-Host ""
Write-Host "Get your API key from: https://makersuite.google.com/app/apikey"
