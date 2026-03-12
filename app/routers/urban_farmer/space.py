from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import List, Optional
import json
import uuid
import os
from datetime import datetime

from app.core.neo4j_driver import neo4j_driver
from app.core.security import get_current_urban_farmer
from app.models.urban_farmer_models import (
    SpaceRecordResponse, PlantingPlan, SpaceAnalysisResult, 
    GrowthLogCreate, GrowthLogResponse
)
from app.services.vision_service import vision_service
from app.services.gemini_service import gemini_service
from app.utils.image_processing import ImageProcessor
from app.core.config import settings

from fastapi.templating import Jinja2Templates

# Calculate templates directory relative to this file
APP_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
templates = Jinja2Templates(directory=os.path.join(APP_DIR, "templates"))

from app.services.urban_gemini_service import (
    analyse_space as run_analysis,
    generate_planting_plan as run_gen_plan,
    chat_with_urban_ai
)

router = APIRouter(prefix="/urban/space", tags=["Urban Space"])

# Ensure upload directory exists
UPLOAD_DIR = "uploads/urban_spaces"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def _convert_neo4j_types(data):
    """Recursively convert Neo4j types (like DateTime) to JSON-serializable formats."""
    from neo4j.time import DateTime
    
    if isinstance(data, list):
        return [_convert_neo4j_types(item) for item in data]
    elif isinstance(data, dict):
        return {k: _convert_neo4j_types(v) for k, v in data.items()}
    elif isinstance(data, DateTime):
        return data.to_native().isoformat()
    return data

@router.get("/dashboard", response_class=HTMLResponse)
async def urban_dashboard_page(request: Request):
    """Render the Urban Farmer dashboard"""
    return templates.TemplateResponse("urban_farmer/dashboard.html", {"request": request})

@router.get("/list", response_model=List[dict])
async def list_urban_spaces(current_user: dict = Depends(get_current_urban_farmer)):
    """API endpoint to list all spaces for the current urban farmer"""
    session = neo4j_driver.get_session()
    try:
        query = '''
        MATCH (u:UrbanFarmer {id: $farmer_id})-[:OWNS_SPACE]->(s:SpaceRecord)
        RETURN s ORDER BY s.created_at DESC
        '''
        result = session.run(query, farmer_id=current_user["id"])
        
        spaces = []
        for record in result:
            node = record["s"]
            # Recursively convert Neo4j types for the entire node properties
            spaces.append(_convert_neo4j_types(dict(node)))
            
        return spaces
    finally:
        session.close()

@router.get("/submit", response_class=HTMLResponse)
async def submit_space_page(request: Request):
    """Render the Urban Space Submission page (Auth handled by JS)"""
    return templates.TemplateResponse("urban_farmer/space_submit.html", {"request": request})

