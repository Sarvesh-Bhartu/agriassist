# Agricultural Assistant Platform

AI-Powered Agricultural Assistant Platform using FastAPI, Google Gemini AI, and SQLite.

## Features

🌱 **Plant Identification**: Upload plant images and get AI-powered identification with invasive species detection
🌾 **Crop Recommendations**: Personalized AI crop suggestions based on soil, budget, and historical data  
🗺️ **Farm Mapping**: Map farm boundaries and calculate area using GPS coordinates
🍃 **Carbon Credits**: Estimate carbon credit value based on farm size and soil type
🔔 **Web Alerts**: In-app notifications for important updates
🏆 **Gamification**: Earn points, unlock badges, and compete on leaderboards

## Tech Stack

- **Backend**: FastAPI (Python 3.11+)
- **Database**: SQLite (file-based, no setup needed)
- **AI**: Google Gemini (Vision + Pro models)
- **Frontend**: Jinja2 templates + Tailwind CSS
- **Geospatial**: Shapely + PyProj for area calculations

## Quick Start

### 1. Clone the Repository

```bash
cd agrigravity
```

### 2. Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```env
# Required
GEMINI_API_KEY=your-gemini-api-key-here
SECRET_KEY=your-secret-key-for-jwt

# Optional (defaults are fine for development)
DATABASE_URL=sqlite:///./agritech.db
DEBUG=True
```

**Get Gemini API Key:**
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Copy and paste into `.env`

### 5. Run the Application

```bash
# Development server with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or using Python directly
python -m app.main
```

### 6. Access the Application

- **Web Interface**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Alternative API Docs**: http://localhost:8000/redoc

## Project Structure

```
agrigravity/
├── app/
│   ├── core/               # Config, database, security
│   ├── models/             # SQLAlchemy models & Pydantic schemas
│   ├── routers/            # API endpoints
│   ├── services/           # Business logic (Gemini, calculations)
│   ├── templates/          # Jinja2 HTML templates
│   ├── static/             # CSS, JavaScript, images
│   ├── utils/              # Helper functions
│   └── main.py             # FastAPI application
├── uploads/                # Uploaded images
├── logs/                   # Application logs  
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (create from .env.example)
└── agritech.db            # SQLite database (auto-created)
```

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new farmer
- `POST /api/auth/login` - Login and get JWT token
- `GET /api/auth/me` - Get current user info

### Plant Identification
- `POST /api/plants/identify` - Upload image for identification
- `GET /api/plants/history` - Get plant detection history
- `POST /api/plants/{id}/mark-destroyed` - Mark invasive plant as destroyed

### Farm Management
- `POST /api/farms/` - Create new farm
- `GET /api/farms/` - Get all farms
- `GET /api/farms/{id}` - Get farm details
- `POST /api/farms/{id}/calculate-carbon` - Calculate carbon credits

### Crop Recommendations
- `POST /api/recommendations/` - Get AI crop recommendations

### Alerts
- `GET /api/alerts/` - Get alerts for farmer
- `POST /api/alerts/{id}/mark-read` - Mark alert as read

### Gamification
- `GET /api/gamification/leaderboard` - Get leaderboard
- `GET /api/gamification/badges` - Get all badges
- `GET /api/gamification/my-stats` - Get user's stats

### Dashboard
- `GET /api/dashboard/stats` - Get dashboard statistics

## Usage Examples

### 1. Register a New Farmer

```bash
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "9876543210",
    "name": "Ramesh Kumar",
    "password": "secure_password",
    "district": "Pune",
    "state": "Maharashtra"
  }'
```

### 2. Upload Plant Image

```bash
curl -X POST "http://localhost:8000/api/plants/identify" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "image=@plant_photo.jpg" \
  -F "latitude=18.5204" \
  -F "longitude=73.8567"
```

### 3. Create Farm

```bash
curl -X POST "http://localhost:8000/api/farms/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Farm",
    "soil_type": "black",
    "polygon_coordinates": [
      {"lat": 18.52, "lon": 73.85},
      {"lat": 18.53, "lon": 73.85},
      {"lat": 18.53, "lon": 73.86},
      {"lat": 18.52, "lon": 73.86}
    ]
  }'
```

### 4. Get Crop Recommendations

```bash
curl -X POST "http://localhost:8000/api/recommendations/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "season": "Kharif 2025",
    "budget": 50000
  }'
```

## Web Interface

The platform includes a full web interface accessible through the browser:

1. **Landing Page** (`/`) - Feature showcase
2. **Login** (`/login`) - User authentication
3. **Register** (`/register`) - New farmer registration
4. **Dashboard** (`/dashboard`) - Overview of stats and activity
5. **Plant Scanner** (`/plants/scanner`) - Upload and identify plants
6. **Farm Manager** (`/farms/create`) - Create and map farms
7. **Recommendations** (`/recommendations`) - Get crop suggestions
8. **Alerts** (`/alerts`) - View notifications
9. **Leaderboard** (`/leaderboard`) - Gamification rankings

## Gamification System

### Points
- Plant detected: 50 points
- Invasive plant detected: 100 points
- Plant destroyed: 25 bonus points
- Farm mapped: 100 points
- Crop recommendation used: 20 points

### Badges
- 🌟 **Early Adopter** - Register in first month
- 🌿 **Plant Guardian** - Detect 10 invasive plants (500 points)
- 🍃 **Carbon Champion** - Map farm and calculate carbon credits (100 points)
- 🏆 **Top Farmer** - Reach #1 on leaderboard (1000 points)
- 📚 **Knowledge Seeker** - Use recommendations 5 times (250 points)

## Development

### Database Migrations

The database is automatically created on first run. To reset:

```bash
# Delete existing database
rm agritech.db

# Restart application (database will be recreated)
uvicorn app.main:app --reload
```

### Testing API with Swagger UI

1. Start the server
2. Go to http://localhost:8000/docs
3. Click "Authorize" and enter your JWT token
4. Test endpoints interactively

## Troubleshooting

### Common Issues

**1. Import errors**
```bash
# Make sure you're in the project root directory
cd agrigravity

# Reinstall dependencies
pip install -r requirements.txt
```

**2. Gemini API errors**
- Check that your API key is correct in `.env`
- Verify API key has Gemini API enabled
- Check API quota limits

**3. Database errors**
```bash
# Reset database
rm agritech.db

# Restart application
```

**4. Image upload issues**
- Ensure `uploads/plants` directory exists
- Check file permissions
- Verify image size < 10MB

## Production Deployment

For production deployment:

1. **Change SECRET_KEY** to a strong random value
2. **Set DEBUG=False** in `.env`
3. **Use PostgreSQL** instead of SQLite (update DATABASE_URL)
4. **Add CORS origins** in `main.py`
5. **Use production WSGI server** (Gunicorn):

```bash
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

6. **Set up HTTPS** with reverse proxy (Nginx/Caddy)
7. **Enable rate limiting**
8. **Set up monitoring and logging**

## Future Enhancements

- WhatsApp/SMS integration (Twilio)
- Weather API integration
- Interactive map visualization (Leaflet.js)
- Multi-language support
- Mobile app (React Native/Flutter)
- Advanced analytics dashboard
- Crop disease prediction
- Market price forecasting

## License

MIT License

## Support

For issues or questions, please open an issue on GitHub or contact support.

---

**Built with ❤️ for Indian Farmers**
