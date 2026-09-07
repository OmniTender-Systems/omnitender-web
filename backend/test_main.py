import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["service"] == "OmniSubEstimator API"


def test_healthcheck():
    response = client.get("/healthcheck")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_upload_invalid_file_type():
    files = {"file": ("test.txt", b"dummy content", "text/plain")}
    response = client.post("/upload", files=files)
    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]


def test_upload_valid_file():
    files = {"file": ("blueprint.pdf", b"%PDF-1.4 dummy pdf content", "application/pdf")}
    data = {"project_title": "Test Building"}
    response = client.post("/upload", files=files, data=data)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["filename"] == "blueprint.pdf"
    assert res_data["project_title"] == "Test Building"
    assert len(res_data["materials"]) > 0
    assert res_data["total_estimated_cost"] > 0


def test_estimate_endpoint():
    takeoff = {
        "project_title": "Sample Takeoff",
        "materials": [
            {"item_name": "Drywall", "total_cost_est": 1000.0},
            {"item_name": "Studs", "total_cost_est": 500.0},
        ],
    }
    response = client.post("/estimate", json={"takeoff_data": takeoff, "pricing_tier": "standard"})
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["material_subtotal"] == 1500.0
    assert res_data["labor_estimate"] == 525.0
    assert res_data["overhead_and_profit"] == 225.0
    assert res_data["grand_total"] == 2250.0