@router.post("/submit", response_model=SpaceRecordResponse)
async def submit_space(
    request: Request,
    name: str = Form(...),
    space_type: str = Form(...),
    polygons: str = Form(..., description="JSON string of list of lists of coords"),
    images: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_urban_farmer)
):
    """
    Handle space submission with multi-image files and polygon data.
    The polygons JSON should match the order of images.
    """
    if len(images) > 3:
        raise HTTPException(status_code=400, detail="Maximum 3 images allowed")
        
    try:
        polygons_data = json.loads(polygons)
        if len(polygons_data) != len(images):
            raise HTTPException(status_code=400, detail="Polygon data count must match image count")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid polygon JSON format")

    session = neo4j_driver.get_session()
    try:
        space_id = str(uuid.uuid4())
        
        # Save images and store paths
        saved_image_paths = []
        for img in images:
            file_ext = img.filename.split(".")[-1]
            file_name = f"{space_id}_{uuid.uuid4().hex}.{file_ext}"
            file_path = os.path.join(UPLOAD_DIR, file_name)
            
            with open(file_path, "wb") as f:
                f.write(await img.read())
            saved_image_paths.append(file_path)

        # Create SpaceRecord node
        query = '''
        MATCH (u:UrbanFarmer {id: $farmer_id})
        CREATE (s:SpaceRecord {
            id: $id,
            name: $name,
            space_type: $space_type,
            image_paths: $image_paths,
            polygons_json: $polygons_json,
            status: "pending_analysis",
            created_at: datetime()
        })
        CREATE (u)-[:OWNS_SPACE]->(s)
        RETURN s
        '''
        
        result = session.run(
            query,
            farmer_id=current_user["id"],
            id=space_id,
            name=name,
            space_type=space_type,
            image_paths=saved_image_paths,
            polygons_json=polygons
        )
        
        record = result.single()
        if not record:
            raise HTTPException(status_code=500, detail="Failed to create space record")
            
        space_node = record["s"]
        
        # Note: Analysis by Gemini will happen in a separate step or background task
        # to avoid blocking the user response.
        
        return SpaceRecordResponse(
            id=space_node["id"],
            farmer_id=current_user["id"],
            name=space_node["name"],
            space_type=space_node["space_type"],
            status=space_node["status"],
            created_at=space_node["created_at"].to_native()
        )
        
    finally:
        session.close()


@router.post("/{space_id}/analyze")
async def analyze_space(
    space_id: str,
    current_user: dict = Depends(get_current_urban_farmer)
):
    """
    Trigger Gemini AI analysis for a specific space.
    Called manually by the user from the dashboard.
    """
    from app.services.urban_gemini_service import analyse_space as run_analysis
    from app.models.urban_farmer_models import SpaceAnalysisResult

    session = neo4j_driver.get_session()
    try:
        # 1. Fetch the space record from Neo4j
        result = session.run(
            """
            MATCH (u:UrbanFarmer {id: $farmer_id})-[:OWNS_SPACE]->(s:SpaceRecord {id: $space_id})
            RETURN s
            """,
            farmer_id=current_user["id"],
            space_id=space_id
        )
        record = result.single()
        if not record:
            raise HTTPException(status_code=404, detail="Space not found or unauthorized")

        space_node = record["s"]
        image_paths = list(space_node.get("image_paths", []))
        polygons_json = space_node.get("polygons_json", "[]")
        space_name = space_node.get("name", "")
        space_type = space_node.get("space_type", "balcony")

        # 2. Run Gemini analysis
        analysis = await run_analysis(space_name, space_type, image_paths, polygons_json)

        if "error" in analysis:
            raise HTTPException(status_code=500, detail=f"Gemini analysis failed: {analysis['error']}")

        # 3. Persist results back to Neo4j
        recommended_crops_json = json.dumps(analysis.get("recommended_crops", []))
        key_tips_json = json.dumps(analysis.get("key_tips", []))

        session.run(
            """
            MATCH (s:SpaceRecord {id: $space_id})
            SET s.status = "analyzed",
                s.estimated_area_sqm = $area,
                s.sunlight_level = $sunlight_level,
                s.sunlight_hours_per_day = $sunlight_hours,
                s.recommended_crops_json = $crops,
                s.estimated_carbon_credits_per_year = $carbon,
                s.estimated_monthly_income_inr = $income,
                s.soil_recommendation = $soil,
                s.key_tips_json = $tips,
                s.overall_suitability = $suitability,
                s.suitability_reason = $suitability_reason,
                s.analyzed_at = datetime()
            """,
            space_id=space_id,
            area=analysis.get("estimated_area_sqm"),
            sunlight_level=analysis.get("sunlight_level"),
            sunlight_hours=analysis.get("sunlight_hours_per_day"),
            crops=recommended_crops_json,
            carbon=analysis.get("estimated_carbon_credits_per_year"),
            income=analysis.get("estimated_monthly_income_inr"),
            soil=analysis.get("soil_recommendation"),
            tips=key_tips_json,
            suitability=analysis.get("overall_suitability"),
            suitability_reason=analysis.get("suitability_reason")
        )

        # 4. Return the result
        from app.models.urban_farmer_models import CropRecommendation
        crops = [CropRecommendation(**c) for c in analysis.get("recommended_crops", [])]

        return SpaceAnalysisResult(
            space_id=space_id,
            status="analyzed",
            estimated_area_sqm=analysis.get("estimated_area_sqm"),
            sunlight_level=analysis.get("sunlight_level"),
            sunlight_hours_per_day=analysis.get("sunlight_hours_per_day"),
            recommended_crops=crops,
            estimated_carbon_credits_per_year=analysis.get("estimated_carbon_credits_per_year"),
            estimated_monthly_income_inr=analysis.get("estimated_monthly_income_inr"),
            soil_recommendation=analysis.get("soil_recommendation"),
            key_tips=analysis.get("key_tips"),
            overall_suitability=analysis.get("overall_suitability"),
            suitability_reason=analysis.get("suitability_reason")
        )

    finally:
        session.close()

