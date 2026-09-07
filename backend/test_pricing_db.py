import pytest
from backend.pricing_db import (
    get_all_pricing_items,
    get_item_by_name,
    calculate_takeoff_materials,
    RS_MEANS_DATABASE,
)


def test_pricing_database_seeded():
    items = get_all_pricing_items()
    assert len(items) >= 10
    assert any(i.csi_code == "09 29 00" for i in items)
    assert any("drywall" in i.item_name.lower() for i in items)


def test_get_item_by_name():
    drywall = get_item_by_name("gypsum")
    assert drywall is not None
    assert drywall.unit == "sheets"
    assert drywall.material_cost > 0

    stud = get_item_by_name("metal framing studs")
    assert stud is not None
    assert stud.csi_code == "09 22 16"

    none_item = get_item_by_name("nonexistent_item_xyz")
    assert none_item is None


def test_calculate_takeoff_materials_standard():
    materials = calculate_takeoff_materials(
        total_floor_area_sqft=1000.0,
        total_wall_linear_ft=120.0,
        wall_height_ft=10.0,
        room_count=3,
        finish_level="standard",
    )
    assert len(materials) >= 8
    
    # Check drywall item
    drywall = next(m for m in materials if "drywall" in m["category"].lower() and "board" in m["item_name"].lower())
    assert drywall["quantity"] > 0
    assert drywall["unit"] == "sheets"
    assert drywall["total_cost_est"] > 0

    # Check framing studs
    studs = next(m for m in materials if "studs" in m["item_name"].lower())
    assert studs["quantity"] > 50

    # Check doors
    doors = next(m for m in materials if "door" in m["item_name"].lower())
    assert doors["quantity"] == 3


def test_calculate_takeoff_materials_premium():
    materials = calculate_takeoff_materials(
        total_floor_area_sqft=500.0,
        total_wall_linear_ft=60.0,
        wall_height_ft=10.0,
        room_count=2,
        finish_level="premium",
    )
    drywall = next(m for m in materials if "drywall" in m["category"].lower() and "board" in m["item_name"].lower())
    assert "Type X" in drywall["item_name"]
