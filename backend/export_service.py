"""
Export service for OmniSubEstimator material takeoffs.
Provides CSV and JSON generation formatted for subcontractor bidding and accounting workflows.
"""

import csv
import io
from typing import Dict, Any, Optional


def generate_takeoff_csv(
    takeoff_data: Dict[str, Any],
    estimate_data: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Generates CSV string containing the itemized material takeoff and estimate summary.
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # Header metadata
    project_title = takeoff_data.get("project_title", "Blueprint Takeoff")
    filename = takeoff_data.get("filename", "unknown.pdf")
    writer.writerow(["OmniSubEstimator — Subcontractor Material Takeoff & Cost Estimate"])
    writer.writerow(["Project Title:", project_title])
    writer.writerow(["Source File:", filename])
    writer.writerow(["Total Floor Area (sq ft):", takeoff_data.get("total_floor_area_sqft", "N/A")])
    writer.writerow(["Total Wall Linear Ft:", takeoff_data.get("total_wall_linear_ft", "N/A")])
    writer.writerow([])

    # Table headers
    writer.writerow([
        "CSI MasterFormat",
        "Category",
        "Item Name",
        "Quantity",
        "Unit",
        "Unit Cost ($)",
        "Total Cost ($)",
    ])

    materials = takeoff_data.get("materials", [])
    for m in materials:
        writer.writerow([
            m.get("csi_code", "09 00 00"),
            m.get("category", "General"),
            m.get("item_name", "Material Item"),
            m.get("quantity", 0),
            m.get("unit", "each"),
            f"{float(m.get('unit_cost_est', 0.0)):.2f}",
            f"{float(m.get('total_cost_est', 0.0)):.2f}",
        ])

    writer.writerow([])

    # Cost estimate breakdown if provided
    if estimate_data:
        writer.writerow(["--- ESTIMATE SUMMARY ---"])
        writer.writerow(["Material Subtotal ($):", f"{float(estimate_data.get('material_subtotal', 0.0)):.2f}"])
        writer.writerow(["Labor Estimate ($):", f"{float(estimate_data.get('labor_estimate', 0.0)):.2f}"])
        writer.writerow(["Overhead & Profit ($):", f"{float(estimate_data.get('overhead_and_profit', 0.0)):.2f}"])
        writer.writerow(["Grand Total Quote ($):", f"{float(estimate_data.get('grand_total', 0.0)):.2f}"])
    else:
        total_mat = takeoff_data.get("total_estimated_cost", 0.0)
        writer.writerow(["Total Estimated Material Cost ($):", f"{float(total_mat):.2f}"])

    return output.getvalue()