@router.post("/{space_id}/plan", response_model=PlantingPlan)
async def create_planting_plan(
    space_id: str,
    current_user: dict = Depends(get_current_urban_farmer)
):
    """
    Generate a detailed planting plan for a space that has already been analyzed.
    """
    from app.services.urban_gemini_service import generate_planting_plan as run_gen_plan

    session = neo4j_driver.get_session()
    try:
        # 1. Fetch space and analysis from Neo4j
        result = session.run(
            """
            MATCH (u:UrbanFarmer {id: $farmer_id})-[:OWNS_SPACE]->(s:SpaceRecord {id: $space_id})
            RETURN s
            """,
            farmer_id=current_user["id"],
            space_id=space_id
        )
        record = result.single()
        if not record:
            raise HTTPException(status_code=404, detail="Space not found or unauthorized")

        space_node = record["s"]
        if space_node.get("status") != "analyzed":
            raise HTTPException(status_code=400, detail="Space must be analyzed before generating a plan")

        # Reconstruct analysis dict from node properties
        analysis_result = {
            "estimated_area_sqm": space_node.get("estimated_area_sqm"),
            "sunlight_level": space_node.get("sunlight_level"),
            "sunlight_hours_per_day": space_node.get("sunlight_hours_per_day"),
            "recommended_crops": json.loads(space_node.get("recommended_crops_json", "[]"))
        }

        # 2. Generate Plan with Gemini
        plan_data = await run_gen_plan(
            space_node.get("name", "My Garden"),
            space_node.get("space_type", "balcony"),
            analysis_result
        )

        if "error" in plan_data:
            raise HTTPException(status_code=500, detail=f"Plan generation failed: {plan_data['error']}")

        # 3. Save to Neo4j
        plan_id = str(uuid.uuid4())
        steps_json = json.dumps(plan_data.get("steps", []))
        budget_json = json.dumps(plan_data.get("budget_breakdown", []))
        tips_json = json.dumps(plan_data.get("maintenance_tips", []))

        session.run(
            """
            MATCH (s:SpaceRecord {id: $space_id})
            CREATE (p:PlantingPlan {
                id: $plan_id,
                name: $name,
                total_budget_est: $budget,
                expected_monthly_harvest_kg: $harvest,
                steps_json: $steps_json,
                budget_json: $budget_json,
                layout_diagram_svg: $svg,
                maintenance_tips_json: $tips_json,
                created_at: datetime()
            })
            CREATE (s)-[:HAS_PLAN]->(p)
            SET s.status = "planned"
            """,
            space_id=space_id,
            plan_id=plan_id,
            name=plan_data.get("name"),
            budget=float(plan_data.get("total_budget_est", 0)),
            harvest=float(plan_data.get("expected_monthly_harvest_kg", 0)),
            steps_json=steps_json,
            budget_json=budget_json,
            svg=plan_data.get("layout_diagram_svg"),
            tips_json=tips_json
        )

        return PlantingPlan(
            plan_id=plan_id,
            space_id=space_id,
            name=plan_data.get("name"),
            total_budget_est=plan_data.get("total_budget_est"),
            expected_monthly_harvest_kg=plan_data.get("expected_monthly_harvest_kg"),
            steps=plan_data.get("steps"),
            budget_breakdown=plan_data.get("budget_breakdown"),
            layout_diagram_svg=plan_data.get("layout_diagram_svg"),
            maintenance_tips=plan_data.get("maintenance_tips"),
            created_at=datetime.now()
        )

    finally:
        session.close()


