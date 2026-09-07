"""
RS Means Construction Material & Labor Pricing Database Seed.
Provides realistic unit prices, labor rates, and calculation formulas for commercial
and residential subcontractor material takeoffs.
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel


class RSMeansItem(BaseModel):
    csi_code: str
    category: str
    item_name: str
    unit: str
    material_cost: float
    labor_cost: float
    equipment_cost: float
    total_unit_cost: float
    description: str


# Seeded RS Means standard pricing data
RS_MEANS_DATABASE: List[Dict[str, Any]] = [
    {
        "csi_code": "09 29 00",
        "category": "Drywall & Plaster",
        "item_name": '1/2" Gypsum Wallboard (4x8 ft)',
        "unit": "sheets",
        "material_cost": 15.50,
        "labor_cost": 18.20,
        "equipment_cost": 1.20,
        "total_unit_cost": 34.90,
        "description": "Standard 1/2-in gypsum board for interior non-fire rated partition walls.",
    },
    {
        "csi_code": "09 29 00",
        "category": "Drywall & Plaster",
        "item_name": '5/8" Type X Fire-Rated Gypsum Board (4x8 ft)',
        "unit": "sheets",
        "material_cost": 19.80,
        "labor_cost": 21.50,
        "equipment_cost": 1.50,
        "total_unit_cost": 42.80,
        "description": "Fire-resistant gypsum drywall for corridors, demising walls, and shafts.",
    },
    {
        "csi_code": "09 29 00",
        "category": "Drywall & Plaster",
        "item_name": "Drywall Joint Compound & Tape",
        "unit": "buckets (4.5 gal)",
        "material_cost": 22.50,
        "labor_cost": 15.00,
        "equipment_cost": 0.50,
        "total_unit_cost": 38.00,
        "description": "All-purpose premixed joint compound and paper tape for Level 4 drywall finish.",
    },
    {
        "csi_code": "09 22 16",
        "category": "Framing",
        "item_name": "3-5/8\" 20-Gauge Light Metal Framing Studs (10 ft)",
        "unit": "pieces",
        "material_cost": 8.40,
        "labor_cost": 11.20,
        "equipment_cost": 0.80,
        "total_unit_cost": 20.40,
        "description": "Commercial cold-formed steel studs at 16-in O.C. for interior partition walls.",
    },
    {
        "csi_code": "06 11 00",
        "category": "Framing",
        "item_name": "2x4x10 ft SPF Wood Framing Studs",
        "unit": "pieces",
        "material_cost": 7.20,
        "labor_cost": 9.50,
        "equipment_cost": 0.50,
        "total_unit_cost": 17.20,
        "description": "Kiln-dried SPF wood framing lumber for wall studs and blocking.",
    },
    {
        "csi_code": "09 22 16",
        "category": "Framing",
        "item_name": "3-5/8\" Steel Track (10 ft)",
        "unit": "pieces",
        "material_cost": 7.90,
        "labor_cost": 8.50,
        "equipment_cost": 0.60,
        "total_unit_cost": 17.00,
        "description": "Cold-formed steel top and bottom runner tracks for partition framing.",
    },
    {
        "csi_code": "09 65 00",
        "category": "Flooring",
        "item_name": "Commercial Luxury Vinyl Plank (LVP)",
        "unit": "sq ft",
        "material_cost": 3.80,
        "labor_cost": 2.75,
        "equipment_cost": 0.25,
        "total_unit_cost": 6.80,
        "description": "20 mil wear layer glue-down or click-lock commercial vinyl plank flooring.",
    },
    {
        "csi_code": "09 68 00",
        "category": "Flooring",
        "item_name": "Commercial Modular Carpet Tile (24x24 in)",
        "unit": "sq ft",
        "material_cost": 4.25,
        "labor_cost": 2.10,
        "equipment_cost": 0.15,
        "total_unit_cost": 6.50,
        "description": "Nylon solution-dyed modular carpet tiles for high-traffic offices and conference rooms.",
    },
    {
        "csi_code": "09 30 00",
        "category": "Flooring",
        "item_name": "Porcelain Floor Tile (12x24 in)",
        "unit": "sq ft",
        "material_cost": 6.50,
        "labor_cost": 7.20,
        "equipment_cost": 0.50,
        "total_unit_cost": 14.20,
        "description": "Commercial slip-resistant porcelain tile for restrooms, lobbies, and breakrooms.",
    },
    {
        "csi_code": "09 51 00",
        "category": "Ceilings",
        "item_name": "2x2 ft Acoustic Ceiling Tile (ACT) & Grid System",
        "unit": "sq ft",
        "material_cost": 2.90,
        "labor_cost": 3.40,
        "equipment_cost": 0.30,
        "total_unit_cost": 6.60,
        "description": "Suspended T-bar grid system with mineral fiber sound-absorbing ceiling tiles.",
    },
    {
        "csi_code": "09 91 23",
        "category": "Painting & Finishes",
        "item_name": "Interior Commercial Latex Primer & 2 Finish Coats",
        "unit": "sq ft",
        "material_cost": 0.65,
        "labor_cost": 1.45,
        "equipment_cost": 0.15,
        "total_unit_cost": 2.25,
        "description": "Low-VOC commercial eggshell/satin latex paint on interior wall surfaces.",
    },
    {
        "csi_code": "09 65 13",
        "category": "Millwork & Trim",
        "item_name": "4-inch Vinyl Cove Base Molding",
        "unit": "linear ft",
        "material_cost": 1.10,
        "labor_cost": 1.60,
        "equipment_cost": 0.05,
        "total_unit_cost": 2.75,
        "description": "Thermoplastic rubber/vinyl cove base with adhesive backing.",
    },
    {
        "csi_code": "07 21 00",
        "category": "Thermal & Moisture",
        "item_name": "R-13 Sound Batt Fiberglass Insulation (3-1/2 in)",
        "unit": "sq ft",
        "material_cost": 0.85,
        "labor_cost": 0.95,
        "equipment_cost": 0.05,
        "total_unit_cost": 1.85,
        "description": "Acoustical and thermal fiberglass batt insulation for interior demising walls.",
    },
    {
        "csi_code": "08 11 00",
        "category": "Doors & Windows",
        "item_name": "36x84 in Commercial Hollow Metal Door & Frame",
        "unit": "units",
        "material_cost": 450.00,
        "labor_cost": 280.00,
        "equipment_cost": 25.00,
        "total_unit_cost": 755.00,
        "description": "16-gauge hollow metal door with knock-down welded frame, hinges, and lever lockset.",
    },
    {
        "csi_code": "08 14 00",
        "category": "Doors & Windows",
        "item_name": "36x84 in Solid Core Wood Interior Door",
        "unit": "units",
        "material_cost": 320.00,
        "labor_cost": 210.00,
        "equipment_cost": 20.00,
        "total_unit_cost": 550.00,
        "description": "Birch wood veneer solid core flush door with commercial grade mortise lockset.",
    },
]


def get_all_pricing_items() -> List[RSMeansItem]:
    """Return all RS Means database items."""
    return [RSMeansItem(**item) for item in RS_MEANS_DATABASE]


def get_item_by_name(name_query: str) -> Optional[RSMeansItem]:
    """Find RS Means item by substring match."""
    query_lower = name_query.lower()
    for item in RS_MEANS_DATABASE:
        if query_lower in item["item_name"].lower() or query_lower in item["category"].lower():
            return RSMeansItem(**item)
    return None


def calculate_takeoff_materials(
    total_floor_area_sqft: float,
    total_wall_linear_ft: float,
    wall_height_ft: float = 10.0,
    room_count: int = 2,
    finish_level: str = "standard",
) -> List[Dict[str, Any]]:
    """
    Derives itemized material takeoff from architectural measurements using RS Means standards.
    """
    total_wall_surface_area = total_wall_linear_ft * wall_height_ft * 2.0  # both sides
    
    # 1. Drywall: 4x8 sheet = 32 sqft, add 10% cutting waste
    drywall_sheets = round((total_wall_surface_area / 32.0) * 1.10, 1)
    drywall_rate = 15.50 if finish_level != "premium" else 19.80
    drywall_name = '1/2" Gypsum Wallboard (4x8 ft)' if finish_level != "premium" else '5/8" Type X Fire-Rated Gypsum Board (4x8 ft)'
    
    # 2. Joint compound: ~1 bucket per 500 sqft of wall
    joint_compound_buckets = round(max(1.0, (total_wall_surface_area / 500.0) * 1.15), 1)
    
    # 3. Framing studs: 16" O.C. = 1 stud every 1.33 ft + 15% extra for corners/openings + plates
    studs_count = round((total_wall_linear_ft / 1.33) * 1.15, 0)
    top_bottom_tracks = round((total_wall_linear_ft * 2.0 / 10.0) * 1.10, 0)  # 10 ft track lengths
    
    # 4. Flooring: floor area + 10% waste
    flooring_sqft = round(total_floor_area_sqft * 1.10, 1)
    
    # 5. Acoustic ceiling: floor area + 8% waste
    ceiling_sqft = round(total_floor_area_sqft * 1.08, 1)
    
    # 6. Paint: 350 sq ft per gallon coverage * 2 coats
    paint_sqft = round(total_wall_surface_area, 1)
    
    # 7. Baseboards: wall linear ft * 1.05 waste
    baseboard_linear_ft = round(total_wall_linear_ft * 1.05, 1)
    
    # 8. Doors: typically 1 door per room
    doors_count = max(1, room_count)
    
    # Compile line items with RS Means unit pricing
    items = [
        {
            "csi_code": "09 29 00",
            "category": "Drywall & Plaster",
            "item_name": drywall_name,
            "quantity": drywall_sheets,
            "unit": "sheets",
            "unit_cost_est": drywall_rate,
            "total_cost_est": round(drywall_sheets * drywall_rate, 2),
        },
        {
            "csi_code": "09 29 00",
            "category": "Drywall & Plaster",
            "item_name": "Drywall Joint Compound & Tape",
            "quantity": joint_compound_buckets,
            "unit": "buckets (4.5 gal)",
            "unit_cost_est": 22.50,
            "total_cost_est": round(joint_compound_buckets * 22.50, 2),
        },
        {
            "csi_code": "09 22 16",
            "category": "Framing",
            "item_name": "3-5/8\" 20-Gauge Light Metal Framing Studs (10 ft)",
            "quantity": studs_count,
            "unit": "pieces",
            "unit_cost_est": 8.40,
            "total_cost_est": round(studs_count * 8.40, 2),
        },
        {
            "csi_code": "09 22 16",
            "category": "Framing",
            "item_name": "3-5/8\" Steel Track (10 ft)",
            "quantity": top_bottom_tracks,
            "unit": "pieces",
            "unit_cost_est": 7.90,
            "total_cost_est": round(top_bottom_tracks * 7.90, 2),
        },
        {
            "csi_code": "09 65 00",
            "category": "Flooring",
            "item_name": "Commercial Luxury Vinyl Plank (LVP)",
            "quantity": flooring_sqft,
            "unit": "sq ft",
            "unit_cost_est": 3.80,
            "total_cost_est": round(flooring_sqft * 3.80, 2),
        },
        {
            "csi_code": "09 51 00",
            "category": "Ceilings",
            "item_name": "2x2 ft Acoustic Ceiling Tile (ACT) & Grid System",
            "quantity": ceiling_sqft,
            "unit": "sq ft",
            "unit_cost_est": 2.90,
            "total_cost_est": round(ceiling_sqft * 2.90, 2),
        },
        {
            "csi_code": "09 91 23",
            "category": "Painting & Finishes",
            "item_name": "Interior Commercial Latex Primer & 2 Finish Coats",
            "quantity": paint_sqft,
            "unit": "sq ft",
            "unit_cost_est": 0.65,
            "total_cost_est": round(paint_sqft * 0.65, 2),
        },
        {
            "csi_code": "09 65 13",
            "category": "Millwork & Trim",
            "item_name": "4-inch Vinyl Cove Base Molding",
            "quantity": baseboard_linear_ft,
            "unit": "linear ft",
            "unit_cost_est": 1.10,
            "total_cost_est": round(baseboard_linear_ft * 1.10, 2),
        },
        {
            "csi_code": "08 14 00",
            "category": "Doors & Windows",
            "item_name": "36x84 in Solid Core Wood Interior Door",
            "quantity": doors_count,
            "unit": "units",
            "unit_cost_est": 320.00,
            "total_cost_est": round(doors_count * 320.00, 2),
        },
    ]

    return items
