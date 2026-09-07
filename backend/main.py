import io
import json
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(
    title="OmniSubEstimator API",
    description="AI Blueprint Parser & Material Takeoff Engine API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class MaterialItem(BaseModel):
    category: str
    item_name: str
    quantity: float
    unit: str
    unit_cost_est: float
    total_cost_est: float


class TakeoffResponse(BaseModel):
    filename: str
    project_title: Optional[str] = "Untitled Blueprint"
    detected_rooms: List[Dict[str, Any]]
    detected_walls: List[Dict[str, Any]]
    materials: List[MaterialItem]
    total_estimated_cost: float


@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "OmniSubEstimator API",
        "version": "0.1.0",
    }


@app.get("/healthcheck")
def healthcheck():
    return {"status": "ok"}


@app.post("/upload", response_model=TakeoffResponse)
async def upload_blueprint(
    file: UploadFile = File(...),
    project_title: Optional[str] = Form("Blueprint Takeoff"),
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

    # Mock/Initial parser baseline logic for MVP scaffold
    mock_materials = [
        MaterialItem(
            category="Drywall",
            item_name='1/2" Gypsum Board (4x8 ft)',
            quantity=120,
            unit="sheets",
            unit_cost_est=15.50,
            total_cost_est=1860.00,
        ),
        MaterialItem(
            category="Framing",
            item_name='2x4x10 ft Wood Studs',
            quantity=85,
            unit="pieces",
            unit_cost_est=7.20,
            total_cost_est=612.00,
        ),
        MaterialItem(
            category="Flooring",
            item_name="Commercial Vinyl Plank Flooring",
            quantity=1400,
            unit="sq ft",
            unit_cost_est=3.80,
            total_cost_est=5320.00,
        ),
    ]

    mock_rooms = [
        {"id": "room_1", "name": "Main Office Area", "area_sqft": 950.0},
        {"id": "room_2", "name": "Conference Room", "area_sqft": 450.0},
    ]

    mock_walls = [
        {"id": "wall_1", "length_ft": 45.0, "height_ft": 10.0, "type": "Interior Partition"},
        {"id": "wall_2", "length_ft": 30.0, "height_ft": 10.0, "type": "Exterior Wall"},
    ]

    total_cost = sum(item.total_cost_est for item in mock_materials)

    return TakeoffResponse(
        filename=file.filename,
        project_title=project_title,
        detected_rooms=mock_rooms,
        detected_walls=mock_walls,
        materials=mock_materials,
        total_estimated_cost=total_cost,
    )


class EstimateRequest(BaseModel):
    takeoff_data: Dict[str, Any]
    pricing_tier: Optional[str] = "standard"


@app.post("/estimate")
def calculate_estimate(request: EstimateRequest):
    takeoff = request.takeoff_data
    materials = takeoff.get("materials", [])
    
    subtotal = sum(m.get("total_cost_est", 0.0) for m in materials)
    labor_markup = subtotal * 0.35
    overhead_and_profit = subtotal * 0.15
    total_quote = subtotal + labor_markup + overhead_and_profit

    return {
        "project_title": takeoff.get("project_title", "Blueprint Estimate"),
        "pricing_tier": request.pricing_tier,
        "material_subtotal": round(subtotal, 2),
        "labor_estimate": round(labor_markup, 2),
        "overhead_and_profit": round(overhead_and_profit, 2),
        "grand_total": round(total_quote, 2),
        "item_count": len(materials),
    }