@router.get("/{space_id}/plan/view", response_class=HTMLResponse)
async def view_planting_plan_report(
    request: Request,
    space_id: str,
    current_user: dict = Depends(get_current_urban_farmer)
):
    """Render a printable report for a space's planting plan."""
    session = neo4j_driver.get_session()
    try:
        query = """
        MATCH (u:UrbanFarmer {id: $farmer_id})-[:OWNS_SPACE]->(s:SpaceRecord {id: $space_id})-[:HAS_PLAN]->(p:PlantingPlan)
        RETURN p
        """
        result = session.run(query, farmer_id=current_user["id"], space_id=space_id)
        record = result.single()
        
        if not record:
            raise HTTPException(status_code=404, detail="Plan not found")
            
        p = record["p"]
        plan_dict = {
            "name": p["name"],
            "total_budget_est": p["total_budget_est"],
            "expected_monthly_harvest_kg": p["expected_monthly_harvest_kg"],
            "steps": json.loads(p["steps_json"]),
            "budget_breakdown": json.loads(p["budget_json"]),
            "layout_diagram_svg": p.get("layout_diagram_svg"),
            "maintenance_tips": json.loads(p["maintenance_tips_json"]),
            "created_at": p["created_at"].to_native()
        }
        
        return templates.TemplateResponse(
            "urban_farmer/plan_report.html", 
            {"request": request, "plan": plan_dict}
        )
    finally:
        session.close()


@router.get("/{space_id}/plan", response_model=Optional[PlantingPlan])
async def get_planting_plan(
    space_id: str,
    current_user: dict = Depends(get_current_urban_farmer)
):
    """Retrieve the planting plan for a space if it exists."""
    session = neo4j_driver.get_session()
    try:
        query = """
        MATCH (u:UrbanFarmer {id: $farmer_id})-[:OWNS_SPACE]->(s:SpaceRecord {id: $space_id})-[:HAS_PLAN]->(p:PlantingPlan)
        RETURN p
        """
        result = session.run(query, farmer_id=current_user["id"], space_id=space_id)
        record = result.single()
        
        if not record:
            return None
            
        p = record["p"]
        return PlantingPlan(
            plan_id=p["id"],
            space_id=space_id,
            name=p["name"],
            total_budget_est=p["total_budget_est"],
            expected_monthly_harvest_kg=p["expected_monthly_harvest_kg"],
            steps=json.loads(p["steps_json"]),
            budget_breakdown=json.loads(p["budget_json"]),
            layout_diagram_svg=p.get("layout_diagram_svg"),
            maintenance_tips=json.loads(p["maintenance_tips_json"]),
            created_at=p["created_at"].to_native()
        )
    finally:
        session.close()
