from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import List, Optional
import json
import uuid
import os

from app.core.neo4j_driver import neo4j_driver
from app.core.security import get_current_urban_farmer
from app.models.urban_farmer_models import SpaceRecordResponse

from fastapi.templating import Jinja2Templates

# Calculate templates directory relative to this file
APP_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
templates = Jinja2Templates(directory=os.path.join(APP_DIR, "templates"))

router = APIRouter(prefix="/urban/space", tags=["Urban Space"])

# Ensure upload directory exists
UPLOAD_DIR = "uploads/urban_spaces"
os.makedirs(UPLOAD_DIR, exist_ok=True)

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
            # Convert Neo4j DateTime to string and ensure all fields are serializable
            space_dict = dict(node)
            if "created_at" in space_dict:
                space_dict["created_at"] = space_dict["created_at"].to_native().isoformat()
            spaces.append(space_dict)
            
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
