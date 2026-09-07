"""
OmniSubEstimator API - FastAPI Backend Service.
Provides REST endpoints for blueprint uploading, computer vision wall/room parsing,
Gemini vision material takeoff analysis, RS Means pricing calculations, CSV export,
and subcontractor subscription checkout.
"""

import os
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Response
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from contextlib import asynccontextmanager
from backend.pricing_db import (
    get_all_pricing_items,
    calculate_takeoff_materials,
    RSMeansItem,
)
from backend.blueprint_parser import parse_blueprint_file
from backend.gemini_analyzer import analyze_blueprint_materials_with_gemini
from backend.export_service import generate_takeoff_csv
from backend.bid_scraper.api import router as bids_router
from backend.bid_scraper.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="OmniSubEstimator API",
    description="AI Blueprint Parser & Material Takeoff Engine API for Subcontractors",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(bids_router)


class MaterialItem(BaseModel):
    csi_code: Optional[str] = "09 00 00"
    category: str
    item_name: str
    quantity: float
    unit: str
    unit_cost_est: float
    total_cost_est: float


class TakeoffResponse(BaseModel):
    filename: str
    project_title: Optional[str] = "Untitled Blueprint"
    scale: Optional[str] = "1/4\" = 1'-0\""
    total_floor_area_sqft: float = 0.0
    total_wall_linear_ft: float = 0.0
    detected_rooms: List[Dict[str, Any]] = Field(default_factory=list)
    detected_walls: List[Dict[str, Any]] = Field(default_factory=list)
    materials: List[MaterialItem] = Field(default_factory=list)
    total_estimated_cost: float = 0.0
    ai_analysis: Optional[Dict[str, Any]] = None
    annotated_overlay_base64: Optional[str] = None


class EstimateRequest(BaseModel):
    takeoff_data: Dict[str, Any]
    pricing_tier: Optional[str] = "standard"
    labor_rate_multiplier: Optional[float] = 0.35
    overhead_profit_multiplier: Optional[float] = 0.15
    contingency_multiplier: Optional[float] = 0.05


class EstimateResponse(BaseModel):
    project_title: str
    pricing_tier: str
    material_subtotal: float
    labor_estimate: float
    overhead_and_profit: float
    contingency: float
    grand_total: float
    item_count: int


class ExportCSVRequest(BaseModel):
    takeoff_data: Dict[str, Any]
    estimate_data: Optional[Dict[str, Any]] = None


class StripeCheckoutRequest(BaseModel):
    plan_tier: str = "starter"  # 'starter' ($99/mo) or 'pro' ($249/mo)
    success_url: Optional[str] = "https://omnitender.us/estimator.html?checkout=success"
    cancel_url: Optional[str] = "https://omnitender.us/estimator.html?checkout=cancel"


@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "OmniSubEstimator API",
        "version": "0.2.0",
        "features": [
            "PyMuPDF vector blueprint parsing",
            "OpenCV wall & room boundary detection",
            "Gemini 2.5 Pro/Flash Vision material identification",
            "RS Means standard pricing seed database",
            "Subcontractor bid quote calculation & CSV export",
        ],
    }


@app.get("/healthcheck")
def healthcheck():
    return {"status": "ok"}


@app.get("/pricing", response_model=List[RSMeansItem])
def list_rs_means_pricing():
    """Returns the RS Means standard material catalog and unit prices."""
    return get_all_pricing_items()


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@app.get("/estimator", response_class=FileResponse)
def get_estimator_page():
    """Serves the interactive OmniSubEstimator takeoff UI."""
    path = os.path.join(ROOT_DIR, "estimator.html")
    if not os.path.exists(path):
        path = "estimator.html"
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="estimator.html not found")
    return FileResponse(path, media_type="text/html")


@app.get("/logo.svg", response_class=FileResponse)
def get_logo():
    path = os.path.join(ROOT_DIR, "logo.svg")
    if not os.path.exists(path):
        path = "logo.svg"
    return FileResponse(path, media_type="image/svg+xml")


@app.get("/style.css", response_class=FileResponse)
def get_style():
    path = os.path.join(ROOT_DIR, "style.css")
    if not os.path.exists(path):
        path = "style.css"
    return FileResponse(path, media_type="text/css")


@app.get("/bids", response_class=FileResponse)
@app.get("/rfp-search", response_class=FileResponse)
def get_rfp_search_page():
    """Serves the interactive OmniTender NC Municipal Bids & Proposals UI."""
    path = os.path.join(ROOT_DIR, "rfp-search.html")
    if not os.path.exists(path):
        path = "rfp-search.html"
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="rfp-search.html not found")
    return FileResponse(path, media_type="text/html")


