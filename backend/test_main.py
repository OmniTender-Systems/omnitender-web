import cv2
import numpy as np
import pymupdf as fitz
import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def make_test_pdf() -> bytes:
    """Helper to generate a valid test PDF in memory."""
    doc = fitz.open()
    page = doc.new_page(width=600, height=400)
    page.draw_rect(fitz.Rect(50, 50, 550, 350), color=(0, 0, 0), width=3)
    page.draw_line(fitz.Point(300, 50), fitz.Point(300, 350), color=(0, 0, 0), width=3)
    page.insert_text(fitz.Point(100, 150), "OFFICE 101", fontsize=12)
    page.insert_text(fitz.Point(350, 150), "OFFICE 102", fontsize=12)
    b = doc.tobytes()
    doc.close()
    return b


def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["service"] == "OmniSubEstimator API"
    assert "version" in response.json()


def test_healthcheck():
    response = client.get("/healthcheck")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_pricing_endpoint():
    response = client.get("/pricing")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 10
    assert any(i["category"] == "Drywall & Plaster" for i in data)


def test_upload_invalid_file_type():
    files = {"file": ("test.txt", b"dummy content", "text/plain")}
    response = client.post("/upload", files=files)
    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]


def test_upload_valid_pdf_blueprint():
    pdf_bytes = make_test_pdf()
    files = {"file": ("office_plan.pdf", pdf_bytes, "application/pdf")}
    data = {"project_title": "HQ Renovation", "finish_level": "standard"}
    response = client.post("/upload", files=files, data=data)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["filename"] == "office_plan.pdf"
    assert res_data["project_title"] == "HQ Renovation"
    assert res_data["total_floor_area_sqft"] > 0
    assert res_data["total_wall_linear_ft"] > 0
    assert len(res_data["detected_rooms"]) >= 1
    assert len(res_data["materials"]) >= 5
    assert res_data["total_estimated_cost"] > 0
    assert "annotated_overlay_base64" in res_data
    assert "ai_analysis" in res_data


def test_estimate_endpoint():
    takeoff = {
        "project_title": "Sample Takeoff",
        "materials": [
            {"item_name": "Drywall", "total_cost_est": 1000.0},
            {"item_name": "Studs", "total_cost_est": 500.0},
        ],
    }
    req_body = {
        "takeoff_data": takeoff,
        "pricing_tier": "standard",
        "labor_rate_multiplier": 0.35,
        "overhead_profit_multiplier": 0.15,
        "contingency_multiplier": 0.05,
    }
    response = client.post("/estimate", json=req_body)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["material_subtotal"] == 1500.0
    assert res_data["labor_estimate"] == 525.0
    assert res_data["overhead_and_profit"] == 225.0
    assert res_data["contingency"] == 75.0
    assert res_data["grand_total"] == 2325.0


def test_export_csv():
    takeoff = {
        "filename": "test_plan.pdf",
        "project_title": "Apex Medical Office",
        "total_floor_area_sqft": 1200.0,
        "total_wall_linear_ft": 140.0,
        "materials": [
            {
                "csi_code": "09 29 00",
                "category": "Drywall",
                "item_name": '1/2" Gypsum Board',
                "quantity": 100,
                "unit": "sheets",
                "unit_cost_est": 15.50,
                "total_cost_est": 1550.00,
            }
        ],
        "total_estimated_cost": 1550.00,
    }
    estimate = {
        "material_subtotal": 1550.0,
        "labor_estimate": 542.5,
        "overhead_and_profit": 232.5,
        "grand_total": 2325.0,
    }
    response = client.post("/export/csv", json={"takeoff_data": takeoff, "estimate_data": estimate})
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "Gypsum Board" in response.text
    assert "ESTIMATE SUMMARY" in response.text


def test_stripe_create_checkout_session():
    response = client.post(
        "/stripe/create-checkout-session",
        json={"plan_tier": "pro"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "checkout_url" in data
    assert "session_id" in data


def test_ui_endpoints():
    res_page = client.get("/estimator")
    assert res_page.status_code == 200
    assert "text/html" in res_page.headers["content-type"]
    assert "OmniSubEstimator" in res_page.text

    res_logo = client.get("/logo.svg")
    assert res_logo.status_code == 200
    assert "image/svg+xml" in res_logo.headers["content-type"]

    res_css = client.get("/style.css")
    assert res_css.status_code == 200
    assert "text/css" in res_css.headers["content-type"]

