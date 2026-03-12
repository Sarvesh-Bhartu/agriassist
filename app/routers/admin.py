from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional


from app.core.database import get_db
from app.core.security import verify_password, create_access_token, get_current_admin
from app.models.user import Admin, Farmer
from app.models.farm import Farm
from app.models.schemas import AdminLogin, AdminToken, AdminDashboardFarmSchema, VerifyDocumentRequest
from app.services.carbon_service import carbon_service
from app.services.gamification_service import gamification_service

router = APIRouter(prefix="/api/admin", tags=["Admin"])


# ─────────────────────────────────────────
#  POST /api/admin/login
# ─────────────────────────────────────────
@router.post("/login", response_model=AdminToken)
async def admin_login(credentials: AdminLogin, db: Session = Depends(get_db)):
    """Admin login — verify admin_id and password, return JWT token."""
    admin = db.query(Admin).filter(
        Admin.admin_id == credentials.admin_id,
        Admin.is_active == True
    ).first()

    if not admin or not verify_password(credentials.password, admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin ID or password"
        )

    token = create_access_token(data={"sub": admin.id, "role": "admin"})

    return AdminToken(
        access_token=token,
        token_type="bearer",
        admin_id=admin.admin_id,
        name=admin.name
    )


# ─────────────────────────────────────────
#  GET /api/admin/dashboard
# ─────────────────────────────────────────
@router.get("/dashboard", response_model=List[AdminDashboardFarmSchema])
async def admin_dashboard(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Returns all farmers' farms with document verification status."""
    farms = db.query(Farm).all()

    result = []
    for farm in farms:
        farmer = db.query(Farmer).filter(Farmer.id == farm.farmer_id).first()
        result.append(AdminDashboardFarmSchema(
            farm_id=farm.id,
            farm_name=farm.name,
            farmer_id=farm.farmer_id,
            farmer_name=farmer.name if farmer else "Unknown",
            area_hectares=farm.area_hectares,
            area_acres=farm.area_acres,
            carbon_credits_annual=farm.carbon_credits_annual,
            polygon_coordinates=farm.polygon_coordinates,
            document_url=farm.document_url,
            verification_status=farm.verification_status or "pending",
            verification_comments=farm.verification_comments,
            created_at=farm.created_at
        ))

    return result


# ─────────────────────────────────────────
#  POST /api/admin/farms/{farm_id}/verify
# ─────────────────────────────────────────
@router.post("/farms/{farm_id}/verify")
async def verify_farm_document(
    farm_id: str,
    body: VerifyDocumentRequest,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Approve or reject a farm document with optional comments."""
    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")

    if not farm.document_url:
        raise HTTPException(status_code=400, detail="This farm has no uploaded document to verify.")

    if body.status == "rejected" and not body.comments:
        raise HTTPException(
            status_code=400,
            detail="You must provide a comment when rejecting a document."
        )

    farm.verification_status = body.status
    farm.verification_comments = body.comments if body.status == "rejected" else None
    
    # Process deferred actions if approved
    if body.status == "approved":
        # Calculate and save Carbon Credits
        if farm.area_hectares and farm.soil_type:
            try:
                carbon_result = carbon_service.calculate_credits(
                    area_hectares=float(farm.area_hectares),
                    soil_type=farm.soil_type
                )
                farm.carbon_credits_annual = carbon_result['annual_credits']
                farm.carbon_value_inr = carbon_result['annual_value_inr']
            except Exception as e:
                print(f"Warning: Failed to calculate carbon credits upon approval: {e}")
                
        # Trigger Gamification Event Points
        try:
            await gamification_service.add_points(
                db=db,
                farmer_id=farm.farmer_id,
                points=100,
                reason="Mapped farm and got document approved",
                event_type='farm_mapped'
            )
        except Exception as e:
            print(f"Warning: Failed to award gamification points upon approval: {e}")

    db.commit()
    db.refresh(farm)

    return {
        "message": f"Farm document {body.status} successfully.",
        "farm_id": farm.id,
        "verification_status": farm.verification_status,
        "verification_comments": farm.verification_comments
    }


# ═══════════════════════════════════════════════════════════════
#  AI AGENT ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@router.get("/agents/portfolio")
async def agent_portfolio(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Agent 1: Portfolio Analysis — Business Intelligence report from live DB data."""
    from app.services.agents.agent_portfolio import run_portfolio_analysis_agent
    return run_portfolio_analysis_agent(db)


@router.get("/agents/personalized")
async def agent_personalized(
    top_n: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Agent 2: Personalized — Cross-sell/upsell opportunities and targeted campaigns."""
    from app.services.agents.agent_personalized import run_personalized_agent
    return run_personalized_agent(db, top_n=top_n)


@router.get("/agents/retention")
async def agent_retention(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Agent 3: Retention — At-risk farmers and area-level breakthrough strategies."""
    from app.services.agents.agent_retention import run_retention_agent
    return run_retention_agent(db)


@router.get("/agents/crop-advisor")
async def agent_crop_advisor(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Agent 4: Crop Advisor Audit — Quality evaluation of recommendations given to farmers."""
    from app.services.agents.agent_crop_advisor import run_crop_advisor_audit_agent
    return run_crop_advisor_audit_agent(db)


@router.get("/agents/visualization")
async def agent_visualization(
    query: str = Query(default="all", description="Natural language question or 'all' for all charts"),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Agent 5: Data Visualization — Generates heatmaps/charts from live DB data."""
    from app.services.agents.agent_visualization import run_visualization_agent
    return run_visualization_agent(db, query=query)


# ─────────────────────────────────────────
#  SSE Chat Endpoint — Orchestrator
# ─────────────────────────────────────────
@router.get("/chat")
async def admin_chat(
    query: str = Query(..., description="Admin natural language query"),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """
    Perplexity-style streaming chat.
    Streams SSE events: thinking → agent_pick → agent_start → agent_done → chart → answer → done
    """
    from app.services.agents.agent_orchestrator import stream_orchestrator

    async def event_stream():
        async for chunk in stream_orchestrator(query=query, db=db):
            yield chunk

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )
