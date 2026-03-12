import os
import datetime
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import init_db
from app.core.neo4j_driver import neo4j_driver
from app.core.exceptions import AppException, app_exception_handler
from app.core.config import settings

# Import routers
from app.routers import auth, plants, farms, recommendations, alerts, gamification, dashboard, voice_bot
from app.routers import admin as admin_router
from app.routers.urban_farmer import auth as urban_auth
from app.routers.urban_farmer import space as urban_space

# Create FastAPI app
app = FastAPI(
    title="URBAN FARMER ECOSYSTEM v2.0",
    description="Isolated Development for city-scale green cooling and balcony optimization",
    version="2.0.0-BETA",
    debug=True
)

print("🚀 DEBUG: Registered Urban Auth Router")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
app.add_exception_handler(AppException, app_exception_handler)

# Ensure upload directories exist
os.makedirs("uploads", exist_ok=True)
os.makedirs("uploads/plants", exist_ok=True)
os.makedirs("uploads/farms", exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Templates
templates = Jinja2Templates(directory="app/templates")

# Include API routers - FORCE URBAN FIRST
app.include_router(urban_auth.router)
app.include_router(urban_space.router)
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(plants.router)
app.include_router(farms.router)
app.include_router(recommendations.router)
app.include_router(alerts.router)
app.include_router(gamification.router)
app.include_router(voice_bot.router)
app.include_router(admin_router.router)

@app.get("/urban-ping")
async def urban_ping():
    return {"status": "URBAN_ACTIVE", "version": "2.0.0-BETA", "timestamp": str(datetime.datetime.now())}

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database tables and connections"""
    init_db()
    from script_create_admin import create_admin
    create_admin()
    
    try:
        neo4j_driver.connect()
    except Exception as e:
        print(f"⚠️ Warning: Neo4j failure: {e}")
        
    print("🚀 URBAN FARMER ECOSYSTEM v2.0 IS LIVE")
    print("📚 NEW API DOCS: http://localhost:8000/docs")


@app.on_event("shutdown")
async def shutdown_event():
    """Close database connections on shutdown"""
    neo4j_driver.close()


@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "app": "URBAN FARMER ECOSYSTEM v2.0",
        "version": "2.0.0-BETA"
    }


@app.get("/health/neo4j")
async def neo4j_health_check():
    try:
        session = neo4j_driver.get_session()
        result = session.run("RETURN 1 as n")
        record = result.single()
        session.close()
        if record and record["n"] == 1:
            return {"status": "connected"}
        return {"status": "error"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# Web page routes
@app.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("auth/login.html", {"request": request})

@app.get("/register")
async def register_page(request: Request):
    return templates.TemplateResponse("auth/register.html", {"request": request})

@app.get("/dashboard")
async def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/plants/scanner")
async def plant_scanner_page(request: Request):
    return templates.TemplateResponse("plants/scanner.html", {"request": request})

@app.get("/plants/history")
async def plant_history_page(request: Request):
    return templates.TemplateResponse("plants/history.html", {"request": request})

@app.get("/farms/create")
async def create_farm_page(request: Request):
    return templates.TemplateResponse("farms/create.html", {"request": request})

@app.get("/farms")
async def farms_index_page(request: Request):
    return templates.TemplateResponse("farms/index.html", {"request": request})

@app.get("/farms/{farm_id}")
async def farm_detail_page(request: Request, farm_id: str):
    return templates.TemplateResponse("farms/detail.html", {"request": request, "farm_id": farm_id})

@app.get("/admin")
async def admin_login_page(request: Request):
    return templates.TemplateResponse("admin/login.html", {"request": request})

@app.get("/admin/dashboard")
async def admin_dashboard_page(request: Request):
    return templates.TemplateResponse("admin/dashboard.html", {"request": request})

@app.get("/recommendations")
async def recommendations_page(request: Request):
    return templates.TemplateResponse("recommendations/form.html", {"request": request})

@app.get("/alerts")
async def alerts_page(request: Request):
    return templates.TemplateResponse("alerts/list.html", {"request": request})

@app.get("/leaderboard")
async def leaderboard_page(request: Request):
    return templates.TemplateResponse("leaderboard.html", {"request": request})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8001, reload=True)
