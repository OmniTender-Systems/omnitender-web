"""
Gemini Vision Material Identification and Specifications Analyzer.
Leverages Google Gemini Vision models to inspect architectural blueprints, schedules,
and notes to identify finish levels, materials, and trade requirements.
"""

import json
import logging
import os
import re
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


def is_gemini_available() -> bool:
    """Checks if Gemini API credentials exist."""
    return bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))


def analyze_blueprint_materials_with_gemini(
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
    rooms: Optional[List[Dict[str, Any]]] = None,
    walls: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Sends blueprint sheet image to Gemini Vision API for material and finish identification.
    Falls back gracefully to standard commercial heuristic trade analysis if offline or unauthenticated.
    """
    rooms = rooms or []
    walls = walls or []

    if not is_gemini_available():
        logger.info("Gemini API key not configured. Using heuristic material analyzer.")
        return generate_heuristic_material_analysis(rooms, walls)

    try:
        from google import genai
        from google.genai import types

        client = genai.Client()

        prompt = (
            "You are a master commercial construction estimator and blueprint specialist. "
            "Examine this architectural blueprint / floor plan image and extract the construction materials, "
            "wall partitions, floor finishes, ceiling specifications, and door/hardware schedules.\n"
            "Return a strictly valid JSON object with the following schema:\n"
            "{\n"
            '  "project_type": "Commercial Office" | "Retail" | "Residential",\n'
            '  "finish_level": "standard" | "economy" | "premium",\n'
            '  "wall_specifications": "Description of partition framing and drywall (e.g. 5/8 Type X on 3-5/8 steel studs)",\n'
            '  "flooring_specifications": "Description of flooring finishes (e.g. LVP in breakroom, carpet tile in offices)",\n'
            '  "ceiling_specifications": "Description of ceiling system (e.g. 2x2 ACT acoustic drop ceiling)",\n'
            '  "trade_notes": ["Note 1", "Note 2"],\n'
            '  "recommended_subcontractors": ["Drywall & Framing", "Commercial Flooring", "Painting & Finishes", "Acoustic Ceilings"]\n'
            "}\n"
            "Output only the JSON code block."
        )

        candidate_models = ["gemini-2.5-flash", "gemini-3.1-pro-preview", "gemini-2.5-pro"]
        response_text = None

        for model_name in candidate_models:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[
                        types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                        prompt,
                    ],
                )
                if response and response.text:
                    response_text = response.text.strip()
                    break
            except Exception as model_err:
                logger.warning(f"Model {model_name} failed: {model_err}")
                continue

        if response_text:
            cleaned = response_text
            if cleaned.startswith("```"):
                cleaned = re.sub(r"^```[a-zA-Z]*\n", "", cleaned)
                cleaned = re.sub(r"\n```$", "", cleaned)
            parsed = json.loads(cleaned)
            parsed["ai_powered"] = True
            return parsed

    except Exception as e:
        logger.warning(f"Gemini Vision call failed ({e}). Falling back to heuristic analysis.")

    return generate_heuristic_material_analysis(rooms, walls)


def generate_heuristic_material_analysis(
    rooms: List[Dict[str, Any]],
    walls: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Intelligent fallback heuristic analysis when Gemini API is unavailable or for offline testing.
    """
    total_area = sum(r.get("area_sqft", 0.0) for r in rooms)
    has_wet_areas = any(
        any(k in r.get("name", "").lower() for k in ["restroom", "kitchen", "breakroom", "bath"])
        for r in rooms
    )

    return {
        "ai_powered": False,
        "project_type": "Commercial Office / Tenant Improvement" if total_area > 500 else "Small Commercial Space",
        "finish_level": "standard",
        "wall_specifications": '3-5/8" 20-ga steel studs @ 16" O.C. with 1/2" Gypsum Board both sides (5/8" Type X at demising partitions)',
        "flooring_specifications": "Porcelain tile in wet areas & breakrooms; commercial luxury vinyl plank (LVP) and modular carpet tile in open areas",
        "ceiling_specifications": '2x2 ft Acoustical Ceiling Tile (ACT) suspended T-bar grid system at 9\'-0" A.F.F.',
        "trade_notes": [
            "Verify all structural dimension field conditions prior to rough-in.",
            "Level 4 drywall finish specified for all exposed painted partitions.",
            "Sound attenuation batts (R-13) required in all conference room partition cavities.",
            f"Detected {len(rooms)} discrete room zones totaling {round(total_area, 1)} sq ft.",
        ],
        "recommended_subcontractors": [
            "Division 09: Drywall, Framing & Acoustical Ceilings",
            "Division 09: Commercial Flooring & Tile",
            "Division 09: Painting & Wall Coverings",
            "Division 08: Commercial Doors & Hardware",
        ],
    }