@router.post("/plan/{plan_id}/log", response_model=GrowthLogResponse)
async def create_growth_log(
    plan_id: str,
    note: str = Form(...),
    image: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_urban_farmer)
):
    """Create a new growth log entry for a planting plan"""
    session = neo4j_driver.get_session()
    try:
        # Verify ownership of the plan's space
        check_query = """
        MATCH (u:UrbanFarmer {id: $farmer_id})-[:OWNS_SPACE]->(s:SpaceRecord)-[:HAS_PLAN]->(p:PlantingPlan {id: $plan_id})
        RETURN p
        """
        result = session.run(check_query, farmer_id=current_user["id"], plan_id=plan_id)
        if not result.single():
            raise HTTPException(status_code=404, detail="Plan not found or unauthorized")

        log_id = str(uuid.uuid4())
        image_url = None
        
        if image:
            log_upload_dir = "uploads/growth_logs"
            os.makedirs(log_upload_dir, exist_ok=True)
            file_ext = image.filename.split(".")[-1]
            file_name = f"{log_id}.{file_ext}"
            file_path = os.path.join(log_upload_dir, file_name)
            
            with open(file_path, "wb") as f:
                f.write(await image.read())
            image_url = f"/{file_path}"

        query = """
        MATCH (p:PlantingPlan {id: $plan_id})
        CREATE (l:GrowthLog {
            id: $id,
            timestamp: datetime(),
            note: $note,
            image_url: $image_url
        })
        CREATE (p)-[:HAS_LOG]->(l)
        RETURN l
        """
        
        result = session.run(query, plan_id=plan_id, id=log_id, note=note, image_url=image_url)
        record = result.single()
        node = record["l"]
        
        return GrowthLogResponse(
            id=node["id"],
            plan_id=plan_id,
            timestamp=node["timestamp"].to_native(),
            note=node["note"],
            image_url=node["image_url"]
        )
    finally:
        session.close()

@router.get("/plan/{plan_id}/logs", response_model=List[GrowthLogResponse])
async def list_growth_logs(
    plan_id: str,
    current_user: dict = Depends(get_current_urban_farmer)
):
    """Retrieve all growth logs for a specific planting plan"""
    session = neo4j_driver.get_session()
    try:
        query = """
        MATCH (u:UrbanFarmer {id: $farmer_id})-[:OWNS_SPACE]->(s:SpaceRecord)-[:HAS_PLAN]->(p:PlantingPlan {id: $plan_id})-[:HAS_LOG]->(l:GrowthLog)
        RETURN l ORDER BY l.timestamp DESC
        """
        result = session.run(query, farmer_id=current_user["id"], plan_id=plan_id)
        
        logs = []
        for record in result:
            node = record["l"]
            logs.append(GrowthLogResponse(
                id=node["id"],
                plan_id=plan_id,
                timestamp=node["timestamp"].to_native(),
                note=node["note"],
                image_url=node["image_url"]
            ))
            
        return logs
    finally:
        session.close()

@router.get("/market/prices")
async def get_urban_market_prices(
    current_user: dict = Depends(get_current_urban_farmer)
):
    """Get market prices filtered for crops the farmer is actually growing"""
    session = neo4j_driver.get_session()
    try:
        # 1. Find all crop names in the farmer's planting plans
        query = """
        MATCH (u:UrbanFarmer {id: $farmer_id})-[:OWNS_SPACE]->(s:SpaceRecord)-[:HAS_PLAN]->(p:PlantingPlan)
        RETURN p.steps_json as steps
        """
        result = session.run(query, farmer_id=current_user["id"])
        
        target_crops = set()
        for record in result:
            steps = json.loads(record["steps"] or "[]")
            for step in steps:
                target_crops.add(step["crop_name"])
        
        if not target_crops:
            return []

        # 2. Fetch prices from SQL for these crops
        from app.core.database import SessionLocal
        from app.models.crop import MarketPrice
        db = SessionLocal()
        try:
            # Simple substring matching or exact matching
            prices = db.query(MarketPrice).filter(
                MarketPrice.crop_name.in_(list(target_crops))
            ).order_by(MarketPrice.price_date.desc()).limit(10).all()
            
            return [{
                "crop_name": p.crop_name,
                "price_per_kg": p.price_per_kg,
                "market_name": p.market_name,
                "price_date": p.price_date.isoformat(),
                "trend": p.trend
            } for p in prices]
        finally:
            db.close()
            
    finally:
        session.close()

