import cv2
import numpy as np
import pymupdf as fitz
import pytest

from backend.blueprint_parser import (
    detect_scale_from_text,
    extract_document_pages,
    detect_walls_and_rooms,
    parse_blueprint_file,
)


def create_synthetic_blueprint_image():
    """Generates a 800x600 synthetic floor plan image with 2 enclosed rooms and walls."""
    img = np.ones((600, 800, 3), dtype=np.uint8) * 255  # white background
    
    # Outer walls (black lines, thickness=5)
    cv2.rectangle(img, (80, 80), (720, 520), (0, 0, 0), 5)
    
    # Dividing interior wall
    cv2.line(img, (400, 80), (400, 520), (0, 0, 0), 5)

    # Encode to PNG bytes
    _, buf = cv2.imencode(".png", img)
    return buf.tobytes()


def create_synthetic_blueprint_pdf():
    """Generates a synthetic PDF blueprint using PyMuPDF with vectors and text."""
    doc = fitz.open()
    page = doc.new_page(width=800, height=600)
    
    # Draw walls
    page.draw_rect(fitz.Rect(80, 80, 720, 520), color=(0, 0, 0), width=4)
    page.draw_line(fitz.Point(400, 80), fitz.Point(400, 520), color=(0, 0, 0), width=4)
    
    # Insert text annotations
    page.insert_text(fitz.Point(150, 200), "CONFERENCE ROOM", fontsize=14, color=(0, 0, 0))
    page.insert_text(fitz.Point(450, 200), "EXECUTIVE SUITE", fontsize=14, color=(0, 0, 0))
    page.insert_text(fitz.Point(100, 550), 'SCALE: 1/4" = 1\'-0"', fontsize=10, color=(0, 0, 0))
    
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_detect_scale_from_text():
    label, px = detect_scale_from_text('ARCHITECTURAL PLAN\nSCALE: 1/4" = 1\'-0"\nSHEET A-101')
    assert "1/4\"" in label
    assert px == 37.5

    label2, px2 = detect_scale_from_text('SCALE: 1/8" = 1\'-0"')
    assert "1/8\"" in label2
    assert px2 == 18.75


def test_parse_synthetic_image():
    png_bytes = create_synthetic_blueprint_image()
    result = parse_blueprint_file(png_bytes, "floorplan.png")
    
    assert result["filename"] == "floorplan.png"
    assert result["total_wall_linear_ft"] > 0
    assert result["total_floor_area_sqft"] > 0
    assert len(result["detected_rooms"]) >= 1
    assert "data:image/jpeg;base64," in result["annotated_overlay_base64"]


def test_parse_synthetic_pdf():
    pdf_bytes = create_synthetic_blueprint_pdf()
    result = parse_blueprint_file(pdf_bytes, "commercial_plan.pdf")
    
    assert result["filename"] == "commercial_plan.pdf"
    assert "1/4\"" in result["scale"]
    assert result["total_wall_linear_ft"] > 0
    assert result["total_floor_area_sqft"] > 0
    assert len(result["detected_rooms"]) >= 1
    # Check if text annotation was extracted into room names
    room_names = [r["name"].upper() for r in result["detected_rooms"]]
    assert any("CONFERENCE" in name or "EXECUTIVE" in name or "OFFICE" in name or "ROOM" in name for name in room_names)
