# 🚀 Quick Start Guide

## Prerequisites

- Python 3.11+ installed
- Google Gemini API key ([Get here](https://makersuite.google.com/app/apikey))

## Setup (5 minutes)

### 1. Navigate to project directory
```powershell
cd c:\Users\Dell\Downloads\RamnarayanProjects\agrigravity
```

### 2. Install dependencies
```powershell
pip install -r requirements.txt
```

### 3. Configure environment
Open `.env` file and set your API key:
```env
GEMINI_API_KEY=paste-your-actual-key-here
SECRET_KEY=your-secret-jwt-key-change-this
```

### 4. Run the application
```powershell
uvicorn app.main:app --reload
```

### 5. Open in browser
```
http://localhost:8000
```

## First Steps

1. **Register**: Create your farmer account at `/register`
2. **Scan Plant**: Upload a plant image at `/plants/scanner`
3. **Create Farm**: Add your farm at `/farms/create`
4. **Get Recommendations**: Visit `/recommendations`
5. **View Leaderboard**: Check rankings at `/leaderboard`

## API Documentation

Interactive API docs available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Troubleshooting

**Issue**: Database error
**Fix**: Delete `agritech.db` and restart the app

**Issue**: Gemini API error
**Fix**: Check your API key in `.env`

**Issue**: Import errors
**Fix**: Reinstall dependencies: `pip install -r requirements.txt --force-reinstall`

## Support

- Check [README.md](file:///c:/Users/Dell/Downloads/RamnarayanProjects/agrigravity/README.md) for full documentation
- See [walkthrough.md](file:///C:/Users/Dell/.gemini/antigravity/brain/3c03db13-34ae-4ea7-827b-ad6bafbabe08/walkthrough.md) for implementation details
