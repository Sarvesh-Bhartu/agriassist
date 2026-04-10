from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.core.security import verify_password, create_access_token, get_current_admin
from app.models.user import Admin, Farmer
from app.models.farm import Farm
from app.models.schemas import AdminLogin, AdminToken, AdminDashboardFarmSchema, VerifyDocumentRequest
from app.services.carbon_service import carbon_service
from app.services.gamification_service import gamification_service
from app.services.hash_service import generate_land_hash, generate_farmer_ref, farm_uuid_to_uint256
from app.services.blockchain_client import blockchain_client

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

    from fastapi.responses import JSONResponse
    response = JSONResponse(content={
        "access_token": token,
        "token_type": "bearer",
        "admin_id": admin.admin_id,
        "name": admin.name
    })
    response.set_cookie(
        key="admin_access_token",
        value=token,
        httponly=True,
        max_age=24 * 3600,
        samesite="lax",
        secure=False
    )
    return response


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
            created_at=farm.created_at,
            blockchain_tx_hash=farm.blockchain_tx_hash,
            blockchain_status=farm.blockchain_status,
            blockchain_block_number=farm.blockchain_block_number,
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

    blockchain_result = None

    # ── Process deferred actions if APPROVED ─────────────────────────────────
    if body.status == "approved":

        # 1. Calculate and save Carbon Credits
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

        # 2. Gamification: 100 points
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

        # 3. Blockchain: Record approval on Polygon Amoy
        #
        # Design: Non-blocking — if blockchain fails, the farm is STILL approved
        # in the DB. Admin workflows must not break due to chain unavailability.
        # blockchain_status will be 'failed' with blockchain_error set.
        try:
            # Generate deterministic hashes
            land_hash = generate_land_hash(farm)
            farmer_ref = generate_farmer_ref(farm.farmer_id, farm.id)
            numeric_farm_id = farm_uuid_to_uint256(farm.id)

            # Store the land hash in DB (even before blockchain call)
            farm.land_hash = land_hash

            print(f"[Blockchain] Approving farm {farm.id} → numeric_id={numeric_farm_id}")
            print(f"[Blockchain] land_hash={land_hash[:20]}... farmer_ref={farmer_ref[:20]}...")

            # Call Node.js API
            blockchain_result = await blockchain_client.approve_farm(
                farm_id=numeric_farm_id,
                farmer_ref=farmer_ref,
                land_hash=land_hash,
            )

            if blockchain_result.get("success"):
                farm.blockchain_tx_hash = blockchain_result["txHash"]
                farm.blockchain_block_number = str(blockchain_result["blockNumber"])
                farm.blockchain_status = "confirmed"
                farm.blockchain_verified_at = datetime.utcnow()
                farm.blockchain_error = None
                print(f"[Blockchain] TX confirmed: {blockchain_result['txHash']}")
            else:
                # Blockchain failed — record the error but don't block approval
                error_code = blockchain_result.get("code", "")
                error_msg = blockchain_result.get("error", "Unknown blockchain error")

                if error_code == "ALREADY_APPROVED":
                    # Farm was already on-chain — treat as confirmed
                    farm.blockchain_status = "already_approved"
                    farm.blockchain_error = "Farm was already approved on-chain"
                else:
                    farm.blockchain_status = "failed"
                    farm.blockchain_error = error_msg[:500]

                print(f"[Blockchain] Warning: {error_msg}")

        except Exception as e:
            # Catch-all: any unexpected error must not block the admin approval
            farm.blockchain_status = "failed"
            farm.blockchain_error = str(e)[:500]
            print(f"[Blockchain] Unexpected error: {e}")

    # ── Commit all changes ────────────────────────────────────────────────────
    db.commit()
    db.refresh(farm)

    # Build response with blockchain info
    response = {
        "message": f"Farm document {body.status} successfully.",
        "farm_id": farm.id,
        "verification_status": farm.verification_status,
        "verification_comments": farm.verification_comments,
    }

    if body.status == "approved":
        response["blockchain"] = {
            "status": farm.blockchain_status,
            "tx_hash": farm.blockchain_tx_hash,
            "block_number": farm.blockchain_block_number,
            "verified_at": farm.blockchain_verified_at.isoformat() if farm.blockchain_verified_at else None,
            "polygon_scan_url": (
                f"https://amoy.polygonscan.com/tx/{farm.blockchain_tx_hash}"
                if farm.blockchain_tx_hash else None
            ),
            "error": farm.blockchain_error,
        }

    return response

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
