from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import init_db
from app.core.exceptions import AppException, app_exception_handler
from app.core.config import settings

# Import routers
from app.routers import auth, plants, farms, recommendations, alerts, gamification, dashboard

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="AI-Powered Agricultural Assistant Platform",
    version="1.0.0",
    debug=settings.DEBUG
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
app.add_exception_handler(AppException, app_exception_handler)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Templates
templates = Jinja2Templates(directory="app/templates")

# Include API routers
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(plants.router)
app.include_router(farms.router)
app.include_router(recommendations.router)
app.include_router(alerts.router)
app.include_router(gamification.router)


# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database tables"""
    init_db()
    print("✅ Database initialized")
    print(f"🚀 {settings.APP_NAME} is running!")
    print(f"📚 API Documentation: http://localhost:8000/docs")


# Root endpoint - Landing page
@app.get("/")
async def root(request: Request):
    """Landing page"""
    return templates.TemplateResponse("index.html", {"request": request})


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": "1.0.0"
    }


# Web page routes (for Jinja2 templates)
@app.get("/login")
async def login_page(request: Request):
    """Login page"""
    return templates.TemplateResponse("auth/login.html", {"request": request})


@app.get("/register")
async def register_page(request: Request):
    """Registration page"""
    return templates.TemplateResponse("auth/register.html", {"request": request})


@app.get("/dashboard")
async def dashboard_page(request: Request):
    """Dashboard page"""
    return  templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/plants/scanner")
async def plant_scanner_page(request: Request):
    """Plant scanner page"""
    return templates.TemplateResponse("plants/scanner.html", {"request": request})


@app.get("/plants/history")
async def plant_history_page(request: Request):
    """Plant history page"""
    return templates.TemplateResponse("plants/history.html", {"request": request})


@app.get("/farms/create")
async def create_farm_page(request: Request):
    """Create farm page"""
    return templates.TemplateResponse("farms/create.html", {"request": request})


@app.get("/farms/{farm_id}")
async def farm_detail_page(request: Request, farm_id: str):
    """Farm detail page"""
    return templates.TemplateResponse("farms/detail.html", {"request": request, "farm_id": farm_id})


@app.get("/recommendations")
async def recommendations_page(request: Request):
    """Crop recommendations page"""
    return templates.TemplateResponse("recommendations/form.html", {"request": request})


@app.get("/alerts")
async def alerts_page(request: Request):
    """Alerts page"""
    return templates.TemplateResponse("alerts/list.html", {"request": request})


@app.get("/leaderboard")
async def leaderboard_page(request: Request):
    """Leaderboard page"""
    return templates.TemplateResponse("leaderboard.html", {"request": request})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