@router.post("/chat")
async def urban_ai_chat(
    request: Request,
    current_user: dict = Depends(get_current_urban_farmer)
):
    """Context-aware chat for urban farmers"""
    try:
        data = await request.json()
        message = data.get("message")
        history = data.get("history", [])
        
        if not message:
            raise HTTPException(status_code=400, detail="Message is required")

        session = neo4j_driver.get_session()
        try:
            # 1. Fetch user context (Spaces and Plans)
            result = session.run("""
                MATCH (u:UrbanFarmer {id: $farmer_id})
                OPTIONAL MATCH (u)-[:OWNS_SPACE]->(s:SpaceRecord)
                OPTIONAL MATCH (s)-[:HAS_PLAN]->(p:PlantingPlan)
                RETURN s, p
            """, farmer_id=current_user["id"])
            
            context = {"spaces": [], "plans": []}
            for record in result:
                if record["s"]:
                    s_dict = _convert_neo4j_types(dict(record["s"]))
                    if s_dict not in context["spaces"]: context["spaces"].append(s_dict)
                if record["p"]:
                    p_dict = _convert_neo4j_types(dict(record["p"]))
                    if p_dict not in context["plans"]: context["plans"].append(p_dict)
            
            # 2. Call Gemini service
            response = await chat_with_urban_ai(message, context, history)
            return {"response": response}
            
        finally:
            session.close()
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/scan/disease")
async def scan_plant_disease(
    image: UploadFile = File(...),
    current_user: dict = Depends(get_current_urban_farmer)
):
    """Identify plant and disease for Urban Farmers (Reuse YOLO + Gemini)"""
    image_bytes = await image.read()
    
    # Validate and compress
    is_valid, msg = ImageProcessor.validate_image(image_bytes)
    if not is_valid:
        raise HTTPException(400, msg)
    
    compressed_bytes = ImageProcessor.compress_image(image_bytes)
    
    # Save image
    image_filename = f"urban_{current_user['id']}_{uuid.uuid4().hex}.jpg"
    image_path = os.path.join("uploads/plants", image_filename)
    os.makedirs(os.path.dirname(image_path), exist_ok=True)
    
    with open(image_path, "wb") as f:
        f.write(compressed_bytes)
        
    try:
        # 1. YOLO for bounding boxes
        output_dir = os.path.dirname(image_path)
        yolo_result = vision_service.scan_plant(image_path, output_dir)
        
        # 2. Gemini for botanical details
        gemini_data = await gemini_service.identify_plant(image_bytes)
        
        if gemini_data:
            species = gemini_data.get("species", "Unknown")
            status = gemini_data.get("threat_level", "Low")
            is_unhealthy = gemini_data.get("is_invasive", False) or "disease" in status.lower()
        else:
            predictions = yolo_result.get("predictions", [])
            species = predictions[0]["class"] if predictions else "Unknown"
            status = predictions[0]["status"] if predictions else "Healthy"
            is_unhealthy = "disease" in status.lower()

        # 3. Store in Neo4j (Simplified for Urban)
        session = neo4j_driver.get_session()
        try:
            session.run("""
                MATCH (u:UrbanFarmer {id: $farmer_id})
                CREATE (d:PlantDetection {
                    id: $id,
                    species: $species,
                    status: $status,
                    timestamp: datetime(),
                    image_url: $image_url,
                    is_unhealthy: $is_unhealthy
                })
                CREATE (u)-[:PERFORMED_SCAN]->(d)
            """, 
            farmer_id=current_user["id"],
            id=str(uuid.uuid4()),
            species=species,
            status=status,
            image_url=f"/{image_path}",
            is_unhealthy=is_unhealthy)
        finally:
            session.close()

        return {
            "species": species,
            "status": status,
            "is_unhealthy": is_unhealthy,
            "image_url": f"/{image_path}"
        }

    except Exception as e:
        if os.path.exists(image_path): os.remove(image_path)
        raise HTTPException(500, f"Scanner failed: {e}")