@app.post("/upload", response_model=TakeoffResponse)
async def upload_blueprint(
    file: UploadFile = File(...),
    project_title: Optional[str] = Form("Blueprint Takeoff"),
    finish_level: Optional[str] = Form("standard"),
):
    if not file.filename.lower().endswith((".pdf", ".png", ".jpg", ".jpeg")):
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format. Please upload a PDF or image file (.pdf, .png, .jpg, .jpeg).",
        )

    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty.",
        )

    try:
        # 1. Computer Vision & Vector Document Parsing
        parsed_doc = parse_blueprint_file(contents, file.filename)
    except Exception as parse_err:
        raise HTTPException(
            status_code=422,
            detail=f"Blueprint parsing error: {str(parse_err)}",
        )

    detected_rooms = parsed_doc.get("detected_rooms", [])
    detected_walls = parsed_doc.get("detected_walls", [])
    total_floor_area = parsed_doc.get("total_floor_area_sqft", 0.0)
    total_wall_ft = parsed_doc.get("total_wall_linear_ft", 0.0)

    # 2. Gemini Vision Material & Specifications Inspection
    # Rendered first page preview / image analysis
    ai_analysis = analyze_blueprint_materials_with_gemini(
        image_bytes=contents,
        mime_type="application/pdf" if file.filename.lower().endswith(".pdf") else "image/jpeg",
        rooms=detected_rooms,
        walls=detected_walls,
    )

    resolved_finish = finish_level or ai_analysis.get("finish_level", "standard")

    # 3. RS Means Itemized Material Takeoff Calculation
    material_dicts = calculate_takeoff_materials(
        total_floor_area_sqft=total_floor_area,
        total_wall_linear_ft=total_wall_ft,
        wall_height_ft=10.0,
        room_count=len(detected_rooms),
        finish_level=resolved_finish,
    )

    materials = [MaterialItem(**item) for item in material_dicts]
    total_material_cost = round(sum(m.total_cost_est for m in materials), 2)

    return TakeoffResponse(
        filename=file.filename,
        project_title=project_title,
        scale=parsed_doc.get("scale", "1/4\" = 1'-0\""),
        total_floor_area_sqft=total_floor_area,
        total_wall_linear_ft=total_wall_ft,
        detected_rooms=detected_rooms,
        detected_walls=detected_walls,
        materials=materials,
        total_estimated_cost=total_material_cost,
        ai_analysis=ai_analysis,
        annotated_overlay_base64=parsed_doc.get("annotated_overlay_base64"),
    )


@app.post("/estimate", response_model=EstimateResponse)
def calculate_estimate(request: EstimateRequest):
    takeoff = request.takeoff_data
    materials = takeoff.get("materials", [])

    subtotal = sum(float(m.get("total_cost_est", 0.0)) for m in materials)
    labor_rate = request.labor_rate_multiplier if request.labor_rate_multiplier is not None else 0.35
    op_rate = request.overhead_profit_multiplier if request.overhead_profit_multiplier is not None else 0.15
    contingency_rate = request.contingency_multiplier if request.contingency_multiplier is not None else 0.05

    labor_markup = subtotal * labor_rate
    overhead_and_profit = subtotal * op_rate
    contingency = subtotal * contingency_rate
    total_quote = subtotal + labor_markup + overhead_and_profit + contingency

    return EstimateResponse(
        project_title=takeoff.get("project_title", "Blueprint Estimate"),
        pricing_tier=request.pricing_tier or "standard",
        material_subtotal=round(subtotal, 2),
        labor_estimate=round(labor_markup, 2),
        overhead_and_profit=round(overhead_and_profit, 2),
        contingency=round(contingency, 2),
        grand_total=round(total_quote, 2),
        item_count=len(materials),
    )


@app.post("/export/csv")
def export_csv(request: ExportCSVRequest):
    """Generates and streams a CSV file of the takeoff and estimate."""
    csv_content = generate_takeoff_csv(request.takeoff_data, request.estimate_data)
    filename = request.takeoff_data.get("filename", "blueprint").replace(".pdf", "").replace(".png", "")
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}_takeoff_estimate.csv"'},
    )


@app.post("/stripe/create-checkout-session")
def create_checkout_session(request: StripeCheckoutRequest):
    """
    Subcontractor subscription checkout endpoint.
    If STRIPE_SECRET_KEY is configured in the environment, generates a real Stripe Session.
    Otherwise returns a simulated checkout URL and session id for MVP demo and testing.
    """
    plan_prices = {
        "starter": {"amount": 9900, "name": "OmniSubEstimator Starter ($99/mo)"},
        "pro": {"amount": 24900, "name": "OmniSubEstimator Pro Contractor ($249/mo)"},
    }
    tier_info = plan_prices.get(request.plan_tier.lower(), plan_prices["starter"])
    stripe_key = os.environ.get("STRIPE_SECRET_KEY")

    if stripe_key:
        try:
            import stripe
            stripe.api_key = stripe_key
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{
                    "price_data": {
                        "currency": "usd",
                        "product_data": {"name": tier_info["name"]},
                        "unit_amount": tier_info["amount"],
                        "recurring": {"interval": "month"},
                    },
                    "quantity": 1,
                }],
                mode="subscription",
                success_url=request.success_url,
                cancel_url=request.cancel_url,
            )
            return {"session_id": session.id, "checkout_url": session.url}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")

    # Mock checkout for testing / staging
    return {
        "session_id": f"cs_test_mock_{request.plan_tier}",
        "checkout_url": f"{request.success_url}&simulated=true&tier={request.plan_tier}",
        "message": f"Simulated checkout session for {tier_info['name']}",
    }
